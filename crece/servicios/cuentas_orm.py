"""Acceso y cuentas de usuario mediante entidades ORM."""
from datetime import datetime
from sqlalchemy import select,func,or_
from crece.infraestructura.base_datos import transaccion
from crece.infraestructura.modelos import Usuario,Empleado,Cliente,Prestamo,Pago,Auditoria,RecuperacionContrasena
from crece.infraestructura.repositorios import Repositorio
from crece.servicios.permisos import exigir_personal,auditar
from crece.nucleo.seguridad import generar_hash_contrasena,verificar_contrasena

def usuario_dict(user):
    return dict(id=user.id,nombre_usuario=user.nombre_usuario,rol=user.rol,activo=user.activo,version_sesion=user.version_sesion,requiere_cambio_contrasena=user.requiere_cambio_contrasena,ultimo_acceso_en=user.ultimo_acceso_en,creado_en=user.creado_en)

def _password_ok(password,stored):
    try: return verificar_contrasena(password,stored)
    except (ValueError,TypeError): return False

def hay_administrador_configurado():
    with transaccion() as s:
        return bool(s.scalar(select(func.count()).select_from(Usuario).where(Usuario.rol=='ADMINISTRADOR',~Usuario.hash_contrasena.like('CONFIGURAR_%'))))

def configurar_administrador(nombre_usuario,contrasena):
    name=nombre_usuario.strip()
    if not 4<=len(name)<=60: raise ValueError('El usuario debe tener entre 4 y 60 caracteres.')
    password_hash=generar_hash_contrasena(contrasena)
    with transaccion() as s:
        if s.scalar(select(Usuario.id).where(Usuario.rol=='ADMINISTRADOR',~Usuario.hash_contrasena.like('CONFIGURAR_%')).with_for_update().limit(1)):
            raise ValueError('Ya existe un administrador. Ingresa con una cuenta autorizada.')
        Repositorio(s,Usuario).agregar(nombre_usuario=name,hash_contrasena=password_hash,rol='ADMINISTRADOR')

def iniciar_sesion(nombre_usuario,contrasena):
    with transaccion() as s:
        user=s.scalar(select(Usuario).where(Usuario.nombre_usuario==nombre_usuario.strip()))
        if not user or not user.activo or not _password_ok(contrasena,user.hash_contrasena): return None
        user.ultimo_acceso_en=datetime.now()
        return usuario_dict(user)

def iniciar_sesion_cliente_por_correo(correo,contrasena):
    name=correo.strip().lower()
    with transaccion() as s:
        condition=func.lower(Cliente.correo)==name if '@' in name else func.lower(Usuario.nombre_usuario)==name
        user=s.scalar(select(Usuario).join(Cliente,Cliente.usuario_id==Usuario.id).where(condition,Cliente.estado=='ACTIVO',Usuario.rol=='CLIENTE',Usuario.activo.is_(True)))
        if not user or not _password_ok(contrasena,user.hash_contrasena): return None
        user.ultimo_acceso_en=datetime.now()
        return usuario_dict(user)


def _habilitado_web(s,user):
    if not user or not user.activo or user.rol not in ('ADMINISTRADOR','EMPLEADO','CLIENTE') or user.nombre_usuario=='sistema_inicial':
        return False
    if user.rol=='CLIENTE':
        return bool(s.scalar(select(Cliente.id).where(Cliente.usuario_id==user.id,Cliente.estado=='ACTIVO')))
    return True


def iniciar_sesion_web(identificador,contrasena):
    """Una entrada para los tres roles; el nombre exacto de usuario tiene prioridad."""
    name=identificador.strip().lower()
    with transaccion() as s:
        user=s.scalar(select(Usuario).where(func.lower(Usuario.nombre_usuario)==name))
        if user is None and '@' in name:
            ids=set(s.scalars(select(Cliente.usuario_id).where(func.lower(Cliente.correo)==name,Cliente.usuario_id.is_not(None))))
            ids.update(s.scalars(select(Empleado.usuario_id).where(func.lower(Empleado.correo)==name)))
            # Si dos expedientes usan el mismo correo, se debe utilizar el usuario único.
            if len(ids)==1: user=s.get(Usuario,ids.pop())
        if not _habilitado_web(s,user) or not _password_ok(contrasena,user.hash_contrasena): return None
        user.ultimo_acceso_en=datetime.now()
        return usuario_dict(user)


def obtener_usuario_vigente(usuario_id):
    """Revalida estado, rol y vínculo del cliente en cada solicitud privada."""
    with transaccion() as s:
        user=s.get(Usuario,int(usuario_id))
        return usuario_dict(user) if _habilitado_web(s,user) else None

