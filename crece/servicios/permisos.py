"""Autorización en servicios: se consulta el estado vigente, no se confía en la vista."""
from contextvars import ContextVar
from crece.infraestructura.modelos import Usuario,Auditoria

class ErrorPermiso(ValueError):
    pass

_actor=ContextVar('crece_actor',default=None)
_version_actor=ContextVar('crece_version_actor',default=None)
def establecer_actor(usuario_id,version_sesion=None):
    return (_actor.set(int(usuario_id) if usuario_id is not None else None),_version_actor.set(version_sesion))

def restablecer_actor(token):
    _actor.reset(token[0]);_version_actor.reset(token[1])

def verificar_version_usuario(user):
    if _actor.get()==user.id and _version_actor.get() is not None and _version_actor.get()!=user.version_sesion:
        raise ErrorPermiso('La contraseña cambió. Cierra esta sesión e inicia sesión nuevamente.')

def exigir_personal(session,actor_id=None,administrador=False):
    id=actor_id if actor_id is not None else _actor.get()
    user=session.get(Usuario,int(id),with_for_update=True) if id else None
    roles=('ADMINISTRADOR',) if administrador else ('ADMINISTRADOR','EMPLEADO')
    if not user or not user.activo or user.rol not in roles:
        raise ErrorPermiso('Acceso no autorizado: la cuenta debe estar activa y tener el permiso requerido.')
    verificar_version_usuario(user)
    return user

def auditar(session,user,entity,id,action,**detail):
    session.add(Auditoria(usuario_actor_id=user.id if user else None,tipo_entidad=entity,entidad_id=id,accion=action,detalle=detail or None))
