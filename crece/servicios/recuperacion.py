"""Recuperación asistida: código aleatorio, de un uso, sin almacenar secretos en claro."""
import hashlib
import re
import secrets
from datetime import timedelta,timezone
from sqlalchemy import select,update,func
from crece.infraestructura.base_datos import transaccion
from crece.infraestructura.modelos import Usuario,RecuperacionContrasena
from crece.nucleo.seguridad import generar_hash_contrasena
from crece.servicios.permisos import exigir_personal,auditar

ERROR_CODIGO='Usuario o código incorrecto, vencido o ya utilizado. Solicita un código nuevo al administrador.'
MINUTOS_VIGENCIA=15

def invalidar_codigos(s,usuario_id):
    s.execute(update(RecuperacionContrasena).where(RecuperacionContrasena.usuario_id==usuario_id,RecuperacionContrasena.usado_en.is_(None)).values(usado_en=func.utc_timestamp()))

def emitir_codigo(usuario_id,contrasena_administrador,motivo,identidad_verificada=False):
    if identidad_verificada is not True:raise ValueError('Confirma que verificaste personalmente la identidad del titular.')
    if not isinstance(motivo,str) or not 10<=len(motivo.strip())<=250:raise ValueError('Describe la verificación realizada en entre 10 y 250 caracteres; no incluyas contraseñas ni datos del documento.')
    if not isinstance(contrasena_administrador,str) or not 1<=len(contrasena_administrador)<=128:raise ValueError('Confirma tu contraseña de administrador.')
    from crece.servicios.cuentas_orm import _habilitado_web,_password_ok
    with transaccion() as s:
        actor=exigir_personal(s,administrador=True)
        if not _password_ok(contrasena_administrador,actor.hash_contrasena):raise ValueError('La contraseña del administrador no es correcta.')
        if int(usuario_id)==actor.id:raise ValueError('Para recuperar tu propia cuenta solicita ayuda a otro administrador autorizado.')
        user=s.get(Usuario,int(usuario_id),with_for_update=True)
        if not _habilitado_web(s,user):raise ValueError('La cuenta debe existir y estar activa para recuperar el acceso.')
        invalidar_codigos(s,user.id)
        codigo=secrets.token_urlsafe(32)
        # MySQL aporta el reloj común, aunque web y escritorio usen zonas distintas.
        vence=s.scalar(select(func.utc_timestamp()))+timedelta(minutes=MINUTOS_VIGENCIA)
        s.add(RecuperacionContrasena(usuario_id=user.id,codigo_hash=hashlib.sha256(codigo.encode()).hexdigest(),vence_en=vence))
        auditar(s,actor,'usuario',user.id,'EMITIR_RECUPERACION',motivo=motivo.strip(),vence_en_utc=vence.isoformat())
        local=vence.replace(tzinfo=timezone.utc).astimezone().replace(tzinfo=None)
        return dict(usuario=user.nombre_usuario,codigo=codigo,vence_en=local)

def restablecer_contrasena(usuario,codigo,contrasena,confirmacion):
    if not isinstance(usuario,str) or not 1<=len(usuario.strip())<=60 or not isinstance(codigo,str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}',codigo):raise ValueError(ERROR_CODIGO)
    if not isinstance(contrasena,str) or not 10<=len(contrasena)<=128:raise ValueError('La nueva contraseña debe tener entre 10 y 128 caracteres.')
    if contrasena!=confirmacion:raise ValueError('Las contraseñas no coinciden.')
    # El hash costoso se prepara antes de tomar bloqueos; no se registra en auditoría.
    nuevo_hash=generar_hash_contrasena(contrasena)
    from crece.servicios.cuentas_orm import _habilitado_web,_password_ok
    with transaccion() as s:
        user=s.scalar(select(Usuario).where(Usuario.nombre_usuario==usuario.strip()).with_for_update())
        if not _habilitado_web(s,user):raise ValueError(ERROR_CODIGO)
        registro=s.scalar(select(RecuperacionContrasena).where(RecuperacionContrasena.usuario_id==user.id,RecuperacionContrasena.codigo_hash==hashlib.sha256(codigo.encode()).hexdigest(),RecuperacionContrasena.usado_en.is_(None),RecuperacionContrasena.vence_en>func.utc_timestamp()).with_for_update())
        if registro is None:raise ValueError(ERROR_CODIGO)
        if _password_ok(contrasena,user.hash_contrasena):raise ValueError('Elige una contraseña diferente a la anterior.')
        user.hash_contrasena=nuevo_hash
        user.version_sesion+=1
        user.requiere_cambio_contrasena=False
        invalidar_codigos(s,user.id)
        auditar(s,user,'usuario',user.id,'COMPLETAR_RECUPERACION')
    return dict(accepted=True,message='Contraseña actualizada. Tus sesiones anteriores se cerraron. Vuelve a iniciar sesión con tu nueva contraseña.')
