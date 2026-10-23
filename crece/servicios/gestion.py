"""Casos de uso CRUD del personal y cartera con transacciones ORM."""
from datetime import date,datetime
from decimal import Decimal,InvalidOperation
from sqlalchemy import select,func
from sqlalchemy.orm import joinedload
from crece.infraestructura.base_datos import transaccion,ErrorConexionBaseDatos
from crece.infraestructura.modelos import Usuario,Empleado,Cliente,Prestamo,CuotaModel,Pago,Auditoria
from crece.infraestructura.repositorios import Repositorio,PrestamosRepositorio
from crece.servicios.permisos import exigir_personal,auditar
from crece.nucleo.seguridad import generar_hash_contrasena,verificar_contrasena
from crece.nucleo.validaciones import normalizar_persona, normalizar_nombre
from crece.nucleo.amortizacion import calcular_tabla_francesa,redondear_moneda
from crece.nucleo.amortizacion import calcular_tabla_credito,normalizar_frecuencia,FRECUENCIAS
from crece.nucleo.mora import detalle_mora,ahora_local

def dinero(value):
    try:
        number=Decimal(str(value))
        if not number.is_finite(): raise ValueError('El importe debe ser finito.')
        return redondear_moneda(number)
    except InvalidOperation as error: raise ValueError('Ingresa un importe válido.') from error

def cuota_estado(q):
    if q.saldo<=0: return 'PAGADA'
    if q.fecha_vencimiento<ahora_local().date(): return 'VENCIDA'
    return 'PARCIAL' if q.monto_pagado else 'PENDIENTE'

def estado_prestamo(p):
    if p.estado in ('CANCELADO','BORRADOR'): return p.estado
    if p.cuotas and all(q.saldo<=0 for q in p.cuotas): return 'FINALIZADO'
    return 'MORA' if any(cuota_estado(q)=='VENCIDA' for q in p.cuotas) else 'ACTIVO'

def cliente_dict(c):
    return dict(id=c.id,cedula=c.cedula,nombres=c.nombres,apellidos=c.apellidos,nombre_completo=c.nombre,nombre=c.nombre,telefono=c.telefono,correo=c.correo,direccion=c.direccion,estado=c.estado,usuario_id=c.usuario_id)

def cuota_dict(q,p=None):
    p=p or q.prestamo
    mora=detalle_mora(q)
    return dict(id=q.id,cuota_id=q.id,prestamo_id=p.id,cliente=p.cliente.nombre,cliente_id=p.cliente_id,numero_cuota=q.numero_cuota,fecha_vencimiento=q.fecha_vencimiento,saldo_inicial=q.saldo_inicial,cuota_programada=q.cuota_programada,abono_capital=q.abono_capital,interes=q.interes,tasa_mensual=p.tasa_mensual,tasa_periodica=p.tasa_periodica,frecuencia=p.frecuencia,monto_pagado=q.monto_pagado,saldo=mora['saldo_total'],saldo_cuota=mora['saldo_total'],saldo_final=q.saldo_inicial-q.abono_capital,estado=cuota_estado(q),**mora)

def prestamo_dict(p):
    return dict(id=p.id,cliente=p.cliente.nombre,cliente_id=p.cliente_id,cedula=p.cliente.cedula,monto_principal=p.monto_principal,cuota_mensual=p.cuota_mensual,cuota_periodica=p.cuota_mensual,tasa_interes_anual=p.tasa_interes_anual,tasa_mensual=p.tasa_mensual,tasa_periodica=p.tasa_periodica,frecuencia=p.frecuencia,frecuencia_texto=FRECUENCIAS[p.frecuencia],numero_cuotas=p.numero_cuotas,recargo_porcentaje=p.recargo_porcentaje,gracia_horas=p.gracia_horas,plazo_meses=p.plazo_meses,fecha_desembolso=p.fecha_desembolso,fecha_primera_cuota=p.fecha_primera_cuota,estado=estado_prestamo(p),notas=p.notas,creado_por=p.creado_por,empleado=p.creador.nombre_usuario,saldo_pendiente=sum((q.saldo for q in p.cuotas),Decimal('0')),cuotas_vencidas=sum(cuota_estado(q)=='VENCIDA' for q in p.cuotas))

