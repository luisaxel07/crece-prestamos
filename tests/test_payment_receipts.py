"""Comprobantes, permisos de lectura, confirmación y baja de clientes con ORM real."""
import unittest
from io import BytesIO
from decimal import Decimal
from unittest.mock import patch
from sqlalchemy import select,func,inspect
from PIL import Image
import test_orm_management as fixtures
from datos_comprobantes import imagen_prueba
from crece.infraestructura.base_datos import transaccion
from crece.infraestructura.modelos import Pago,ComprobantePago,Cliente,Usuario
from crece.servicios import gestion as s,cuentas_orm as cuentas,portal_orm as portal
from crece.servicios.comprobantes import preparar_comprobante,obtener_comprobante_pago,MAX_COMPROBANTE,ErrorComprobante
from crece.servicios.permisos import establecer_actor
from crece.servicios.reportes import obtener_reporte
from portal_web.app_web import aplicacion

class ComprobanteRulesTests(unittest.TestCase):
    def test_decodes_real_image_and_strips_extra_data(self):
        raw=imagen_prueba()+b'<script>private-metadata</script>'
        salida=preparar_comprobante(raw)
        self.assertNotIn(b'<script>',salida)
        with Image.open(BytesIO(salida)) as image:self.assertEqual(image.format,'JPEG');self.assertFalse(image.getexif())
    def test_invalid_empty_large_animated_and_fake_files_are_rejected(self):
        imagen=Image.new('RGB',(10001,1),'white');buffer=BytesIO();imagen.save(buffer,format='PNG')
        animation=BytesIO();a=Image.new('RGB',(10,10),'white');b=Image.new('RGB',(10,10),'black');a.save(animation,format='GIF',save_all=True,append_images=[b])
        for content in [None,b'',b'<svg onload=alert(1)>',b'not a picture',b'x'*(MAX_COMPROBANTE+1),buffer.getvalue(),animation.getvalue()]:
            with self.subTest(size=len(content) if content else 0),self.assertRaises(ErrorComprobante):preparar_comprobante(content)

class PaymentReceiptTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.OrmManagementTests();self.fixture.setUp()
        self.admin=self.fixture.admin;self.cid=self.fixture.client;self.loan=self.fixture.loan()
        cuentas.crear_cuenta_cliente(self.cid,'cliente@example.test','ClavePrueba-2026')
        self.customer=cuentas.iniciar_sesion_web('cliente@example.test','ClavePrueba-2026')['id']
        self.fixture.employee();self.employee=s.listar_empleados()[0]['usuario_id']
        self.quota=obtener_reporte(prestamo_id=self.loan)['prestamos'][0]['cuotas'][0]
        aplicacion.config.update(TESTING=True)
        self.client=self.browser(self.customer,'CLIENTE');self.admin_browser=self.browser(self.admin,'ADMINISTRADOR');self.employee_browser=self.browser(self.employee,'EMPLEADO')
    def tearDown(self):self.fixture.tearDown()
    def browser(self,id,rol):
        b=aplicacion.test_client()
        with b.session_transaction() as sess:sess.update(version_sesion=1,usuario_id=id,rol=rol,nombre_usuario='prueba',token_csrf='csrf-prueba')
        return b
    def upload(self,content=None,referencia='TRANSFERENCIA-PRUEBA',file=True):
        data=dict(token_csrf='csrf-prueba',cuota_id=str(self.quota['id']),monto='100',referencia=referencia)
        if file:data['comprobante']=(BytesIO(imagen_prueba() if content is None else content),'recibo.png')
        return self.client.post('/pagos/solicitar',data=data,content_type='multipart/form-data')
    def payment(self):
        with transaccion() as db:return db.scalar(select(Pago.id))
    def test_photo_and_text_stay_pending_until_employee_confirms(self):
        self.assertEqual(self.upload().status_code,302);id=self.payment()
        self.assertEqual(portal.listar_cuotas_cliente(self.customer)[0]['saldo'],self.quota['saldo'])
        self.assertEqual(portal.listar_solicitudes_pago_cliente(self.customer)[0]['referencia'],'TRANSFERENCIA-PRUEBA')
        self.assertTrue(portal.listar_solicitudes_pago_cliente(self.customer)[0]['tiene_comprobante'])
        for browser,path in [(self.client,f'/pagos/{id}/comprobante'),(self.employee_browser,f'/gestion/pagos/{id}/comprobante'),(self.admin_browser,f'/gestion/pagos/{id}/comprobante')]:
            r=browser.get(path);self.assertEqual(r.status_code,200);self.assertEqual(r.mimetype,'image/jpeg');self.assertEqual(r.headers['Cache-Control'],'no-store');self.assertEqual(r.headers['X-Content-Type-Options'],'nosniff')
        html=self.employee_browser.get(f'/gestion/pagos/{id}').get_data(as_text=True);self.assertIn('Comprobante adjunto',html);self.assertIn('TRANSFERENCIA-PRUEBA',html)
        r=self.employee_browser.post(f'/gestion/pagos/{id}',data=dict(token_csrf='csrf-prueba',accion='CONFIRMAR',motivo=''))
        self.assertEqual(r.status_code,302)
        self.assertEqual(portal.listar_cuotas_cliente(self.customer)[0]['saldo'],self.quota['saldo']-100)
        with transaccion() as db:self.assertEqual(db.get(Pago,id).registrado_por,self.employee)
        self.assertEqual(self.employee_browser.post(f'/gestion/pagos/{id}',data=dict(token_csrf='csrf-prueba',accion='CONFIRMAR')).status_code,400)
    def test_image_is_private_to_owner_and_current_active_staff(self):
        self.upload();id=self.payment()
        other=s.registrar_cliente('001-170892-0003C','Otra','Persona','88888888');cuentas.crear_cuenta_cliente(other,'otra@example.test','ClavePrueba-2026')
        uid=cuentas.iniciar_sesion_web('otra@example.test','ClavePrueba-2026')['id'];other_browser=self.browser(uid,'CLIENTE')
        self.assertEqual(other_browser.get(f'/pagos/{id}/comprobante').status_code,404)
        self.assertEqual(other_browser.get(f'/gestion/pagos/{id}/comprobante').status_code,403)
        self.assertEqual(aplicacion.test_client().get(f'/pagos/{id}/comprobante').status_code,403)
        self.assertEqual(aplicacion.test_client().get(f'/gestion/pagos/{id}/comprobante').status_code,403)
        cuentas.cambiar_estado_usuario(self.employee,False)
        self.assertEqual(self.employee_browser.get(f'/gestion/pagos/{id}/comprobante').status_code,403)
    def test_missing_bad_or_oversized_file_creates_no_payments_or_attachments(self):
        for response in [self.upload(file=False),self.upload(b'fake image'),self.upload(b'x'*(MAX_COMPROBANTE+1))]:self.assertEqual(response.status_code,302)
        with transaccion() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Pago)),0)
            self.assertEqual(db.scalar(select(func.count()).select_from(ComprobantePago)),0)
    def test_multipart_over_64kb_is_supported_and_global_limit_is_clear(self):
        image=Image.effect_noise((600,600),100).convert('RGB');buffer=BytesIO();image.save(buffer,format='PNG');data=buffer.getvalue();self.assertGreater(len(data),65536)
        self.assertEqual(self.upload(data).status_code,302);self.assertIsNotNone(self.payment())
        r=self.upload(b'x'*(6*1024*1024));self.assertEqual(r.status_code,413)
    def test_csrf_and_reference_remain_required(self):
        r=self.client.post('/pagos/solicitar',data=dict(token_csrf='incorrecto',comprobante=(BytesIO(imagen_prueba()),'foto.png')));self.assertEqual(r.status_code,400)
        self.upload(referencia=' ')
        with transaccion() as db:self.assertEqual(db.scalar(select(func.count()).select_from(Pago)),0)
    def test_duplicate_and_foreign_quota_leave_no_orphan_images(self):
        self.upload();self.upload()
        with transaccion() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Pago)),1)
            self.assertEqual(db.scalar(select(func.count()).select_from(ComprobantePago)),1)
        with self.assertRaises(ValueError):portal.solicitar_pago(self.customer,999,100,'Ajeno',comprobante=imagen_prueba())
        with transaccion() as db:self.assertEqual(db.scalar(select(func.count()).select_from(ComprobantePago)),1)
    def test_legacy_notice_has_no_photo_but_can_still_be_reviewed(self):
        with transaccion() as db:
            p=Pago(cuota_id=self.quota['id'],monto=100,metodo='PAGO_CLIENTE',referencia='AVISO-ANTERIOR',estado='PENDIENTE_VERIFICACION');db.add(p);db.flush();id=p.id
        html=self.admin_browser.get(f'/gestion/pagos/{id}').get_data(as_text=True);self.assertIn('solicitud anterior no tiene foto',html)
        self.assertEqual(self.admin_browser.get(f'/gestion/pagos/{id}/comprobante').status_code,404)
    def test_image_bytes_are_not_loaded_in_payment_lists(self):
        self.upload();id=self.payment()
        rows=s.listar_pagos();self.assertTrue(rows[0]['tiene_comprobante']);self.assertNotIn('contenido',rows[0])
        with transaccion() as db:
            record=db.scalar(select(ComprobantePago).where(ComprobantePago.pago_id==id));self.assertIn('contenido',inspect(record).unloaded)
    def test_rejection_preserves_evidence_without_applying_money(self):
        self.upload();id=self.payment();before=obtener_comprobante_pago(id)['contenido']
        r=self.employee_browser.post(f'/gestion/pagos/{id}',data=dict(token_csrf='csrf-prueba',accion='RECHAZAR',motivo=''))
        self.assertEqual(r.status_code,302);self.assertEqual(portal.listar_cuotas_cliente(self.customer)[0]['saldo'],self.quota['saldo'])
        self.assertEqual(before,obtener_comprobante_pago(id)['contenido'])
    def test_client_delete_is_visible_admin_only_and_requires_confirmation(self):
        html=self.admin_browser.get('/gestion/clientes').get_data(as_text=True);self.assertIn('Eliminar cliente',html)
        self.assertNotIn('Eliminar cliente',self.employee_browser.get('/gestion/clientes').get_data(as_text=True))
        self.assertEqual(self.employee_browser.post(f'/gestion/bajas/cliente/{self.cid}',data=dict(token_csrf='csrf-prueba',confirmacion='SI')).status_code,403)
        self.assertEqual(self.admin_browser.post(f'/gestion/bajas/cliente/{self.cid}',data=dict(confirmacion='SI')).status_code,400)
        before=obtener_reporte(prestamo_id=self.loan)['prestamos'][0]['cuotas']
        self.assertEqual(self.admin_browser.get(f'/gestion/bajas/cliente/{self.cid}').status_code,200)
        self.assertEqual(s.obtener_cliente(self.cid)['estado'],'ACTIVO')
        self.assertEqual(self.admin_browser.post(f'/gestion/bajas/cliente/{self.cid}',data=dict(token_csrf='csrf-prueba',confirmacion='SI')).status_code,302)
        self.assertEqual(s.obtener_cliente(self.cid)['estado'],'INACTIVO');self.assertEqual(before,obtener_reporte(prestamo_id=self.loan)['prestamos'][0]['cuotas'])
    def test_client_without_loans_can_be_deleted_and_linked_login_is_disabled(self):
        id=s.registrar_cliente('001-180893-0004D','Cliente','Sin préstamos','88888888');cuentas.crear_cuenta_cliente(id,'sinprestamos@example.test','ClavePrueba-2026')
        self.assertEqual(self.admin_browser.post(f'/gestion/bajas/cliente/{id}',data=dict(token_csrf='csrf-prueba',confirmacion='SI')).status_code,302)
        with transaccion() as db:self.assertIsNone(db.get(Cliente,id))
        self.assertIsNone(cuentas.iniciar_sesion_web('sinprestamos@example.test','ClavePrueba-2026'))
    def test_desktop_can_open_the_same_photo_with_zoom(self):
        from PySide6.QtWidgets import QApplication,QPushButton
        from ui.payments import PaymentsDialog
        from ui.comprobante_dialog import ComprobanteDialog
        app=QApplication.instance() or QApplication([])
        self.upload();id=self.payment()
        dialog=PaymentsDialog();self.assertTrue(any(b.text()=='Ver comprobante' for b in dialog.findChildren(QPushButton)))
        self.assertEqual(dialog.table.item(0,6).text(),'Adjunto')
        viewer=ComprobanteDialog(obtener_comprobante_pago(id));self.assertFalse(viewer.original.isNull());viewer.zoom(1.25);self.assertFalse(viewer.ajustado);viewer.ajustar();self.assertTrue(viewer.ajustado)
        viewer.close();dialog.close()

if __name__=='__main__':unittest.main()