def crear_cuenta_cliente(cliente_id,correo,contrasena):
    from crece.nucleo.validaciones import normalizar_correo
    name=normalizar_correo(correo,requerido=True)
    password_hash=generar_hash_contrasena(contrasena)
    with transaccion() as s:
        actor=exigir_personal(s)
        c=s.get(Cliente,int(cliente_id),with_for_update=True)
        if not c or c.usuario_id is not None: raise ValueError('El cliente no existe o ya tiene una cuenta.')
        user=Repositorio(s,Usuario).agregar(nombre_usuario=name,hash_contrasena=password_hash,rol='CLIENTE')
        c.usuario_id=user.id
        c.correo=name
        auditar(s,actor,'cliente',c.id,'CREAR_ACCESO')

def actualizar_correo_cliente_portal(cliente_id,correo):
    from crece.nucleo.validaciones import normalizar_correo
    name=normalizar_correo(correo,requerido=True)
    with transaccion() as s:
        actor=exigir_personal(s)
        c=s.get(Cliente,int(cliente_id),with_for_update=True)
        if not c or not c.usuario_id: raise ValueError('No existe una cuenta vinculada.')
        c.correo=name
        auditar(s,actor,'cliente',c.id,'CAMBIAR_CORREO')

def listar_usuarios():
    with transaccion() as s:
        exigir_personal(s,administrador=True)
        return [usuario_dict(u) for u in Repositorio(s,Usuario).listar(Usuario.nombre_usuario!='sistema_inicial')]

def crear_usuario_personal(nombre_usuario,contrasena,rol):
    if rol not in ('ADMINISTRADOR','EMPLEADO') or not 4<=len(nombre_usuario.strip())<=60: raise ValueError('Nombre o rol inválido.')
    password_hash=generar_hash_contrasena(contrasena)
    with transaccion() as s:
        actor=exigir_personal(s,administrador=True)
        user=Repositorio(s,Usuario).agregar(nombre_usuario=nombre_usuario.strip(),hash_contrasena=password_hash,rol=rol)
        auditar(s,actor,'usuario',user.id,'CREAR')
        return user.id

def cambiar_estado_usuario(usuario_id,activo):
    with transaccion() as s:
        actor=exigir_personal(s,administrador=True)
        target=s.get(Usuario,int(usuario_id),with_for_update=True)
        if not target: raise ValueError('Usuario no encontrado.')
        if not activo and target.id==actor.id: raise ValueError('No puedes desactivar tu propia sesión administrativa.')
        if not activo and target.rol=='ADMINISTRADOR' and s.scalar(select(func.count()).select_from(Usuario).where(Usuario.rol=='ADMINISTRADOR',Usuario.activo.is_(True)))<=1:
            raise ValueError('Debe quedar al menos un administrador activo.')
        target.activo=bool(activo)
        auditar(s,actor,'usuario',target.id,'ACTIVAR' if activo else 'DESACTIVAR')

def actualizar_usuario(usuario_id,nombre_usuario,contrasena=''):
    if not 4<=len(nombre_usuario.strip())<=60: raise ValueError('Nombre de usuario inválido.')
    password_hash=generar_hash_contrasena(contrasena) if contrasena else None
    with transaccion() as s:
        actor=exigir_personal(s,administrador=True)
        target=s.get(Usuario,int(usuario_id),with_for_update=True)
        if not target: raise ValueError('Usuario no encontrado.')
        target.nombre_usuario=nombre_usuario.strip()
        if password_hash:
            from crece.servicios.recuperacion import invalidar_codigos
            target.hash_contrasena=password_hash
            target.version_sesion+=1
            invalidar_codigos(s,target.id)
        auditar(s,actor,'usuario',target.id,'ACTUALIZAR')

def eliminar_usuario(usuario_id):
    with transaccion() as s:
        actor=exigir_personal(s,administrador=True)
        user=s.get(Usuario,int(usuario_id),with_for_update=True)
        if not user: raise ValueError('Usuario no encontrado.')
        if user.id==actor.id or user.rol=='ADMINISTRADOR': raise ValueError('Los administradores se desactivan conservando al menos uno activo.')
        used=s.scalar(select(RecuperacionContrasena.id).where(RecuperacionContrasena.usuario_id==user.id).limit(1)) or user.empleado or s.scalar(select(Cliente.id).where(Cliente.usuario_id==user.id).limit(1)) or s.scalar(select(Prestamo.id).where(Prestamo.creado_por==user.id).limit(1)) or s.scalar(select(Pago.id).where(Pago.registrado_por==user.id).limit(1)) or s.scalar(select(Auditoria.id).where(Auditoria.usuario_actor_id==user.id).limit(1))
        if used:
            user.activo=False
            result='DESACTIVADO'
        else:
            s.delete(user)
            result='ELIMINADO'
        auditar(s,actor,'usuario',int(usuario_id),result)
        return result

def obtener_cliente_para_cuenta(cliente_id):
    from crece.servicios.gestion import obtener_cliente
    return obtener_cliente(cliente_id)
