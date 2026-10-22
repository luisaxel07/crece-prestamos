"""Consultas ORM siempre limitadas al cliente autenticado y activo."""
from decimal import Decimal
from sqlalchemy import select
from crece.infraestructura.base_datos import transaccion
from crece.infraestructura.modelos import Usuario,Cliente,Prestamo,CuotaModel,Pago
from crece.infraestructura.repositorios import Repositorio,PrestamosRepositorio
from crece.servicios.comprobantes import preparar_comprobante,guardar_comprobante
from crece.servicios.gestion import cuota_dict,prestamo_dict,estado_prestamo,dinero

def _cliente(s,usuario_id):
    c=s.scalar(select(Cliente).join(Usuario,Usuario.id==Cliente.usuario_id).where(Cliente.usuario_id==int(usuario_id),Cliente.estado=='ACTIVO',Usuario.activo.is_(True),Usuario.rol=='CLIENTE'))
    if not c: raise ValueError('La cuenta no está activa o no está vinculada a un cliente.')
    from crece.servicios.permisos import verificar_version_usuario
    verificar_version_usuario(c.usuario)
    return c

def obtener_resumen_cliente(usuario_id):
    with transaccion() as s:
        c=_cliente(s,usuario_id)
        rows=[q for p in PrestamosRepositorio(s).cartera(c.id) if estado_prestamo(p) in ('ACTIVO','MORA') for q in p.cuotas if q.saldo>0]
        return dict(nombre=c.nombre,saldo=sum((q.saldo for q in rows),Decimal('0')),pendientes=len(rows))

def listar_cuotas_cliente(usuario_id):
    with transaccion() as s:
        c=_cliente(s,usuario_id)
        return sorted([cuota_dict(q,p) for p in PrestamosRepositorio(s).cartera(c.id) if p.estado!='CANCELADO' for q in p.cuotas],key=lambda row:row['fecha_vencimiento'])

def listar_prestamos_cliente(usuario_id):
    with transaccion() as s:
        c=_cliente(s,usuario_id)
        return [dict(**prestamo_dict(p),cuotas_pendientes=sum(q.saldo>0 for q in p.cuotas)) for p in PrestamosRepositorio(s).cartera(c.id)]

def listar_solicitudes_pago_cliente(usuario_id):
    with transaccion() as s:
        c=_cliente(s,usuario_id)
        rows=s.scalars(select(Pago).join(CuotaModel).join(Prestamo).where(Prestamo.cliente_id==c.id,Pago.metodo=='PAGO_CLIENTE').order_by(Pago.id.desc()))
        return [dict(id=p.id,monto=p.monto,metodo=p.metodo,referencia=p.referencia,estado=p.estado,fecha_pago=p.fecha_pago,numero_cuota=p.cuota.numero_cuota,prestamo_id=p.cuota.prestamo_id,tiene_comprobante=p.comprobante is not None) for p in rows]

def solicitar_pago(usuario_id,cuota_id,monto,referencia,comprobante=None):
    amount=dinero(monto)
    imagen=preparar_comprobante(comprobante)
    if not referencia.strip() or len(referencia)>100: raise ValueError('Indica una referencia de hasta 100 caracteres.')
    with transaccion() as s:
        c=_cliente(s,usuario_id)
        q=s.scalar(select(CuotaModel).join(Prestamo).where(CuotaModel.id==int(cuota_id),Prestamo.cliente_id==c.id,Prestamo.estado.in_(('ACTIVO','MORA'))).with_for_update())
        if not q or not 0<amount<=q.saldo: raise ValueError('No puedes solicitar ese monto para esta cuota.')
        if s.scalar(select(Pago.id).where(Pago.cuota_id==q.id,Pago.estado=='PENDIENTE_VERIFICACION').limit(1)):
            raise ValueError('Esta cuota ya tiene un aviso pendiente de revisión.')
        pago=Repositorio(s,Pago).agregar(cuota_id=q.id,monto=amount,metodo='PAGO_CLIENTE',referencia=referencia.strip(),estado='PENDIENTE_VERIFICACION')
        guardar_comprobante(s,pago.id,imagen)
        return pago.id
