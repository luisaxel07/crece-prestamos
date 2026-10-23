"""Gracia y recargo calculados con Decimal y un reloj explícito, sin datos reales."""
import unittest
from types import SimpleNamespace as NS
from datetime import date,datetime,timedelta
from decimal import Decimal as D
from crece.nucleo.mora import detalle_mora,limite_gracia,ahora_local
from crece.nucleo.amortizacion import calcular_tabla_credito,tasa_por_periodo

class MoraTests(unittest.TestCase):
    def cuota(self,porcentaje='1',pagos=()):
        return NS(prestamo=NS(recargo_porcentaje=D(porcentaje),gracia_horas=72,estado='ACTIVO'),fecha_vencimiento=date(2026,10,1),cuota_programada=D('1100'),monto_pagado=D('0'),interes=D('100'),abono_capital=D('1000'),recargo_pagado=D('0'),pagos=list(pagos))
    def pago(self,monto,fecha,estado='CONFIRMADO',recargo='0'):
        return NS(monto=D(monto),fecha_pago=fecha,estado=estado,monto_recargo=D(recargo))
    def test_due_day_grace_and_exact_boundary(self):
        q=self.cuota();limite=limite_gracia(q.fecha_vencimiento)
        self.assertEqual(limite,datetime(2026,10,5))
        self.assertEqual(detalle_mora(q,datetime(2026,10,1,12))['aviso_pago'],'VENCE_HOY')
        self.assertEqual(detalle_mora(q,datetime(2026,10,4,23,59))['aviso_pago'],'EN_GRACIA')
        self.assertEqual(detalle_mora(q,limite)['recargo'],0)
        self.assertEqual(detalle_mora(q,limite+timedelta(microseconds=1))['recargo'],D('10'))
        self.assertEqual(ahora_local().microsecond,0)
    def test_partial_early_payment_interest_first_and_fixed_uncompounded_charge(self):
        q=self.cuota(pagos=[self.pago('600',datetime(2026,10,3))]);q.monto_pagado=D('600')
        detalle=detalle_mora(q,datetime(2026,10,6))
        self.assertEqual(detalle['capital_base_mora'],D('500'))
        self.assertEqual(detalle['recargo'],D('5'))
        q.pagos.append(self.pago('500',datetime(2026,10,6)));q.monto_pagado=D('1100')
        self.assertEqual(detalle_mora(q,datetime(2027,10,6))['saldo_total'],D('5'))
        q.recargo_pagado=D('5')
        self.assertEqual(detalle_mora(q,datetime(2027,10,6))['saldo_total'],0)
    def test_full_payment_inside_grace_and_legacy_contract_never_charge(self):
        q=self.cuota(pagos=[self.pago('1100',datetime(2026,10,4,23,59,59))]);q.monto_pagado=D('1100')
        self.assertEqual(detalle_mora(q,datetime(2026,10,20))['recargo'],0)
        self.assertEqual(detalle_mora(self.cuota('0'),datetime(2030,1,1))['recargo'],0)
    def test_unverified_or_voided_receipts_do_not_reduce_penalty_base(self):
        for estado in ('PENDIENTE_VERIFICACION','RECHAZADO','ANULADO'):
            q=self.cuota(pagos=[self.pago('1100',datetime(2026,10,2),estado)])
            self.assertEqual(detalle_mora(q,datetime(2026,10,6))['recargo'],D('10'))
    def test_confirmed_conversions_and_installment_count(self):
        expected={'MENSUAL':D('2'),'QUINCENAL':D('1'),'SEMANAL':D('2')*12/52,'DIARIO':D('2')/30}
        for frecuencia,tasa in expected.items():
            self.assertEqual(tasa_por_periodo(D('2'),frecuencia),tasa)
            plan=calcular_tabla_credito(D('10000'),D('2'),12,date(2026,10,1),frecuencia)
            self.assertEqual(len(plan),12)
            self.assertEqual(sum(q.abono_capital for q in plan),D('10000'))
            self.assertEqual(plan[-1].saldo_final,0)

if __name__=='__main__':unittest.main()
