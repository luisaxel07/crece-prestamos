"""Calendarios y motor francés por período; sin persistencia ni cuotas ficticias en producción."""
import unittest
from datetime import date,timedelta
from decimal import Decimal
from crece.nucleo.amortizacion import calcular_tabla_francesa,calcular_tabla_mensual,calcular_tabla_periodica

class FrecuenciasTests(unittest.TestCase):
    def plan(self,frecuencia,tasa='2',n=4,fecha=date(2026,1,31)):
        return calcular_tabla_periodica(Decimal('10000'),Decimal(tasa),n,fecha,frecuencia)
    def test_monthly_contract_matches_original_annual_calculation(self):
        for tasa in ('0','2','0.1234'):
            self.assertEqual(self.plan('MENSUAL',tasa),calcular_tabla_mensual(Decimal('10000'),Decimal(tasa),4,date(2026,1,31)))
        self.assertEqual([q.fecha_vencimiento for q in self.plan('MENSUAL')],[date(2026,1,31),date(2026,2,28),date(2026,3,31),date(2026,4,30)])
    def test_fifteen_seven_and_one_calendar_day_intervals(self):
        for frecuencia,dias in [('QUINCENAL',15),('SEMANAL',7),('DIARIO',1)]:
            plan=self.plan(frecuencia)
            self.assertEqual([q.fecha_vencimiento for q in plan],[date(2026,1,31)+timedelta(days=dias*i) for i in range(4)])
            self.assertEqual(sum(q.abono_capital for q in plan),Decimal('10000'))
            self.assertEqual(plan[-1].saldo_final,0)
    def test_leap_day_and_year_end_are_real_calendar_dates(self):
        plan=self.plan('DIARIO',fecha=date(2028,2,28))
        self.assertEqual(plan[1].fecha_vencimiento,date(2028,2,29))
        self.assertEqual(self.plan('SEMANAL',fecha=date(2026,12,31))[1].fecha_vencimiento,date(2027,1,7))
    def test_period_rate_and_money_are_applied_once_each_installment(self):
        for frecuencia in ('MENSUAL','QUINCENAL','SEMANAL','DIARIO'):
            plan=self.plan(frecuencia,tasa='1')
            self.assertEqual(plan[0].interes,Decimal('100.00'))
            self.assertEqual(sum(q.pago for q in plan),Decimal('10000')+sum(q.interes for q in plan))
    def test_zero_interest_and_invalid_inputs(self):
        self.assertEqual(sum(q.pago for q in self.plan('SEMANAL','0')),Decimal('10000'))
        for frecuencia,tasa,n in [('OTRA','2',4),('SEMANAL','-1',4),('DIARIO','NaN',4),('MENSUAL','2',0),('MENSUAL','2',601),('SEMANAL','2',1.5),('SEMANAL','2',True)]:
            with self.subTest(frecuencia=frecuencia,tasa=tasa,n=n),self.assertRaises(ValueError):self.plan(frecuencia,tasa,n)

    def test_issuance_rejects_overflowing_installment_before_opening_transaction(self):
        from unittest.mock import patch
        from crece.servicios.gestion import registrar_prestamo_periodico
        with patch('crece.servicios.gestion.transaccion') as abrir:
            with self.assertRaisesRegex(ValueError,'fuera del rango'):
                registrar_prestamo_periodico(1,Decimal('999999999999.99'),Decimal('2'),1,date(2026,9,1),date(2026,10,1))
            abrir.assert_not_called()

if __name__=='__main__':unittest.main()
