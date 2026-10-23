"""Un crédito pendiente por cliente; validación transaccional real en MySQL."""
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from sqlalchemy import select,func
import test_orm_management as fixtures
from crece.infraestructura.base_datos import transaccion
from crece.infraestructura.modelos import Prestamo,CuotaModel,Usuario
from crece.servicios import gestion as g
from crece.servicios.permisos import establecer_actor

class PrestamoUnicoTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.OrmManagementTests();self.fixture.setUp()
        self.cliente=self.fixture.client;self.admin=self.fixture.admin
    def tearDown(self):self.fixture.tearDown()
    def emitir(self,actor=None):
        return g.registrar_prestamo(self.cliente,Decimal('1000'),Decimal('24'),2,date(2026,10,1),date(2026,11,1),actor_id=actor)
    def test_second_loan_warns_and_does_not_create_rows(self):
        id=self.emitir()
        with self.assertRaisesRegex(ValueError,'ya tiene asignado.*sin saldar.*cuando haya saldado'):
            self.emitir()
        with transaccion() as s:
            self.assertEqual(s.scalar(select(func.count()).select_from(Prestamo)),1)
            self.assertEqual(s.scalar(select(func.count()).select_from(CuotaModel)),2)
    def test_partial_or_overdue_installment_still_blocks_new_loan(self):
        id=self.emitir();q=next(p for p in g.listar_prestamos() if p['id']==id)
        with transaccion() as s:cuota=s.scalar(select(CuotaModel).where(CuotaModel.prestamo_id==id));qid=cuota.id
        g.registrar_cobro(qid,Decimal('1'),'EFECTIVO')
        with self.assertRaises(ValueError):self.emitir()
    def test_fully_settled_contract_allows_new_loan_and_preserves_history(self):
        id=self.emitir()
        with transaccion() as s:cuotas=[(q.id,q.saldo) for q in s.scalars(select(CuotaModel).where(CuotaModel.prestamo_id==id))]
        for qid,saldo in cuotas:g.registrar_cobro(qid,saldo,'EFECTIVO')
        nuevo=self.emitir();self.assertNotEqual(id,nuevo)
        with transaccion() as s:self.assertEqual(s.scalar(select(func.count()).select_from(Prestamo)),2)
    def test_cancelled_contract_does_not_block_new_loan(self):
        id=self.emitir();g.eliminar_prestamo(id,'Anulación de contrato de prueba')
        self.assertNotEqual(id,self.emitir())
    def test_two_distinct_operators_cannot_issue_simultaneously(self):
        with transaccion() as s:
            user=Usuario(nombre_usuario='otro_operador_prueba',hash_contrasena='sin_acceso',rol='EMPLEADO');s.add(user);s.flush();otro=user.id
        def intentar(actor):
            try:return self.emitir(actor)
            except ValueError:return None
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(intentar,(self.admin,otro)))
        self.assertEqual(sum(r is not None for r in results),1)
        with transaccion() as s:self.assertEqual(s.scalar(select(func.count()).select_from(Prestamo)),1)

if __name__=='__main__':unittest.main()
