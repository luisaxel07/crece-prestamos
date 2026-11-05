"""Recuperación asistida e invalidación de sesiones contra MySQL/InnoDB aislado."""
import unittest
from datetime import datetime,timedelta
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select,func
from mysql_support import preparar_mysql
from crece.infraestructura.base_datos import transaccion
from crece.infraestructura.modelos import Usuario,RecuperacionContrasena,Auditoria
from crece.nucleo.seguridad import generar_hash_contrasena
from crece.servicios.permisos import establecer_actor,exigir_personal
from crece.servicios.recuperacion import emitir_codigo,restablecer_contrasena,ERROR_CODIGO
from crece.servicios.cuentas_orm import iniciar_sesion_web,actualizar_usuario,cambiar_estado_usuario
from portal_web.app_web import aplicacion

ANTERIOR='PruebaAnterior-2026'
NUEVA='PruebaRenovada-2026'

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.engine=preparar_mysql()
        with transaccion() as s:
            clave=generar_hash_contrasena(ANTERIOR)
            admin=Usuario(nombre_usuario='admin_recuperacion',hash_contrasena=clave,rol='ADMINISTRADOR')
            empleado=Usuario(nombre_usuario='asesor_recuperacion',hash_contrasena=clave,rol='EMPLEADO')
            s.add_all([admin,empleado]);s.flush();self.admin=admin.id;self.empleado=empleado.id
        establecer_actor(self.admin,1)
        aplicacion.config['TESTING']=True

    def tearDown(self):establecer_actor(None)
    def emitir(self):return emitir_codigo(self.empleado,ANTERIOR,'Identidad verificada presencialmente con expediente',True)
    def cambiar(self,codigo,usuario='asesor_recuperacion',password=NUEVA,confirm=NUEVA):return restablecer_contrasena(usuario,codigo,password,confirm)
    def browser(self,id,rol):
        b=aplicacion.test_client()
        with b.session_transaction() as sess:sess.update(usuario_id=id,rol=rol,nombre_usuario='prueba',token_csrf='csrf-prueba',version_sesion=1)
        return b

    def test_code_is_hashed_audited_expires_and_does_not_replace_password_on_issue(self):
        r=self.emitir();self.assertEqual(len(r['codigo']),43)
        self.assertTrue(datetime.now()+timedelta(minutes=14)<r['vence_en']<datetime.now()+timedelta(minutes=16))
        self.assertIsNotNone(iniciar_sesion_web('asesor_recuperacion',ANTERIOR))
        with transaccion() as s:
            fila=s.scalar(select(RecuperacionContrasena));self.assertNotEqual(fila.codigo_hash,r['codigo']);self.assertEqual(len(fila.codigo_hash),64)
            reloj=s.scalar(select(func.utc_timestamp()))
            self.assertTrue(timedelta(minutes=14)<fila.vence_en-reloj<=timedelta(minutes=15))
            auditoria=str(s.scalar(select(Auditoria.detalle)));self.assertNotIn(r['codigo'],auditoria);self.assertNotIn(ANTERIOR,auditoria)

    def test_requires_administrator_reauthentication_and_verified_identity(self):
        for clave,identidad,motivo in [('incorrecta',True,'Verificación presencial'),(ANTERIOR,False,'Verificación presencial'),(ANTERIOR,True,'corto')]:
            with self.assertRaises(ValueError):emitir_codigo(self.empleado,clave,motivo,identidad)
        establecer_actor(self.empleado,1)
        with self.assertRaises(ValueError):self.emitir()
        establecer_actor(self.admin,1)
        with self.assertRaises(ValueError):emitir_codigo(self.admin,ANTERIOR,'Verificación presencial',True)
        with transaccion() as s:self.assertIsNone(s.scalar(select(RecuperacionContrasena.id)))

    def test_success_changes_password_consumes_code_and_requires_new_login(self):
        r=self.emitir();self.assertTrue(self.cambiar(r['codigo'])['accepted'])
        self.assertIsNone(iniciar_sesion_web('asesor_recuperacion',ANTERIOR))
        self.assertEqual(iniciar_sesion_web('asesor_recuperacion',NUEVA)['version_sesion'],2)
        with self.assertRaisesRegex(ValueError,ERROR_CODIGO):self.cambiar(r['codigo'])

    def test_reissue_expiry_wrong_user_and_invalid_codes(self):
        anterior=self.emitir();vigente=self.emitir()
        for usuario,codigo in [('asesor_recuperacion',anterior['codigo']),('no_existe',vigente['codigo']),('admin_recuperacion',vigente['codigo']),('asesor_recuperacion','x'*43)]:
            with self.assertRaisesRegex(ValueError,ERROR_CODIGO):self.cambiar(codigo,usuario)
        with transaccion() as s:
            for r in s.scalars(select(RecuperacionContrasena)):r.vence_en=datetime.now()-timedelta(seconds=1)
        with self.assertRaisesRegex(ValueError,ERROR_CODIGO):self.cambiar(vigente['codigo'])

    def test_inactive_accounts_cannot_issue_or_consume_code(self):
        r=self.emitir();cambiar_estado_usuario(self.empleado,False)
        with self.assertRaises(ValueError):self.emitir()
        with self.assertRaisesRegex(ValueError,ERROR_CODIGO):self.cambiar(r['codigo'])

    def test_password_validation_does_not_consume_valid_code(self):
        r=self.emitir()
        for password,confirm in [('corta','corta'),('x'*129,'x'*129),(NUEVA,'otra'),(ANTERIOR,ANTERIOR)]:
            with self.assertRaises(ValueError):self.cambiar(r['codigo'],password=password,confirm=confirm)
        self.assertTrue(self.cambiar(r['codigo'])['accepted'])

    def test_concurrent_consumption_only_succeeds_once_with_innodb(self):
        r=self.emitir()
        def intentar(_):
            try:self.cambiar(r['codigo']);return True
            except ValueError:return False
        with ThreadPoolExecutor(max_workers=2) as pool:resultado=list(pool.map(intentar,range(2)))
        self.assertEqual(sorted(resultado),[False,True])

    def test_recovery_revokes_web_and_desktop_sessions(self):
        b=self.browser(self.empleado,'EMPLEADO');self.assertEqual(b.get('/api/auth/session').status_code,200)
        r=self.emitir();self.cambiar(r['codigo'])
        self.assertEqual(b.get('/api/auth/session').status_code,401)
        establecer_actor(self.empleado,1)
        with transaccion() as s,self.assertRaises(ValueError):exigir_personal(s)
        establecer_actor(self.empleado,2)
        with transaccion() as s:self.assertEqual(exigir_personal(s).id,self.empleado)

    def test_direct_password_change_invalidates_pending_recovery(self):
        r=self.emitir();actualizar_usuario(self.empleado,'asesor_recuperacion',NUEVA)
        with self.assertRaisesRegex(ValueError,ERROR_CODIGO):self.cambiar(r['codigo'])

    def test_web_admin_issues_once_no_token_in_cookie_or_url_and_employee_is_denied(self):
        b=self.browser(self.admin,'ADMINISTRADOR');path=f'/gestion/usuarios/{self.empleado}/recuperar'
        self.assertEqual(b.get(path).status_code,200)
        self.assertEqual(b.post(path,data={}).status_code,400)
        r=b.post(path,data=dict(token_csrf='csrf-prueba',clave_admin=ANTERIOR,motivo='Identidad contrastada presencialmente',identidad='SI'))
        self.assertEqual(r.status_code,200);self.assertIn('Código de recuperación',r.get_data(as_text=True));self.assertEqual(r.headers['Cache-Control'],'no-store')
        import re
        codigo=re.search(r'id="codigo-temporal" readonly value="([^"]+)"',r.get_data(as_text=True)).group(1)
        with b.session_transaction() as sess:self.assertNotIn(codigo,str(dict(sess)))
        self.assertNotIn(codigo,r.headers.get('Location',''))
        self.assertNotIn('codigo-temporal',b.get(path).get_data(as_text=True))
        self.assertEqual(self.browser(self.empleado,'EMPLEADO').get(path).status_code,403)

    def test_public_endpoint_never_auto_logs_in_and_requires_csrf(self):
        r=self.emitir();b=aplicacion.test_client();b.get('/recuperar')
        datos=dict(username=r['usuario'],code=r['codigo'],password=NUEVA,confirm=NUEVA)
        self.assertEqual(b.post('/api/auth/recover',json=datos).status_code,400)
        with b.session_transaction() as sess:csrf=sess['token_csrf']
        response=b.post('/api/auth/recover',json=datos,headers={'X-CSRF-Token':csrf})
        self.assertEqual(response.status_code,200);self.assertTrue(response.json['accepted'])
        self.assertEqual(b.get('/api/auth/session').status_code,401)

    def test_public_registration_explains_controlled_access_without_fake_form(self):
        b=aplicacion.test_client();html=b.get('/registro').get_data(as_text=True)
        self.assertIn('Las cuentas se crean desde administración',html);self.assertNotIn('<form',html)
        html=b.get('/recuperar').get_data(as_text=True)
        for name in ('username','code','password','confirm'):self.assertIn(f'name="{name}"',html)

if __name__=='__main__':unittest.main()
