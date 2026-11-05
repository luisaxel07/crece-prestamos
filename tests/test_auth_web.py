"""Comprobaciones de seguridad sin acceder a MySQL ni escribir datos reales."""
import unittest
from unittest.mock import patch
from portal_web.app_web import aplicacion


class AuthWebTests(unittest.TestCase):
    def setUp(self):
        aplicacion.config['TESTING'] = True
        self.client = aplicacion.test_client()
        self.fresh=patch('portal_web.seguridad_web.obtener_usuario_vigente')
        self.current=self.fresh.start();self.current.return_value=None
        self.addCleanup(self.fresh.stop)
        self.client.get('/acceso')
        with self.client.session_transaction() as session:
            self.token = session['token_csrf']
        self.headers = {'X-CSRF-Token': self.token}

    def login(self, user):
        self.current.return_value=user
        with patch('portal_web.app_web.iniciar_sesion_web', return_value=user):
            return self.client.post('/api/auth/login', json={
                'username': 'cliente', 'password': 'prueba-no-real', 'remember': False,
            }, headers=self.headers)

    def test_pages_are_complete_and_not_cached(self):
        for path in ['/acceso', '/registro', '/recuperar']:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'window.CRECE_AUTH', response.data)
                self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertNotIn('Regístrate aquí',self.client.get('/acceso').get_data(as_text=True))

    def test_csrf_required_before_credentials_are_checked(self):
        with patch('portal_web.app_web.iniciar_sesion_web') as authenticate:
            response = self.client.post('/api/auth/login', json={})
        self.assertEqual(response.status_code, 400)
        authenticate.assert_not_called()

    def test_invalid_credentials_cannot_create_session(self):
        self.assertEqual(self.login(None).status_code, 401)
        self.assertEqual(self.client.get('/api/auth/session').status_code, 401)

    def test_staff_cannot_enter_customer_portal(self):
        response = self.login({'id': 2, 'rol': 'ADMINISTRADOR', 'nombre_usuario': 'Admin'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['redirectUrl'], '/gestion/')
        self.assertEqual(self.client.get('/inicio').status_code, 403)

    def test_success_rotates_csrf_and_logout_invalidates_session(self):
        response = self.login({'id': 17, 'rol': 'CLIENTE', 'nombre_usuario': 'Cliente'})
        self.assertTrue(response.json['authenticated'])
        state = self.client.get('/api/auth/session').json
        self.assertTrue(state['authenticated'])
        self.assertNotEqual(state['csrfToken'], self.token)
        self.assertEqual(self.client.post('/api/auth/logout', json={}, headers=self.headers).status_code, 400)
        response = self.client.post('/api/auth/logout', json={}, headers={'X-CSRF-Token': state['csrfToken']})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/api/auth/session').status_code, 401)

    def test_unavailable_services_never_claim_success(self):
        for path in ['register', 'recover']:
            with self.subTest(path=path):
                response = self.client.post('/api/auth/' + path, json={}, headers=self.headers)
                self.assertEqual(response.status_code, 409 if path=='register' else 400)
                self.assertFalse(response.json['accepted'])

    def test_database_outage_is_explicit(self):
        from crece.servicios.clientes import ErrorConexionBaseDatos
        with patch('portal_web.app_web.iniciar_sesion_web', side_effect=ErrorConexionBaseDatos('Prueba')):
            response = self.client.post('/api/auth/login', json={'username': 'cliente', 'password': 'prueba'}, headers=self.headers)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.client.get('/api/auth/session').status_code, 401)


if __name__ == '__main__':
    unittest.main()
