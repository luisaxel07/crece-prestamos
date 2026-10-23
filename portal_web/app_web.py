"""Portal web de CRECE + PRÉSTAMOS con acceso por rol.

Este portal consume los mismos servicios y la misma base MySQL de la aplicación
administrativa. No expone información de otros clientes.
"""
from __future__ import annotations

import os
import secrets
import sys
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from io import BytesIO

from flask import Flask, abort, flash, g, jsonify, redirect, render_template, request, send_file, session, url_for

RAIZ_PROYECTO = Path(__file__).resolve().parents[1]
if str(RAIZ_PROYECTO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROYECTO))

from crece.servicios.comprobantes import MAX_COMPROBANTE,ErrorComprobante,obtener_comprobante_pago
from crece.servicios.cuentas_orm import iniciar_sesion_web
from portal_web.seguridad_web import registrar_seguridad,destino_usuario,verificar_csrf
from crece.servicios.clientes import ErrorConexionBaseDatos
from crece.servicios.portal_cliente import (
    listar_cuotas_cliente,
    listar_prestamos_cliente,
    listar_solicitudes_pago_cliente,
    obtener_resumen_cliente,
    solicitar_pago,
)


aplicacion = Flask(__name__)
# En producción se configura como variable del servidor. El valor temporal permite
# trabajar localmente sin publicar una clave fija en el repositorio.
aplicacion.config.update(
    SECRET_KEY=os.environ.get("SECRETO_PORTAL_WEB", secrets.token_urlsafe(48)),
    PERMANENT_SESSION_LIFETIME=timedelta(hours=4),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("PORTAL_WEB_HTTPS", "0") == "1",
    TEMPLATES_AUTO_RELOAD=True,
    SEND_FILE_MAX_AGE_DEFAULT=0,
    MAX_CONTENT_LENGTH=6*1024*1024,
    MAX_FORM_MEMORY_SIZE=256*1024,
    MAX_FORM_PARTS=20,
)
aplicacion.jinja_env.auto_reload = True
registrar_seguridad(aplicacion)


def _token_csrf() -> str:
    if "token_csrf" not in session:
        session["token_csrf"] = secrets.token_urlsafe(32)
    return session["token_csrf"]


@aplicacion.context_processor
def variables_compartidas() -> dict:
    return {"token_csrf": _token_csrf(), "usuario_portal": session.get("nombre_usuario"),
            "rol_portal": getattr(g,'usuario_actual',{}).get('rol') if getattr(g,'usuario_actual',None) else None,
            "inicio_usuario": destino_usuario(session.get('rol')),
            "auth_config": {"baseUrl": url_for("api_login").rsplit("/", 1)[0],
                            "csrfToken": _token_csrf(), "dashboard": url_for("inicio")}}


def _usuario_id() -> int:
    usuario_id = session.get("usuario_id")
    if not usuario_id or session.get("rol") != "CLIENTE":
        abort(403)
    return int(usuario_id)


def _verificar_csrf() -> None:
    verificar_csrf()


@aplicacion.after_request
def proteger_respuestas_acceso(respuesta):
    if request.endpoint!='static':
        respuesta.headers["Cache-Control"] = "no-store"
        respuesta.headers["X-Content-Type-Options"] = "nosniff"
        respuesta.headers["X-Frame-Options"] = "DENY"
        respuesta.headers['Referrer-Policy']='same-origin'
    return respuesta


@aplicacion.before_request
def limitar_cuerpo_formularios():
    limite=6*1024*1024 if request.path=='/pagos/solicitar' else 64*1024
    if request.content_length and request.content_length>limite:abort(413)

@aplicacion.errorhandler(413)
def archivo_demasiado_grande(error):
    return render_template('error.html',codigo=413,mensaje='La solicitud es demasiado grande. El comprobante debe ser una imagen de hasta 5 MB.'),413

@aplicacion.errorhandler(400)
def solicitud_invalida(error):
    if request.path.startswith("/api/auth/"):
        return jsonify(message="La solicitud no es válida o la sesión expiró. Recarga la página."), 400
    return error


@aplicacion.route("/registro")
def registro():
    return render_template("registro.html")


@aplicacion.route("/recuperar")
def recuperar():
    return render_template("recuperar.html")