def validar_persona(cedula,nombres,apellidos,telefono,correo='',**_):
    return normalizar_persona(cedula,nombres,apellidos,telefono,correo)


def listar_clientes():
    with transaccion() as s:
        exigir_personal(s)
        return [cliente_dict(c) for c in Repositorio(s,Cliente).listar()]

def obtener_cliente(cliente_id):
    with transaccion() as s:
        exigir_personal(s)
        c=s.get(Cliente,int(cliente_id))
        if not c: raise ValueError('Cliente no encontrado.')
        return cliente_dict(c)

def registrar_cliente(cedula,nombres,apellidos,telefono,correo='',direccion=''):
    data=validar_persona(cedula,nombres,apellidos,telefono,correo)
    if len(direccion)>255: raise ValueError('Dirección demasiado larga.')
    with transaccion() as s:
        user=exigir_personal(s)
        c=Repositorio(s,Cliente).agregar(**{**data,'correo':data['correo'] or None},direccion=direccion.strip() or None)
        auditar(s,user,'cliente',c.id,'CREAR')
        return c.id

def actualizar_cliente(cliente_id,cedula,nombres,apellidos,telefono,correo='',direccion='',estado='ACTIVO'):
    data=validar_persona(cedula,nombres,apellidos,telefono,correo)
    if estado not in ('ACTIVO','INACTIVO','BLOQUEADO') or len(direccion)>255: raise ValueError('Estado o dirección inválidos.')
    with transaccion() as s:
        user=exigir_personal(s)
        c=Repositorio(s,Cliente).obtener(cliente_id,True)
        if not c: raise ValueError('Cliente no encontrado.')
        for key,value in data.items(): setattr(c,key,value or None)
        c.direccion=direccion.strip() or None
        c.estado=estado
        auditar(s,user,'cliente',c.id,'ACTUALIZAR')

def eliminar_cliente(cliente_id):
    with transaccion() as s:
        user=exigir_personal(s,administrador=True)
        c=Repositorio(s,Cliente).obtener(cliente_id,True)
        if not c: raise ValueError('Cliente no encontrado.')
        if c.prestamos:
            c.estado='INACTIVO'
            result='INACTIVADO'
        else:
            if c.usuario: c.usuario.activo=False
            s.delete(c)
            result='ELIMINADO'
        auditar(s,user,'cliente',int(cliente_id),result)
        return result

def listar_clientes_para_prestamo(): return [c for c in listar_clientes() if c['estado']=='ACTIVO']

def _exigir_cliente_sin_prestamo_pendiente(s,cliente_id):
    # La fila del cliente ya está bloqueada por la emisión. La consulta actual
    # también se bloquea para que dos operadores no emitan créditos simultáneos.
    prestamos=s.scalars(select(Prestamo).where(
        Prestamo.cliente_id==cliente_id,
        Prestamo.estado.not_in(('CANCELADO','BORRADOR')),
    ).order_by(Prestamo.id).with_for_update()).all()
    for p in prestamos:
        if not p.cuotas or any(q.saldo>0 for q in p.cuotas):
            raise ValueError(f'No se puede emitir otro préstamo: el cliente ya tiene asignado el préstamo PR-{p.id:05d} sin saldar. Podrá solicitar uno nuevo cuando haya saldado completamente el préstamo actual.')

def listar_prestamos():
    with transaccion() as s:
        exigir_personal(s)
        return [prestamo_dict(p) for p in PrestamosRepositorio(s).cartera()]

