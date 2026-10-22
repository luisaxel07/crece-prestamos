from io import BytesIO
from datos_comprobantes import imagen_prueba
"""Presentación y flujo del portal, con servicios aislados de MySQL."""
import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import patch
from portal_web.app_web import aplicacion


class ClientPortalTests(unittest.TestCase):
    def setUp(self):
        aplicacion.config['TESTING'] = True
        self.client = aplicacion.test_client()
        fresh=patch('portal_web.seguridad_web.obtener_usuario_vigente',return_value=dict(id=23,rol='CLIENTE',nombre_usuario='cliente@example.test'))
        fresh.start();self.addCleanup(fresh.stop)
        self.token = 'csrf-de-prueba'
        with self.client.session_transaction() as session:
            session.update(version_sesion=1,usuario_id=23,rol='CLIENTE',nombre_usuario='cliente@example.test',token_csrf=self.token)

    def test_private_routes_reject_a_signed_out_session(self):
        visitor = aplicacion.test_client()
        for route in ['/inicio','/prestamos','/cuotas']:
            self.assertEqual(visitor.get(route).status_code,403)

    def test_quota_dates_and_customer_scope_are_preserved(self):
        records = [dict(id=2,prestamo_id=1,numero_cuota=2,fecha_vencimiento=date(2027,1,8),cuota_programada=Decimal('945.60'),saldo=Decimal('945.60'),estado='PENDIENTE'),dict(id=1,prestamo_id=1,numero_cuota=1,fecha_vencimiento=date(2026,12,8),cuota_programada=Decimal('945.60'),saldo=Decimal('945.60'),estado='PENDIENTE')]
        with patch('portal_web.app_web.listar_cuotas_cliente',return_value=records) as quotas, patch('portal_web.app_web.listar_solicitudes_pago_cliente',return_value=[]) as history:
            response = self.client.get('/cuotas?prestamo=999&usuario_id=999')
        quotas.assert_called_once_with(23)
        history.assert_called_once_with(23)
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code,200)
        self.assertLess(html.index('08/12/2026'),html.index('08/01/2027'))
        self.assertIn('Informar pago',html)
        self.assertIn('aria-labelledby="nombreCuota"',html)
        self.assertIn('El equipo lo verificará antes de confirmarlo.',html)

    def test_loan_percentage_is_readable_and_links_to_its_own_plan(self):
        record = dict(id=7,monto_principal=Decimal('10000'),saldo_pendiente=Decimal('9455.95'),cuota_mensual=Decimal('945.60'),fecha_desembolso=date(2026,9,8),tasa_interes_anual=Decimal('24.0000'),plazo_meses=12,estado='ACTIVO')
        with patch('portal_web.app_web.listar_prestamos_cliente',return_value=[record]) as loans:
            response = self.client.get('/prestamos')
        loans.assert_called_once_with(23)
        html = response.get_data(as_text=True)
        self.assertIn('24.00 %',html)
        self.assertNotIn('24.0000%',html)
        self.assertIn('/cuotas?prestamo=7#plan-cuotas',html)
        self.assertEqual(html.count('aria-current="page"'),2)

    def test_payment_form_keeps_csrf_and_server_verification_flow(self):
        with patch('portal_web.app_web.solicitar_pago') as notify:
            response = self.client.post('/pagos/solicitar',data={'token_csrf':'incorrecto','cuota_id':'5','monto':'945.60','referencia':'Prueba'})
            self.assertEqual(response.status_code,400)
            notify.assert_not_called()
            response = self.client.post('/pagos/solicitar',data={'token_csrf':self.token,'cuota_id':'5','monto':'945.60','referencia':'Referencia de prueba','comprobante':(BytesIO(imagen_prueba()),'comprobante.png')})
            self.assertEqual(response.status_code,302)
            notify.assert_called_once_with(23,5,Decimal('945.60'),'Referencia de prueba',comprobante=imagen_prueba())
        with self.client.session_transaction() as session:
            self.assertIn('verificará',session['_flashes'][-1][1])

    def test_empty_pages_render_without_inventing_amounts(self):
        with patch('portal_web.app_web.listar_cuotas_cliente',return_value=[]),patch('portal_web.app_web.listar_solicitudes_pago_cliente',return_value=[]):
            response = self.client.get('/cuotas')
        self.assertEqual(response.status_code,200)
        self.assertIn('No tienes cuotas para mostrar.',response.get_data(as_text=True))


if __name__=='__main__':
    unittest.main()
