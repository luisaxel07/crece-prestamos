"""Frecuencias, mora y verificación de transferencias en MySQL exclusivo de pruebas."""
import unittest
from contextlib import contextmanager,ExitStack
from datetime import date,datetime,timedelta
from decimal import Decimal as D
from unittest.mock import patch
from sqlalchemy import select
import test_orm_management as fixtures
from datos_comprobantes import imagen_prueba
from crece.infraestructura.base_datos import transaccion
from crece.infraestructura.modelos import Usuario,Cliente,Prestamo,CuotaModel,Pago
from crece.servicios import gestion as g,portal_orm as portal
from crece.servicios.reportes import obtener_reporte
from crece.nucleo.amortizacion import calcular_tabla_credito,FRECUENCIAS

@contextmanager
def reloj(fecha):
    with ExitStack() as stack:
        for modulo in ('crece.nucleo.mora','crece.servicios.gestion','crece.servicios.portal_orm'):
            stack.enter_context(patch(modulo+'.ahora_local',return_value=fecha))
        yield

class FrecuenciaMoraMysqlTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.OrmManagementTests();self.fixture.setUp();self.cid=self.fixture.client
    def tearDown(self):self.fixture.tearDown()
    def emitir(self,frecuencia='MENSUAL',numero=1,cliente=None):
        return g.registrar_prestamo_periodico(cliente or self.cid,D('1000'),D('2'),numero,date(2026,9,1),date(2026,10,1),frecuencia)
    def cuota(self,id):return obtener_reporte(prestamo_id=id)['prestamos'][0]['cuotas'][0]
    def cuenta_cliente(self):
        with transaccion() as s:
            u=Usuario(nombre_usuario='cliente_mora',hash_contrasena='sin_acceso',rol='CLIENTE');s.add(u);s.flush()
            s.get(Cliente,self.cid).usuario_id=u.id;return u.id
    def test_four_persisted_calendars_match_shared_engine(self):
        with reloj(datetime(2026,9,1)):
            for i,frecuencia in enumerate(FRECUENCIAS):
                cid=self.cid if i==0 else g.registrar_cliente(f'001-150890-{i+1:04d}A','Otra','Persona','88888888')
                id=self.emitir(frecuencia,4,cid);p=obtener_reporte(prestamo_id=id)['prestamos'][0]
                esperado=calcular_tabla_credito(D('1000'),D('2'),4,date(2026,10,1),frecuencia)
                self.assertEqual(p['frecuencia'],frecuencia);self.assertEqual(p['numero_cuotas'],4)
                self.assertEqual(p['recargo_porcentaje'],1)
                self.assertEqual([q['fecha_vencimiento'] for q in p['cuotas']],[q.fecha_vencimiento for q in esperado])
                self.assertEqual([q['interes'] for q in p['cuotas']],[q.interes for q in esperado])
                self.assertEqual(sum(q['abono_capital'] for q in p['cuotas']),1000)
    def test_grace_partial_payment_fixed_fee_final_installment_and_new_loan_gate(self):
        with reloj(datetime(2026,10,3)):
            id=self.emitir();q=self.cuota(id);qid=q['id'];g.registrar_cobro(qid,D('520'),'EFECTIVO')
            self.assertEqual(self.cuota(id)['recargo'],0)
        with reloj(datetime(2026,10,6)):
            q=self.cuota(id);self.assertEqual(q['recargo'],D('5'));self.assertEqual(q['capital_base_mora'],500)
            g.registrar_cobro(qid,D('500'),'EFECTIVO')
            self.assertEqual(self.cuota(id)['saldo'],5)
            with self.assertRaisesRegex(ValueError,'ya tiene asignado'):self.emitir()
            pago=g.registrar_cobro(qid,D('5'),'EFECTIVO')
            self.assertEqual(self.cuota(id)['saldo'],0)
            report=obtener_reporte(prestamo_id=id)
            self.assertEqual(report['totales']['cobrado'],D('1025'))
            self.assertEqual(report['totales']['recargos_cobrados'],5)
            self.assertNotEqual(self.emitir(),id)
            g.resolver_pago(pago,'ANULAR','Corrección de prueba')
            self.assertEqual(self.cuota(id)['recargo_pendiente'],5)
            with transaccion() as s:self.assertEqual(s.get(Pago,pago).monto_recargo,5)
        with reloj(datetime(2027,10,6)):self.assertEqual(self.cuota(id)['recargo'],5)
    def test_transfer_submitted_in_grace_and_confirmed_later_has_no_fee(self):
        uid=self.cuenta_cliente()
        with reloj(datetime(2026,10,3)):
            id=self.emitir();q=self.cuota(id)
            pago=portal.solicitar_pago(uid,q['id'],D('1020'),'Referencia comprobada',imagen_prueba())
            with self.assertRaisesRegex(ValueError,'solicitud pendiente'):g.registrar_cobro(q['id'],D('1'),'EFECTIVO')
        with reloj(datetime(2026,10,8)):
            self.assertEqual(self.cuota(id)['recargo'],10)
            g.resolver_pago(pago,'CONFIRMAR')
            q=self.cuota(id);self.assertEqual(q['recargo'],0);self.assertEqual(q['saldo'],0)
            with self.assertRaises(ValueError):g.resolver_pago(pago,'CONFIRMAR')
    def test_notifications_from_due_day_and_legacy_untouched(self):
        uid=self.cuenta_cliente()
        with reloj(datetime(2026,9,1)):id=self.emitir()
        for fecha,aviso in [(datetime(2026,9,30),''),(datetime(2026,10,1,12),'VENCE_HOY'),(datetime(2026,10,4,23),'EN_GRACIA'),(datetime(2026,10,5,0,0,1),'VENCIDA')]:
            with reloj(fecha):self.assertEqual(portal.listar_cuotas_cliente(uid)[0]['aviso_pago'],aviso)
        with reloj(datetime(2026,10,6)):
            otro=g.registrar_cliente('001-160891-0002B','Anterior','Cliente','88888888')
            viejo=g.registrar_prestamo(otro,D('1000'),D('24'),1,date(2026,9,1),date(2026,10,1),con_recargo=False)
            self.assertEqual(self.cuota(viejo)['recargo'],0)
            self.assertEqual(len(portal.listar_prestamos_cliente(uid)),1)
    def test_fee_only_payment_and_reversal_are_allocated_and_audited(self):
        with reloj(datetime(2026,10,6)):
            id=self.emitir();q=self.cuota(id)
            pago=g.registrar_cobro(q['id'],D('1030'),'EFECTIVO')
            q=self.cuota(id);self.assertEqual(q['monto_pagado'],1020);self.assertEqual(q['recargo_pagado'],10)
            g.resolver_pago(pago,'ANULAR','Revisión de pago')
            q=self.cuota(id);self.assertEqual(q['saldo'],1030);self.assertEqual(q['recargo_pagado'],0)
            self.assertEqual(q['monto_pagado'],0)
            with self.assertRaises(ValueError):g.registrar_cobro(q['id'],D('1030.01'),'EFECTIVO')

    def test_receipt_at_exact_grace_boundary_uses_one_payment_timestamp(self):
        with reloj(datetime(2026,10,1)):
            id=self.emitir();qid=self.cuota(id)['id']
        limite=datetime(2026,10,5)
        with patch('crece.servicios.gestion.ahora_local',return_value=limite),patch('crece.nucleo.mora.ahora_local',return_value=limite+timedelta(seconds=1)):
            pago=g.registrar_cobro(qid,D('1020'),'EFECTIVO')
        with reloj(datetime(2026,10,6)):
            self.assertEqual(self.cuota(id)['saldo'],0)
            with transaccion() as s:
                self.assertEqual(s.get(Pago,pago).fecha_pago,limite)
                self.assertEqual(s.get(Prestamo,id).estado,'FINALIZADO')

if __name__=='__main__':unittest.main()