def registrar_prestamo(cliente_id,monto_principal,tasa_anual,plazo_meses,fecha_desembolso,fecha_primera_cuota,actor_id=None,*,frecuencia='MENSUAL',con_recargo=True):
    """Contrato anual conservado para compatibilidad; la nueva UI convierte la tasa mensual."""
    principal=dinero(monto_principal)
    annual=Decimal(str(tasa_anual))
    if not annual.is_finite() or not 0<=annual<=Decimal('999.9999') or annual.as_tuple().exponent < -4:
        raise ValueError('La tasa debe poder almacenarse con hasta cuatro decimales nominales anuales.')
    frecuencia=normalizar_frecuencia(frecuencia)
    if not isinstance(plazo_meses,int) or isinstance(plazo_meses,bool) or not 1<=plazo_meses<=600 or principal<=0 or principal>Decimal('999999999999.99'):
        raise ValueError('Monto o número de cuotas fuera de rango (1 a 600 cuotas).')
    if fecha_primera_cuota<=fecha_desembolso: raise ValueError('La primera cuota debe ser posterior al desembolso.')
    tabla=calcular_tabla_credito(principal,annual/Decimal('12'),plazo_meses,fecha_primera_cuota,frecuencia)
    if any(q.abono_capital<0 or q.pago<=0 for q in tabla): raise ValueError('El monto y plazo no permiten cuotas positivas en centavos.')
    if any(q.pago+(redondear_moneda(q.abono_capital/100) if con_recargo else 0)>Decimal('999999999999.99') for q in tabla):
        raise ValueError('El monto y la tasa producen cuotas fuera del rango permitido. Reduce el capital o la tasa.')
    with transaccion() as s:
        user=exigir_personal(s,actor_id)
        c=s.get(Cliente,int(cliente_id),with_for_update=True)
        if not c or c.estado!='ACTIVO': raise ValueError('El cliente debe estar activo para emitir un préstamo.')
        _exigir_cliente_sin_prestamo_pendiente(s,c.id)
        p=Repositorio(s,Prestamo).agregar(cliente_id=c.id,creado_por=user.id,monto_principal=principal,tasa_interes_anual=annual,plazo_meses=plazo_meses,cuota_mensual=tabla[0].pago,frecuencia=frecuencia,recargo_porcentaje=Decimal('1') if con_recargo else Decimal('0'),gracia_horas=72,fecha_desembolso=fecha_desembolso,fecha_primera_cuota=fecha_primera_cuota)
        for q in tabla:
            s.add(CuotaModel(prestamo_id=p.id,numero_cuota=q.numero,fecha_vencimiento=q.fecha_vencimiento,saldo_inicial=q.saldo_inicial,cuota_programada=q.pago,abono_capital=q.abono_capital,interes=q.interes))
        auditar(s,user,'prestamo',p.id,'EMITIR',tasa_mensual=str(annual/12),cuotas=plazo_meses,frecuencia=frecuencia,recargo_porcentaje=str(p.recargo_porcentaje),gracia_horas=72)
        return p.id


def registrar_prestamo_mensual(cliente_id,monto_principal,tasa_mensual,plazo_meses,fecha_desembolso,fecha_primera_cuota):
    monthly=Decimal(str(tasa_mensual))
    if not monthly.is_finite() or monthly<0:
        raise ValueError('Ingresa una tasa mensual válida y no negativa.')
    # La columna histórica conserva el equivalente nominal anual; nunca se migran cuotas emitidas.
    annual=(monthly*Decimal('12')).normalize()
    return registrar_prestamo(cliente_id,monto_principal,annual,plazo_meses,fecha_desembolso,fecha_primera_cuota)

def registrar_prestamo_periodico(cliente_id,monto_principal,tasa_mensual,numero_cuotas,fecha_desembolso,fecha_primera_cuota,frecuencia='MENSUAL'):
    mensual=Decimal(str(tasa_mensual))
    if not mensual.is_finite() or mensual<0:raise ValueError('Ingresa una tasa mensual válida y no negativa.')
    return registrar_prestamo(cliente_id,monto_principal,(mensual*12).normalize(),numero_cuotas,fecha_desembolso,fecha_primera_cuota,frecuencia=frecuencia,con_recargo=True)

def actualizar_prestamo(prestamo_id,notas):
    if len(notas)>500: raise ValueError('Las notas admiten hasta 500 caracteres.')
    with transaccion() as s:
        user=exigir_personal(s)
        p=s.get(Prestamo,int(prestamo_id),with_for_update=True)
        if not p: raise ValueError('Préstamo no encontrado.')
        p.notas=notas.strip() or None
        auditar(s,user,'prestamo',p.id,'ACTUALIZAR_NOTAS')

