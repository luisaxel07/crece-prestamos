from datos_comprobantes import imagen_prueba
"""Integración real de entidades/servicios en MySQL aislado; sin alterar la base del proyecto."""
import tempfile
import unittest
from pathlib import Path
from datetime import date
from decimal import Decimal
from sqlalchemy import select, func
from mysql_support import preparar_mysql
from crece.infraestructura.base_datos import configurar_motor, transaccion
from crece.infraestructura.modelos import Base, Usuario, Cliente, Prestamo, CuotaModel, Pago
from crece.servicios.permisos import establecer_actor
from crece.servicios import gestion as g, cuentas_orm as cuentas, portal_orm as portal
from crece.servicios.reportes import obtener_reporte, limitar_reporte
from crece.nucleo.amortizacion import calcular_tabla_francesa, calcular_tabla_mensual


class OrmManagementTests(unittest.TestCase):
    def setUp(self):
        self.engine=preparar_mysql()
        with transaccion() as s:
            user=Usuario(nombre_usuario='admin_prueba',hash_contrasena='sin_acceso',rol='ADMINISTRADOR')
            s.add(user);s.flush();self.admin=user.id
        establecer_actor(self.admin)
        self.client=g.registrar_cliente('001-150890-0001A','Cliente','De prueba','88888888','cliente@example.test','Dirección de prueba')

    def tearDown(self):
        establecer_actor(None)

    def loan(self,client=None):
        return g.registrar_prestamo(client or self.client,Decimal('10000'),Decimal('24'),12,date(2026,9,8),date(2026,10,8))

    def employee(self):
        return g.guardar_empleado('001-190894-0101E','Asesor','Prueba','88888888','asesor@example.test','Asesor de crédito','asesor_prueba','ClavePrueba-2026')

    def test_monthly_equals_annual_without_modifying_persisted_quotas(self):
        self.assertEqual(calcular_tabla_francesa(Decimal('10000'),Decimal('24'),12,date(2026,10,8)),calcular_tabla_mensual(Decimal('10000'),Decimal('2'),12,date(2026,10,8)))
        loan=self.loan()
        before=obtener_reporte(prestamo_id=loan)
        g.actualizar_prestamo(loan,'Observación actualizada')
        after=obtener_reporte(prestamo_id=loan)
        self.assertEqual(before['prestamos'][0]['cuotas'],after['prestamos'][0]['cuotas'])
        self.assertEqual(after['prestamos'][0]['tasa_mensual'],Decimal('2'))
        self.assertEqual(after['prestamos'][0]['creado_por'],self.admin)
        self.assertEqual(sum(q['abono_capital'] for q in after['prestamos'][0]['cuotas']),Decimal('10000'))

    def test_employee_credentials_active_gate_and_issuer(self):
        self.employee()
        employee=g.listar_empleados()[0]
        self.assertIsNone(cuentas.iniciar_sesion('asesor_prueba','incorrecta'))
        login=cuentas.iniciar_sesion('asesor_prueba','ClavePrueba-2026')
        self.assertEqual(login['rol'],'EMPLEADO')
        establecer_actor(login['id'])
        loan=self.loan()
        self.assertEqual(obtener_reporte(prestamo_id=loan)['prestamos'][0]['creado_por'],login['id'])
        with self.assertRaises(ValueError): g.listar_empleados()
        establecer_actor(self.admin)
        cuentas.cambiar_estado_usuario(employee['usuario_id'],False)
        self.assertIsNone(cuentas.iniciar_sesion('asesor_prueba','ClavePrueba-2026'))
        establecer_actor(login['id'])
        with self.assertRaises(ValueError): self.loan()

    def test_employee_crud_and_history_preservation(self):
        id=self.employee()
        g.guardar_empleado('001-190894-0101E','Asesora','Editada','99999999','','Supervisora','asesor_prueba','',empleado_id=id)
        self.assertEqual(g.listar_empleados()[0]['cargo'],'Supervisora')
        self.assertEqual(g.eliminar_empleado(id),'ELIMINADO')
        self.assertEqual(g.listar_empleados(),[])
        self.employee()
        employee=g.listar_empleados()[0]
        establecer_actor(employee['usuario_id']);self.loan();establecer_actor(self.admin)
        self.assertEqual(g.eliminar_empleado(employee['id']),'DESACTIVADO')
        self.assertFalse(g.listar_empleados()[0]['activo'])

    def test_client_crud_and_linked_records(self):
        other=g.registrar_cliente('001-160891-0002B','Otra','Persona','88888888')
        g.actualizar_cliente(other,'001-160891-0002B','Otra','Editada','99999999')
        self.assertEqual(g.obtener_cliente(other)['apellidos'],'Editada')
        self.assertEqual(g.eliminar_cliente(other),'ELIMINADO')
        loan=self.loan()
        self.assertEqual(g.eliminar_cliente(self.client),'INACTIVADO')
        self.assertEqual(len(obtener_reporte(prestamo_id=loan)['prestamos'][0]['cuotas']),12)
        with self.assertRaises(ValueError): self.loan()

    def test_duplicate_rolls_back_and_last_admin_is_protected(self):
        with self.assertRaises(ValueError): g.registrar_cliente('001-150890-0001A','Duplicado','Prueba','88888888')
        self.assertEqual(len(g.listar_clientes()),1)
        with self.assertRaises(ValueError): cuentas.cambiar_estado_usuario(self.admin,False)
        with self.assertRaises(ValueError): cuentas.eliminar_usuario(self.admin)

    def test_cancel_issued_loan_preserves_quotas_excludes_totals(self):
        loan=self.loan()
        self.assertEqual(g.eliminar_prestamo(loan,'Error de captura'),'ANULADO')
        report=obtener_reporte(prestamo_id=loan)
        self.assertEqual(len(report['prestamos'][0]['cuotas']),12)
        self.assertEqual(report['prestamos'][0]['estado'],'CANCELADO')
        self.assertEqual(report['totales']['saldo'],0)
        self.assertEqual(g.listar_cuotas_cobro(),[])

    def test_payments_reconcile_and_annul_without_erasing_history(self):
        loan=self.loan();report=obtener_reporte(prestamo_id=loan)
        q=report['prestamos'][0]['cuotas'][0]
        with self.assertRaises(ValueError): g.registrar_cobro(q['id'],q['saldo']+1,'EFECTIVO')
        self.assertEqual(g.listar_pagos(),[])
        payment=g.registrar_cobro(q['id'],q['saldo'],'EFECTIVO')
        paid=obtener_reporte(prestamo_id=loan)
        self.assertEqual(paid['totales']['programado'],paid['totales']['cobrado']+paid['totales']['saldo'])
        with self.assertRaises(ValueError): g.eliminar_prestamo(loan,'No permitido')
        g.resolver_pago(payment,'EDITAR_REFERENCIA','Recibo corregido')
        g.resolver_pago(payment,'ANULAR','Captura duplicada')
        self.assertEqual(g.listar_pagos()[0]['estado'],'ANULADO')
        self.assertEqual(obtener_reporte(prestamo_id=loan)['totales']['saldo'],report['totales']['saldo'])

    def test_portal_ownership_pending_confirmation_and_revoked_access(self):
        self.loan()
        cuentas.crear_cuenta_cliente(self.client,'cliente@example.test','ClavePrueba-2026')
        client_login=cuentas.iniciar_sesion_cliente_por_correo('cliente@example.test','ClavePrueba-2026')
        other=g.registrar_cliente('001-160891-0002B','Otro','Cliente','88888888')
        other_loan=self.loan(other)
        foreign_quota=obtener_reporte(prestamo_id=other_loan)['prestamos'][0]['cuotas'][0]
        with self.assertRaises(ValueError): portal.solicitar_pago(client_login['id'],foreign_quota['id'],10,'No propio',comprobante=imagen_prueba())
        quotas=portal.listar_cuotas_cliente(client_login['id'])
        self.assertEqual(len(quotas),12)
        q=quotas[0]
        payment=portal.solicitar_pago(client_login['id'],q['id'],q['saldo'],'Transferencia prueba',comprobante=imagen_prueba())
        self.assertEqual(portal.listar_cuotas_cliente(client_login['id'])[0]['saldo'],q['saldo'])
        with self.assertRaises(ValueError): portal.solicitar_pago(client_login['id'],q['id'],q['saldo'],'Duplicada',comprobante=imagen_prueba())
        g.resolver_pago(payment,'CONFIRMAR')
        self.assertEqual(portal.listar_cuotas_cliente(client_login['id'])[0]['saldo'],0)
        with self.assertRaises(ValueError): g.resolver_pago(payment,'CONFIRMAR')
        cuentas.cambiar_estado_usuario(client_login['id'],False)
        with self.assertRaises(ValueError): portal.listar_cuotas_cliente(client_login['id'])

    def test_report_scope_and_visible_filters(self):
        loan=self.loan()
        other=g.registrar_cliente('001-160891-0002B','Otro','Cliente','88888888')
        self.loan(other)
        report=obtener_reporte(cliente_id=self.client)
        self.assertEqual([p['id'] for p in report['prestamos']],[loan])
        self.assertEqual(report['cliente']['cedula'],'001-150890-0001A')
        empty=limitar_reporte(obtener_reporte(),set())
        self.assertEqual(empty['prestamos'],[])
        self.assertEqual(empty['totales']['saldo'],0)

    def test_cancel_export_preserves_existing_destination(self):
        from ui.export_worker import guardar_atomico,ExportacionCancelada
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            target=Path(folder)/'existente.xlsx'
            target.write_bytes(b'original')
            with self.assertRaises(ExportacionCancelada): guardar_atomico({},target,'xlsx',cancelado=lambda:True)
            self.assertEqual(target.read_bytes(),b'original')
            self.assertEqual(list(Path(folder).iterdir()),[target])


if __name__=='__main__': unittest.main()
