"""Sesiones, CSRF y permisos de solicitud. El actor ORM nunca se comparte entre usuarios."""
from functools import wraps
import secrets
from flask import abort,g,jsonify,request,session,url_for
from crece.servicios.cuentas_orm import obtener_usuario_vigente
from crece.infraestructura.base_datos import ErrorConexionBaseDatos
from crece.servicios.permisos import establecer_actor,restablecer_actor

ROLES_PERSONAL=('ADMINISTRADOR','EMPLEADO')

def destino_usuario(rol):
    return url_for('personal.inicio') if rol in ROLES_PERSONAL else url_for('inicio')

def verificar_csrf():
    received=request.headers.get('X-CSRF-Token','') if request.is_json else request.form.get('token_csrf','')
    expected=session.get('token_csrf','')
    if not expected or not secrets.compare_digest(received.encode(),expected.encode()):
        abort(400,'La sesión expiró. Recarga la página e inténtalo otra vez.')

def requiere_personal(administrador=False):
    def decorator(view):
        @wraps(view)
        def protected(*args,**kwargs):
            user=getattr(g,'usuario_actual',None)
            allowed=('ADMINISTRADOR',) if administrador else ROLES_PERSONAL
            if not user or user['rol'] not in allowed: abort(403)
            if request.method=='POST': verificar_csrf()
            return view(*args,**kwargs)
        return protected
    return decorator

def registrar_seguridad(app):
    @app.before_request
    def validar_sesion():
        g.actor_token=establecer_actor(None)
        g.usuario_actual=None
        public={'static','api_login','api_logout','api_registro_controlado','api_recuperar','logo_marca','logo_horizontal','logo_horizontal_oscuro','registro','recuperar'}
        if request.endpoint in public or not session.get('usuario_id'): return
        try: user=obtener_usuario_vigente(session['usuario_id'])
        except ErrorConexionBaseDatos:
            if request.path.startswith('/api/'):
                return jsonify(authenticated=False,message='No se pudo verificar la sesión. Intenta nuevamente.'),503
            abort(503,'No se pudo verificar la sesión. Intenta nuevamente.')
        except (ValueError,TypeError): user=None
        if not user or session.get('version_sesion')!=user.get('version_sesion',1):
            session.clear()
            if request.path.startswith('/api/'):
                return jsonify(authenticated=False,message='Tu sesión ya no es válida. Inicia sesión nuevamente.'),401
            abort(403,'Tu sesión ya no es válida. Vuelve a iniciar sesión con una cuenta activa.')
        g.usuario_actual=user
        session.update(rol=user['rol'],nombre_usuario=user['nombre_usuario'])
        establecer_actor(user['id'],user.get('version_sesion',1))

    @app.teardown_request
    def liberar_actor(_error):
        token=g.pop('actor_token',None)
        if token is not None: restablecer_actor(token)