def eliminar_prestamo(prestamo_id,motivo):
    if not motivo.strip(): raise ValueError('Escribe el motivo de la anulación.')
    with transaccion() as s:
        user=exigir_personal(s,administrador=True)
        p=s.get(Prestamo,int(prestamo_id),with_for_update=True)
        if not p: raise ValueError('Préstamo no encontrado.')
        if any(q.monto_pagado>0 or q.pagos for q in p.cuotas): raise ValueError('El préstamo tiene pagos; conserva su historial y revisa los cobros antes de anularlo.')
        if p.estado=='BORRADOR':
            for q in p.cuotas: s.delete(q)
            s.delete(p)
            result='ELIMINADO'
        else:
            p.estado='CANCELADO'
            p.notas=('Anulado: '+motivo.strip())[:500]
            result='ANULADO'
        auditar(s,user,'prestamo',int(prestamo_id),result,motivo=motivo[:500])
        return result

def listar_cuotas_cobro():
    with transaccion() as s:
        exigir_personal(s)
        rows=[cuota_dict(q,p) for p in PrestamosRepositorio(s).cartera() if estado_prestamo(p) in ('ACTIVO','MORA') for q in p.cuotas if q.saldo>0]
        return sorted(rows,key=lambda r:(r['fecha_vencimiento'],r['cliente']))

def obtener_resumen():
    with transaccion() as s:
        exigir_personal(s)
        rows=[q for p in PrestamosRepositorio(s).cartera() if estado_prestamo(p) in ('ACTIVO','MORA') for q in p.cuotas if q.saldo>0]
        overdue=sum(cuota_estado(q)=='VENCIDA' for q in rows)
        return dict(cartera_activa=sum((q.saldo for q in rows),Decimal('0')),cuotas_pendientes=len(rows),pagos_por_verificar=s.scalar(select(func.count()).select_from(Pago).where(Pago.estado=='PENDIENTE_VERIFICACION')),indice_mora=redondear_moneda(Decimal(overdue)*100/len(rows)) if rows else Decimal('0'))

def _aplicar_pago(s,q,amount,pago=None):
    momento=ahora_local()
    p=s.get(Prestamo,q.prestamo_id,with_for_update=True)
    s.expire(p,['cuotas'])
    if q.prestamo.estado not in ('ACTIVO','MORA'): raise ValueError('El préstamo no está activo para recibir pagos.')
    # Una solicitud presentada dentro de la gracia conserva su fecha al verificarse.
    # Solo los movimientos confirmados afectan el capital y el recargo.
    if pago is not None:pago.estado='CONFIRMADO'
    mora=detalle_mora(q,momento)
    if amount<=0 or amount>mora['saldo_total']: raise ValueError('El monto debe ser positivo y no superar el saldo de la cuota.')
    ordinario=min(amount,mora['saldo_ordinario'])
    recargo=amount-ordinario
    q.monto_pagado+=ordinario
    q.recargo_pagado+=recargo
    q.pagado_en=momento
    return recargo

def _actualizar_estados_cobro(s,q):
    # Primero se persiste el desglose y la fecha del movimiento; la mora consulta
    # ese historial, incluso cuando la operación cruza el límite de la gracia.
    s.flush()
    q.estado=cuota_estado(q)
    q.prestamo.estado=estado_prestamo(q.prestamo)