@aplicacion.route("/api/auth/login", methods=["POST"])
def api_login():
    _verificar_csrf()
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return jsonify(message="Solicitud no válida."), 400
    usuario_texto, clave = datos.get("username"), datos.get("password")
    if not isinstance(usuario_texto, str) or not isinstance(clave, str) or not usuario_texto.strip() or not clave or len(usuario_texto) > 254 or len(clave) > 128:
        return jsonify(message="Ingresa un usuario o correo y una contraseña válidos."), 400
    try:
        usuario = iniciar_sesion_web(usuario_texto, clave)
    except ErrorConexionBaseDatos:
        return jsonify(message="El portal no puede conectarse en este momento. Intenta más tarde."), 503
    if not usuario or usuario["rol"] not in ('CLIENTE','EMPLEADO','ADMINISTRADOR'):
        return jsonify(message="Usuario o contraseña incorrectos, o cuenta no disponible."), 401
    session.clear()
    session.permanent = datos.get("remember") is True
    session.update(usuario_id=usuario["id"], nombre_usuario=usuario["nombre_usuario"], rol=usuario['rol'],version_sesion=usuario.get('version_sesion',1))
    _token_csrf()
    return jsonify(authenticated=True,rol=usuario['rol'],redirectUrl=destino_usuario(usuario['rol']))


@aplicacion.route("/api/auth/session")
def api_session():
    if not getattr(g,'usuario_actual',None):
        return jsonify(authenticated=False), 401
    return jsonify(authenticated=True, csrfToken=_token_csrf(),rol=g.usuario_actual['rol'],redirectUrl=destino_usuario(g.usuario_actual['rol']))


@aplicacion.route("/api/auth/logout", methods=["POST"])
def api_logout():
    _verificar_csrf()
    session.clear()
    return jsonify(authenticated=False)


@aplicacion.route('/api/auth/register',methods=['POST'])
def api_registro_controlado():
    _verificar_csrf()
    return jsonify(accepted=False,message='Las cuentas se crean desde administración después de verificar el expediente. Solicita tu acceso al personal de CRECE+ PRÉSTAMOS.'),409


@aplicacion.route('/api/auth/recover',methods=['POST'])
def api_recuperar():
    _verificar_csrf()
    datos=request.get_json(silent=True)
    if not isinstance(datos,dict):return jsonify(accepted=False,message='Solicitud no válida.'),400
    from crece.servicios.recuperacion import restablecer_contrasena
    try:
        resultado=restablecer_contrasena(datos.get('username'),datos.get('code'),datos.get('password'),datos.get('confirm'))
    except ValueError as error:return jsonify(accepted=False,message=str(error)),400
    except ErrorConexionBaseDatos:return jsonify(accepted=False,message='No se pudo completar la recuperación. Intenta nuevamente.'),503
    # No se inicia una sesión con el código: se exige autenticar de nuevo.
    session.clear()
    return jsonify(resultado)


@aplicacion.route("/marca/logo")
def logo_marca():
    return send_file(RAIZ_PROYECTO / "assets" / "logo_crece.png", mimetype="image/png")


@aplicacion.route("/marca/logo-horizontal")
def logo_horizontal():
    return send_file(RAIZ_PROYECTO / "assets" / "logo_horizontal_crece.png", mimetype="image/png")


@aplicacion.route("/marca/logo-horizontal-oscuro")
def logo_horizontal_oscuro():
    return send_file(RAIZ_PROYECTO / "portal_web" / "static" / "auth" / "assets" / "logo-oscuro.png", mimetype="image/png")


@aplicacion.route("/")
def raiz():
    return redirect(destino_usuario(session.get('rol')) if session.get("usuario_id") else url_for("acceso"))


@aplicacion.route("/acceso", methods=["GET", "POST"])
def acceso():
    if session.get("usuario_id"):
        return redirect(destino_usuario(session.get('rol')))
    if request.method == "POST":
        _verificar_csrf()
        try:
            usuario = iniciar_sesion_web(request.form.get('username',request.form.get("correo", "")), request.form.get("contrasena", ""))
        except ErrorConexionBaseDatos:
            flash("El portal no puede conectarse en este momento. Intenta nuevamente más tarde.", "error")
            return render_template("acceso.html"), 503
        if not usuario or usuario["rol"] not in ('CLIENTE','EMPLEADO','ADMINISTRADOR'):
            flash("Usuario o contraseña incorrectos, o cuenta no disponible.", "error")
        else:
            session.clear()
            session.permanent = True
            session["usuario_id"] = usuario["id"]
            session["nombre_usuario"] = usuario["nombre_usuario"]
            session["rol"] = usuario['rol']
            session['version_sesion']=usuario.get('version_sesion',1)
            _token_csrf()
            return redirect(destino_usuario(usuario['rol']))
    return render_template("acceso.html")


@aplicacion.route("/cerrar-sesion", methods=["POST"])
def cerrar_sesion():
    if not session.get('usuario_id'): abort(403)
    _verificar_csrf()
    session.clear()
    flash("Tu sesión se cerró correctamente.", "exito")
    return redirect(url_for("acceso"))


