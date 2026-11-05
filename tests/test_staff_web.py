from datos_comprobantes import imagen_prueba
"""Acceso web multirrol y operaciones reales sobre MySQL aislado."""
import unittest
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from sqlalchemy import select,func
from mysql_support import preparar_mysql
from crece.infraestructura.base_datos import configurar_motor,transaccion
from crece.infraestructura.modelos import Base,Usuario,Prestamo,Cliente,Pago
from crece.servicios.permisos import establecer_actor,_actor
from crece.servicios import gestion as servicios,cuentas_orm as cuentas
from crece.nucleo.seguridad import generar_hash_contrasena
from crece.servicios.reportes import obtener_reporte
from portal_web.app_web import aplicacion

class StaffWebTests(unittest.TestCase):
    def setUp(self):
        self.engine=preparar_mysql()
        with transaccion() as s:
            u=Usuario(nombre_usuario='admin_web',hash_contrasena=generar_hash_contrasena('PruebaSegura-2026'),rol='ADMINISTRADOR');s.add(u);s.flush();self.admin=u.id
        establecer_actor(self.admin)
        self.cid=servicios.registrar_cliente('001-150890-0001A','Cliente','Prueba','88888888','cliente@example.test')
        self.loan=servicios.registrar_prestamo(self.cid,Decimal('10000'),Decimal('24'),12,date(2026,9,8),date(2026,10,8),con_recargo=False)
        self.eid=servicios.guardar_empleado('001-190894-0101E','Asesor','Prueba','88888888','asesor@example.test','Asesor','asesor_web','PruebaSegura-2026')
        self.emp=servicios.listar_empleados()[0]['usuario_id']
        cuentas.crear_cuenta_cliente(self.cid,'cliente@example.test','PruebaSegura-2026')
        self.customer=cuentas.iniciar_sesion_web('cliente@example.test','PruebaSegura-2026')['id']
        aplicacion.config.update(TESTING=True,REPORT_TEMP_DIR=str(Path(__file__).parent))
        self.browser=aplicacion.test_client()
        establecer_actor(None)
    def tearDown(self):
        establecer_actor(None)
    def csrf(self,b=None):
        with (b or self.browser).session_transaction() as s: return s['token_csrf']
    def login(self,name='admin_web',b=None):
        b=b or self.browser;b.get('/acceso')
        return b.post('/api/auth/login',json=dict(username=name,password='PruebaSegura-2026',rol='ADMINISTRADOR'),headers={'X-CSRF-Token':self.csrf(b)})
    def post(self,path,data):
        return self.browser.post(path,data=dict(token_csrf=self.csrf(),**data))
    def test_three_roles_have_distinct_access_and_shared_credentials(self):
        for name,target,role in [('admin_web','/gestion/','ADMINISTRADOR'),('asesor_web','/gestion/','EMPLEADO'),('cliente@example.test','/inicio','CLIENTE')]:
            b=aplicacion.test_client();r=self.login(name,b)
            self.assertEqual(r.status_code,200);self.assertEqual(r.json['redirectUrl'],target);self.assertEqual(r.json['rol'],role)
            self.assertEqual(b.get(target).status_code,200)
            if role=='CLIENTE': self.assertEqual(b.get('/gestion/').status_code,403)
            else: self.assertEqual(b.get('/inicio').status_code,403)
        self.assertEqual(cuentas.iniciar_sesion('asesor_web','PruebaSegura-2026')['id'],self.emp)
        self.assertEqual(cuentas.iniciar_sesion_web('asesor@example.test','PruebaSegura-2026')['id'],self.emp)
    def test_all_staff_screens_render_admin(self):
        self.login()
        paths=['/gestion/','/gestion/clientes','/gestion/clientes/nuevo',f'/gestion/clientes/{self.cid}',f'/gestion/clientes/{self.cid}/editar','/gestion/prestamos','/gestion/prestamos/nuevo',f'/gestion/prestamos/{self.loan}',f'/gestion/prestamos/{self.loan}/notas','/gestion/cobros','/gestion/pagos','/gestion/simulador','/gestion/reportes','/gestion/empleados','/gestion/empleados/nuevo',f'/gestion/empleados/{self.eid}/editar','/gestion/usuarios','/gestion/usuarios/nuevo',f'/gestion/usuarios/{self.emp}/editar',f'/gestion/usuarios/{self.emp}/estado',f'/gestion/bajas/cliente/{self.cid}']
        for path in paths:
            with self.subTest(path=path): self.assertEqual(self.browser.get(path).status_code,200)
        self.assertIsNone(_actor.get())
    def test_staff_admin_routes_and_post_csrf_cannot_be_bypassed(self):
        self.login('asesor_web')
        for path in ['/gestion/empleados','/gestion/usuarios',f'/gestion/bajas/prestamo/{self.loan}',f'/gestion/usuarios/{self.admin}/estado']:
            self.assertEqual(self.browser.get(path).status_code,403)
            self.assertIn(self.post(path,{'activo':'0'}).status_code,(403,405))
        html=self.browser.get('/gestion/').get_data(as_text=True)
        self.assertNotIn('Cuentas y permisos</a>',html)
        self.assertEqual(self.browser.post('/gestion/clientes/nuevo',data={}).status_code,400)
        with transaccion() as s: self.assertEqual(s.scalar(select(func.count()).select_from(Cliente)),1)
    def test_anonymous_and_customer_cannot_read_staff_or_export(self):
        for path in ['/gestion/','/gestion/clientes','/gestion/reportes/pdf','/gestion/reportes/xlsx']:
            self.assertEqual(self.browser.get(path).status_code,403)
        self.login('cliente@example.test')
        for path in ['/gestion/','/gestion/clientes','/gestion/reportes/pdf','/gestion/reportes/xlsx']:
            self.assertEqual(self.browser.get(path).status_code,403)
    def test_disabled_account_is_revoked_on_next_request(self):
        self.login('asesor_web');establecer_actor(self.admin);cuentas.cambiar_estado_usuario(self.emp,False);establecer_actor(None)
        self.assertEqual(self.browser.get('/gestion/').status_code,403)
        self.assertEqual(self.browser.get('/api/auth/session').status_code,401)
        self.assertEqual(self.login('asesor_web').status_code,401)
    def test_current_database_role_overrides_old_session(self):
        self.login()
        with transaccion() as s: s.get(Usuario,self.admin).rol='EMPLEADO'
        self.assertEqual(self.browser.get('/gestion/usuarios').status_code,403)
        self.assertEqual(self.browser.get('/gestion/').status_code,200)
    def test_web_loan_records_real_employee_and_existing_contract_is_preserved(self):
        establecer_actor(self.admin);before=obtener_reporte(prestamo_id=self.loan)['prestamos'][0]['cuotas'];nuevo_cliente=servicios.registrar_cliente('001-160891-0002B','Nuevo','Cliente','88888888');establecer_actor(None)
        self.login('asesor_web')
        r=self.post('/gestion/prestamos/nuevo',dict(cliente_id=str(nuevo_cliente),tipo_credito='ASALARIADO',monto='6000',tasa='12',frecuencia='MENSUAL',meses='6',fecha_desembolso='2026-10-22',fecha_primera_cuota='2026-11-22',creado_por=str(self.admin),rol='ADMINISTRADOR'))
        self.assertEqual(r.status_code,302)
        with transaccion() as s:
            p=s.scalar(select(Prestamo).where(Prestamo.id!=self.loan));self.assertEqual(p.creado_por,self.emp);self.assertEqual(p.tasa_mensual,12);self.assertEqual(len(p.cuotas),6)
        establecer_actor(self.admin);self.assertEqual(before,obtener_reporte(prestamo_id=self.loan)['prestamos'][0]['cuotas']);establecer_actor(None)
        self.assertEqual(self.post('/gestion/prestamos/nuevo',dict(cliente_id=self.cid,monto='NaN',tasa=2,meses=6,fecha_desembolso='2026-10-22',fecha_primera_cuota='2026-11-22')).status_code,400)
    def test_customer_crud_and_credential_provisioning(self):
        self.login('asesor_web')
        fields=dict(cedula='001-160891-0002B',nombres='Otra',apellidos='Persona',telefono='88888888',correo='otra@example.test',direccion='Dirección')
        r=self.post('/gestion/clientes/nuevo',fields);self.assertEqual(r.status_code,302)
        id=int(r.location.rsplit('/',1)[1]);fields.update(nombres='Editada',estado='ACTIVO')
        self.assertEqual(self.post(f'/gestion/clientes/{id}/editar',fields).status_code,302)
        self.assertEqual(self.post(f'/gestion/clientes/{id}/cuenta',dict(correo='otra@example.test',contrasena='PruebaSegura-2026')).status_code,302)
        self.assertEqual(cuentas.iniciar_sesion_web('otra@example.test','PruebaSegura-2026')['rol'],'CLIENTE')
    def test_collection_and_client_payment_review_use_shared_services(self):
        self.login('asesor_web')
        establecer_actor(self.admin);q=obtener_reporte(prestamo_id=self.loan)['prestamos'][0]['cuotas'][0];establecer_actor(None)
        self.assertEqual(self.browser.get(f'/gestion/cobros/{q["id"]}').status_code,200)
        self.assertEqual(self.post(f'/gestion/cobros/{q["id"]}',dict(monto='100',metodo='EFECTIVO',referencia='WEB-001')).status_code,302)
        with transaccion() as s:
            p=s.scalar(select(Pago));pid=p.id;self.assertEqual(p.registrado_por,self.emp);self.assertEqual(p.cuota.monto_pagado,100)
        self.assertEqual(self.browser.get(f'/gestion/pagos/{pid}').status_code,200)
        self.assertEqual(self.post(f'/gestion/pagos/{pid}',dict(accion='ANULAR',motivo='No autorizado')).status_code,400)
        self.assertEqual(self.post(f'/gestion/pagos/{pid}',dict(accion='EDITAR_REFERENCIA',motivo='Referencia editada')).status_code,302)
    def test_web_review_applies_customer_notice_once(self):
        from crece.servicios.portal_orm import solicitar_pago
        establecer_actor(self.admin)
        q=obtener_reporte(prestamo_id=self.loan)['prestamos'][0]['cuotas'][0]
        establecer_actor(None)
        payment=solicitar_pago(self.customer,q['id'],Decimal('100'),'Transferencia por verificar',comprobante=imagen_prueba())
        self.login('asesor_web')
        self.assertEqual(self.post(f'/gestion/pagos/{payment}',dict(accion='CONFIRMAR',motivo='')).status_code,302)
        self.assertEqual(self.post(f'/gestion/pagos/{payment}',dict(accion='CONFIRMAR',motivo='')).status_code,400)
        with transaccion() as db:
            p=db.get(Pago,payment);self.assertEqual(p.estado,'CONFIRMADO');self.assertEqual(p.cuota.monto_pagado,100);self.assertEqual(p.registrado_por,self.emp)

    def test_reports_export_brand_scope_and_private_cache(self):
        establecer_actor(self.admin)
        other=servicios.registrar_cliente('001-180893-0004D','Ajeno','Al reporte','88888888')
        servicios.registrar_prestamo_mensual(other,Decimal('6000'),Decimal('3'),6,date(2026,10,22),date(2026,11,22))
        establecer_actor(None)
        self.login()
        from openpyxl import load_workbook
        r=self.browser.get(f'/gestion/reportes/xlsx?cliente_id={self.cid}')
        self.assertEqual(r.status_code,200);self.assertEqual(r.headers['Cache-Control'],'no-store')
        wb=load_workbook(BytesIO(r.data));self.assertEqual(wb.sheetnames,['Resumen','Préstamos','Cuotas','Pagos periodo'])
        self.assertTrue(all(ws._images for ws in wb));self.assertEqual(wb['Cuotas'].max_row,21)
        self.assertFalse(any('Ajeno' in str(c.value) for row in wb['Cuotas'] for c in row))
        r=self.browser.get(f'/gestion/reportes/pdf?prestamo_id={self.loan}&vista=1')
        self.assertEqual(r.status_code,200);self.assertTrue(r.data.startswith(b'%PDF'));self.assertTrue(r.headers['Content-Disposition'].startswith('inline'))
        self.assertEqual(self.browser.get('/gestion/reportes?cliente_id=abc').status_code,400)
        r=self.browser.get('/gestion/reportes/xlsx?q=sin-coincidencia');wb=load_workbook(BytesIO(r.data));self.assertEqual(wb['Préstamos'].max_row,9)
    def test_employee_crud_and_admin_protection(self):
        self.login()
        fields=dict(cedula='001-200895-0102F',nombres='Otra',apellidos='Asesora',telefono='88888888',correo='otraempleada@example.test',cargo='Asesora',nombre_usuario='otra_asesora',contrasena='PruebaSegura-2026',activo='1')
        self.assertEqual(self.post('/gestion/empleados/nuevo',fields).status_code,302)
        establecer_actor(self.admin);new=next(e for e in servicios.listar_empleados() if e['cedula']=='001-200895-0102F');establecer_actor(None)
        fields.update(cargo='Supervisora',contrasena='',activo='0');self.assertEqual(self.post(f'/gestion/empleados/{new["id"]}/editar',fields).status_code,302)
        self.assertIsNone(cuentas.iniciar_sesion_web('otra_asesora','PruebaSegura-2026'))
        self.assertEqual(self.post(f'/gestion/usuarios/{self.admin}/estado',dict(activo='0')).status_code,400)
        self.assertEqual(self.post(f'/gestion/bajas/empleado/{new["id"]}',dict(confirmacion='SI')).status_code,302)
    def test_simulator_does_not_issue_and_invalid_forms_do_not_mutate(self):
        self.login()
        r=self.post('/gestion/simulador',dict(tipo_credito='ASALARIADO',monto='10000',tasa='12',frecuencia='MENSUAL',meses='12',fecha_primera_cuota='2026-11-22'))
        self.assertEqual(r.status_code,200);self.assertIn('Plan de cuotas',r.get_data(as_text=True))
        r=self.post('/gestion/clientes/nuevo',dict(cedula='001-170892-0003C',nombres='<script>alert(1)</script>',apellidos='X',telefono='x',correo='incorrecto'))
        self.assertEqual(r.status_code,400);self.assertNotIn(b'<script>alert(1)</script>',r.data)
        with transaccion() as s:self.assertEqual(s.scalar(select(func.count()).select_from(Prestamo)),1)
    def test_independent_sessions_do_not_leak_actor_and_csrf_rotates(self):
        original=establecer_actor(987)
        try:
            self.login();self.assertEqual(_actor.get(),987)
            employee=aplicacion.test_client();self.login('asesor_web',employee)
            self.assertEqual(employee.get('/gestion/usuarios').status_code,403)
            self.assertEqual(self.browser.get('/gestion/usuarios').status_code,200)
            self.assertEqual(_actor.get(),987)
        finally:
            from crece.servicios.permisos import restablecer_actor
            restablecer_actor(original)

    def test_frequency_selection_is_persisted_and_duplicate_loan_warns(self):
        self.login('asesor_web')
        datos=dict(cliente_id=self.cid,tipo_credito='ASALARIADO',monto='1000',tasa='12',meses='4',frecuencia='SEMANAL',fecha_desembolso='2026-10-22',fecha_primera_cuota='2026-11-10')
        respuesta=self.post('/gestion/prestamos/nuevo',datos)
        self.assertEqual(respuesta.status_code,400)
        self.assertIn('ya tiene asignado',respuesta.get_data(as_text=True))
        establecer_actor(self.admin)
        nuevo=servicios.registrar_cliente('001-170892-0003C','Otra','Persona','88888888')
        establecer_actor(None);datos['cliente_id']=nuevo
        respuesta=self.post('/gestion/prestamos/nuevo',datos);self.assertEqual(respuesta.status_code,302)
        with transaccion() as s:
            p=s.scalar(select(Prestamo).where(Prestamo.cliente_id==nuevo))
            self.assertEqual(p.frecuencia,'SEMANAL');self.assertEqual(p.numero_cuotas,4)
            self.assertEqual(p.cuotas[1].fecha_vencimiento,date(2026,11,17))
            self.assertEqual(p.recargo_porcentaje,1)
        detalle=self.browser.get(respuesta.location).get_data(as_text=True)
        self.assertIn('Tasa del período',detalle);self.assertIn('Recargo total',detalle)
        datos['frecuencia']='OTRA';self.assertEqual(self.post('/gestion/prestamos/nuevo',datos).status_code,400)

    def test_simulator_all_four_frequencies_require_valid_selection(self):
        self.login()
        for frecuencia in ('MENSUAL','QUINCENAL','SEMANAL','DIARIO'):
            respuesta=self.post('/gestion/simulador',dict(tipo_credito='ASALARIADO',monto='1000',tasa='12',meses='4',frecuencia=frecuencia,fecha_primera_cuota='2026-11-10'))
            self.assertEqual(respuesta.status_code,200)
            self.assertIn('Tasa del periodo',respuesta.get_data(as_text=True))
        self.assertEqual(self.post('/gestion/simulador',dict(tipo_credito='ASALARIADO',monto='1000',tasa='12',meses='4',frecuencia='OTRA',fecha_primera_cuota='2026-11-10')).status_code,400)

if __name__=='__main__':unittest.main()