def registrar_cobro(cuota_id,monto,metodo,referencia=''):
    if metodo not in ('EFECTIVO','TRANSFERENCIA','TARJETA'): raise ValueError('Método de pago inválido.')
    amount=dinero(monto)
    with transaccion() as s:
        user=exigir_personal(s)
        q=s.get(CuotaModel,int(cuota_id),with_for_update=True)
        if not q: raise ValueError('Cuota no encontrada.')
        if s.scalar(select(Pago.id).where(Pago.cuota_id==q.id,Pago.estado=='PENDIENTE_VERIFICACION').limit(1)):
            raise ValueError('Hay una solicitud pendiente para esta cuota. Revísala antes de registrar otro cobro.')
        recargo=_aplicar_pago(s,q,amount)
        pg=Repositorio(s,Pago).agregar(cuota_id=q.id,registrado_por=user.id,monto=amount,monto_recargo=recargo,fecha_pago=q.pagado_en,metodo=metodo,referencia=referencia.strip()[:100] or None)
        s.expire(q,['pagos'])
        _actualizar_estados_cobro(s,q)
        auditar(s,user,'pago',pg.id,'REGISTRAR',monto=str(amount),recargo=str(recargo))
        return pg.id

def listar_pagos():
    with transaccion() as s:
        exigir_personal(s)
        rows=s.scalars(select(Pago).options(joinedload(Pago.cuota).joinedload(CuotaModel.prestamo).joinedload(Prestamo.cliente)).order_by(Pago.id.desc())).all()
        return [dict(id=p.id,cliente=p.cuota.prestamo.cliente.nombre,prestamo_id=p.cuota.prestamo_id,numero_cuota=p.cuota.numero_cuota,monto=p.monto,monto_recargo=p.monto_recargo,metodo=p.metodo,referencia=p.referencia,estado=p.estado,fecha_pago=p.fecha_pago,tiene_comprobante=p.comprobante is not None) for p in rows]

def resolver_pago(pago_id,accion,motivo=''):
    if accion not in ('CONFIRMAR','RECHAZAR','ANULAR','EDITAR_REFERENCIA'): raise ValueError('Acción de pago inválida.')
    with transaccion() as s:
        user=exigir_personal(s,administrador=accion=='ANULAR')
        pg=s.get(Pago,int(pago_id),with_for_update=True)
        if not pg: raise ValueError('Pago no encontrado.')
        q=s.get(CuotaModel,pg.cuota_id,with_for_update=True)
        if accion=='EDITAR_REFERENCIA': pg.referencia=motivo.strip()[:100] or None
        elif accion in ('CONFIRMAR','RECHAZAR'):
            if pg.estado!='PENDIENTE_VERIFICACION': raise ValueError('La solicitud ya fue resuelta.')
            if accion=='CONFIRMAR':
                pg.monto_recargo=_aplicar_pago(s,q,pg.monto,pg)
                _actualizar_estados_cobro(s,q)
            pg.estado='CONFIRMADO' if accion=='CONFIRMAR' else 'RECHAZADO'
            pg.registrado_por=user.id
        else:
            if pg.estado!='CONFIRMADO' or not motivo.strip(): raise ValueError('Solo se anulan pagos confirmados indicando un motivo.')
            loan=s.get(Prestamo,q.prestamo_id,with_for_update=True)
            s.expire(loan,['cuotas'])
            ordinario=pg.monto-pg.monto_recargo
            if q.monto_pagado<ordinario or q.recargo_pagado<pg.monto_recargo: raise ValueError('El pago no concuerda con el saldo aplicado.')
            q.monto_pagado-=ordinario
            q.recargo_pagado-=pg.monto_recargo
            pg.estado='ANULADO'
            q.estado=cuota_estado(q)
            if q.monto_pagado==0: q.pagado_en=None
            q.prestamo.estado='ACTIVO'
            q.prestamo.estado=estado_prestamo(q.prestamo)
            pg.notas=motivo[:500]
        auditar(s,user,'pago',pg.id,accion,monto=str(pg.monto),recargo=str(pg.monto_recargo))

def obtener_reporte_cartera(): return listar_prestamos()

def obtener_actividad_reciente():
    with transaccion() as s:
        exigir_personal(s)
        rows=[dict(fecha=p.creado_en,tipo='Préstamo emitido',detalle=f'PR-{p.id:05d} · {p.cliente.nombre}') for p in s.scalars(select(Prestamo).order_by(Prestamo.id.desc()).limit(5))]
        rows.extend(dict(fecha=p.fecha_pago,tipo='Cobro confirmado',detalle=f'C$ {p.monto:,.2f} · {p.cuota.prestamo.cliente.nombre}') for p in s.scalars(select(Pago).where(Pago.estado=='CONFIRMADO').order_by(Pago.id.desc()).limit(5)))
        return sorted(rows,key=lambda r:r['fecha'],reverse=True)[:5]