@aplicacion.route("/inicio")
def inicio():
    usuario_id = _usuario_id()
    try:
        resumen = obtener_resumen_cliente(usuario_id)
        prestamos = listar_prestamos_cliente(usuario_id)
        cuotas = listar_cuotas_cliente(usuario_id)
    except ValueError:
        session.clear()
        abort(403, 'La cuenta de cliente no está activa.')
    except ErrorConexionBaseDatos as error:
        flash(str(error), "error")
        resumen, prestamos, cuotas = {"nombre": "Cliente", "saldo": 0, "pendientes": 0}, [], []
    proximas = sorted((cuota for cuota in cuotas if cuota["estado"] != "PAGADA"), key=lambda cuota: cuota["fecha_vencimiento"])[:4]
    return render_template("inicio.html", resumen=resumen, prestamos=prestamos, proximas=proximas, avisos=[q for q in cuotas if q.get("aviso_pago")])


@aplicacion.route("/prestamos")
def prestamos():
    usuario_id = _usuario_id()
    try:
        datos = listar_prestamos_cliente(usuario_id)
    except ValueError:
        session.clear()
        abort(403, 'La cuenta de cliente no está activa.')
    except ErrorConexionBaseDatos as error:
        flash(str(error), "error")
        datos = []
    return render_template("prestamos.html", prestamos=datos)


@aplicacion.route("/cuotas")
def cuotas():
    usuario_id = _usuario_id()
    try:
        datos = listar_cuotas_cliente(usuario_id)
        solicitudes = listar_solicitudes_pago_cliente(usuario_id)
    except ValueError:
        session.clear()
        abort(403, 'La cuenta de cliente no está activa.')
    except ErrorConexionBaseDatos as error:
        flash(str(error), "error")
        datos, solicitudes = [], []
    datos = sorted(datos, key=lambda cuota: (cuota["fecha_vencimiento"], cuota["id"]))
    return render_template("cuotas.html", cuotas=datos, solicitudes=solicitudes)


@aplicacion.route("/pagos/solicitar", methods=["POST"])
def crear_solicitud_pago():
    usuario_id = _usuario_id()
    _verificar_csrf()
    try:
        cuota_id = int(request.form.get("cuota_id", ""))
        monto = Decimal(request.form.get("monto", "").replace(",", "."))
        referencia = request.form.get("referencia", "").strip()
        if len(referencia) > 100:
            raise ValueError("La referencia no puede superar 100 caracteres.")
        archivo=request.files.get('comprobante')
        if archivo is None or not archivo.filename:raise ErrorComprobante('Adjunta una foto del comprobante de pago.')
        with archivo.stream as stream:contenido=stream.read(MAX_COMPROBANTE+1)
        solicitar_pago(usuario_id, cuota_id, monto, referencia,comprobante=contenido)
        flash("Tu solicitud fue enviada. Un colaborador verificará el pago antes de confirmarlo.", "exito")
    except ErrorComprobante as error:
        flash(str(error),"error")
    except (ValueError, InvalidOperation):
        flash("Revisa el monto y los datos de tu solicitud de pago.", "error")
    except ErrorConexionBaseDatos as error:
        flash(str(error), "error")
    return redirect(url_for("cuotas"))


@aplicacion.route('/pagos/<int:pago_id>/comprobante')
def comprobante_cliente(pago_id):
    usuario_id=_usuario_id()
    try:datos=obtener_comprobante_pago(pago_id,usuario_cliente_id=usuario_id)
    except ErrorComprobante:abort(404)
    except ValueError:
        session.clear();abort(403)
    except ErrorConexionBaseDatos:abort(503,'No se pudo consultar el comprobante. Intenta nuevamente.')
    return send_file(BytesIO(datos['contenido']),mimetype=datos['tipo_mime'],download_name=datos['nombre'],as_attachment=request.args.get('descargar')=='1')


@aplicacion.template_filter("moneda")
def formato_moneda(valor) -> str:
    return f"C$ {Decimal(valor or 0):,.2f}"


@aplicacion.template_filter("fecha")
def formato_fecha(valor) -> str:
    return valor.strftime("%d/%m/%Y") if valor else "—"


@aplicacion.template_filter("porcentaje")
def formato_porcentaje(valor) -> str:
    tasa=Decimal(valor or 0)
    if tasa==tasa.quantize(Decimal('0.01')):return f'{tasa:.2f} %'
    return format(tasa,'.8f').rstrip('0').rstrip('.')+' %'


@aplicacion.errorhandler(403)
@aplicacion.errorhandler(503)
def error_de_acceso(error):
    return render_template('error.html',codigo=error.code,mensaje=error.description),error.code


from portal_web.personal import personal
aplicacion.register_blueprint(personal)


if __name__ == "__main__":
    # Solo para uso local. En producción se publica detrás de HTTPS con un servidor WSGI.
    aplicacion.run(host="127.0.0.1", port=5000, debug=os.environ.get("PORTAL_WEB_DEPURACION") == "1")