def listar_empleados():
    with transaccion() as s:
        exigir_personal(s,administrador=True)
        return [dict(id=e.id,usuario_id=e.usuario_id,cedula=e.cedula,nombres=e.nombres,apellidos=e.apellidos,nombre=f'{e.nombres} {e.apellidos}',telefono=e.telefono,correo=e.correo,cargo=e.cargo,nombre_usuario=e.usuario.nombre_usuario,activo=e.usuario.activo,rol=e.usuario.rol) for e in s.scalars(select(Empleado).options(joinedload(Empleado.usuario)).order_by(Empleado.id.desc()))]

def guardar_empleado(cedula,nombres,apellidos,telefono,correo,cargo,nombre_usuario,contrasena,activo=True,empleado_id=None):
    data=validar_persona(cedula,nombres,apellidos,telefono,correo)
    cedula,nombres,apellidos,telefono,correo=(data[k] for k in ('cedula','nombres','apellidos','telefono','correo'))
    cargo=normalizar_nombre(cargo,'cargo')
    if not 4<=len(nombre_usuario.strip())<=60 or not cargo.strip() or len(cargo)>80: raise ValueError('Usuario o cargo inválido.')
    password_hash=generar_hash_contrasena(contrasena) if contrasena else None
    if empleado_id is None and not password_hash: raise ValueError('Asigna una contraseña al nuevo empleado.')
    with transaccion() as s:
        actor=exigir_personal(s,administrador=True)
        if empleado_id is None:
            user=Repositorio(s,Usuario).agregar(nombre_usuario=nombre_usuario.strip(),hash_contrasena=password_hash,rol='EMPLEADO',activo=bool(activo))
            e=Repositorio(s,Empleado).agregar(usuario_id=user.id,cedula=cedula.strip(),nombres=nombres.strip(),apellidos=apellidos.strip(),telefono=telefono.strip(),correo=correo.strip() or None,cargo=cargo.strip())
        else:
            e=s.get(Empleado,int(empleado_id),with_for_update=True)
            if not e: raise ValueError('Empleado no encontrado.')
            user=e.usuario
            user.nombre_usuario=nombre_usuario.strip()
            user.activo=bool(activo)
            if password_hash:
                from crece.servicios.recuperacion import invalidar_codigos
                user.hash_contrasena=password_hash
                user.version_sesion+=1
                invalidar_codigos(s,user.id)
            for key,value in dict(cedula=cedula,nombres=nombres,apellidos=apellidos,telefono=telefono,correo=correo,cargo=cargo).items(): setattr(e,key,value.strip() or None)
        auditar(s,actor,'empleado',e.id,'ACTUALIZAR' if empleado_id else 'CREAR')
        return e.id

def eliminar_empleado(empleado_id):
    with transaccion() as s:
        actor=exigir_personal(s,administrador=True)
        e=s.get(Empleado,int(empleado_id),with_for_update=True)
        if not e: raise ValueError('Empleado no encontrado.')
        user=e.usuario
        from crece.infraestructura.modelos import RecuperacionContrasena
        used=s.scalar(select(RecuperacionContrasena.id).where(RecuperacionContrasena.usuario_id==user.id).limit(1)) or s.scalar(select(func.count()).select_from(Prestamo).where(Prestamo.creado_por==user.id)) or s.scalar(select(func.count()).select_from(Pago).where(Pago.registrado_por==user.id)) or s.scalar(select(func.count()).select_from(Auditoria).where(Auditoria.usuario_actor_id==user.id))
        if used:
            user.activo=False
            result='DESACTIVADO'
        else:
            s.delete(e)
            s.flush()
            s.delete(user)
            result='ELIMINADO'
        auditar(s,actor,'empleado',int(empleado_id),result)
        return result
