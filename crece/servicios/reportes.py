"""Una instantánea ORM alimenta vista, PDF, Excel e impresión sin recalcular contratos."""
from datetime import datetime,date,time,timedelta
from decimal import Decimal
from crece.infraestructura.base_datos import transaccion
from crece.infraestructura.modelos import Cliente
from crece.nucleo.amortizacion import redondear_moneda
from crece.nucleo.mora import detalle_mora,ahora_local
from crece.infraestructura.repositorios import PrestamosRepositorio
from crece.servicios.permisos import exigir_personal
from crece.servicios.gestion import prestamo_dict,cuota_dict,cliente_dict

def totales_cartera(prestamos):
    valid=[p for p in prestamos if p['estado'] not in ('CANCELADO','BORRADOR')]
    cuotas=[q for p in valid for q in p['cuotas']]
    total=lambda campo:sum((q.get(campo,Decimal('0')) for q in cuotas),Decimal('0'))
    return dict(principal=sum((p['monto_principal'] for p in valid),Decimal('0')),interes=total('interes'),programado=total('cuota_programada'),cobrado=total('monto_pagado')+total('recargo_pagado'),saldo=total('saldo'),recargos=total('recargo'),recargos_cobrados=total('recargo_pagado'),recargos_pendientes=total('recargo_pendiente'))

def obtener_reporte(cliente_id=None,prestamo_id=None):
    with transaccion() as s:
        actor=exigir_personal(s)
        rows=PrestamosRepositorio(s).cartera(cliente_id,prestamo_id)
        if prestamo_id is not None and not rows: raise ValueError('Préstamo no encontrado.')
        client=None
        if cliente_id is not None:
            c=s.get(Cliente,int(cliente_id))
            if not c: raise ValueError('Cliente no encontrado.')
            client=cliente_dict(c)
        elif prestamo_id is not None: client=cliente_dict(rows[0].cliente)
        loans=[dict(**prestamo_dict(p),cuotas=[cuota_dict(q,p) for q in p.cuotas]) for p in rows]
        valid=[p for p in loans if p['estado'] not in ('CANCELADO','BORRADOR')]
        quotas=[q for p in valid for q in p['cuotas']]
        totals=totales_cartera(loans)
        return dict(titulo='Ficha de préstamo y plan de cuotas' if prestamo_id is not None else 'Estado de cuenta del cliente' if client else 'Reporte general de cartera',generado_en=datetime.now(),generado_por=actor.nombre_usuario,cliente=client,prestamos=loans,totales=totals)

def cotizar_liquidacion(prestamo_id,fecha):
    """Cotiza una liquidacion anticipada; nunca registra cobros ni altera el plan."""
    if not isinstance(fecha,date):
        raise ValueError('Indica una fecha valida para la liquidacion.')
    if fecha<ahora_local().date():
        raise ValueError('La fecha de liquidacion no puede ser anterior a hoy.')
    with transaccion() as s:
        exigir_personal(s)
        rows=PrestamosRepositorio(s).cartera(prestamo_id=prestamo_id)
        if not rows: raise ValueError('Prestamo no encontrado.')
        p=rows[0]
        if p.estado in ('CANCELADO','BORRADOR'):
            raise ValueError('Solo se puede cotizar un prestamo emitido y activo.')
        momento=datetime.combine(fecha,time.max)
        vencidas=Decimal('0');recargos=Decimal('0');capital_futuro=Decimal('0')
        fecha_base=p.fecha_desembolso
        for q in p.cuotas:
            if q.fecha_vencimiento<=fecha:
                vencidas+=max(Decimal('0'),q.cuota_programada-q.monto_pagado)
                recargos+=detalle_mora(q,momento)['recargo_pendiente']
                fecha_base=max(fecha_base,q.fecha_vencimiento)
            else:
                pagado_capital=max(Decimal('0'),q.monto_pagado-min(q.monto_pagado,q.interes))
                capital_futuro+=max(Decimal('0'),q.abono_capital-pagado_capital)
        dias=max(0,(fecha-fecha_base).days)
        if p.metodo_interes=='PLANO' and capital_futuro>0:
            siguiente=next((q for q in p.cuotas if q.fecha_vencimiento>fecha),None)
            periodo_dias=max(1,(siguiente.fecha_vencimiento-fecha_base).days) if siguiente else 1
            interes_devengado=redondear_moneda(siguiente.interes*Decimal(min(dias,periodo_dias))/Decimal(periodo_dias)) if siguiente else Decimal('0.00')
        else:
            interes_devengado=redondear_moneda(capital_futuro*p.tasa_mensual*Decimal(dias)/Decimal('3000'))
        vencidas=redondear_moneda(vencidas)
        recargos=redondear_moneda(recargos)
        capital_futuro=redondear_moneda(capital_futuro)
        total=redondear_moneda(vencidas+recargos+capital_futuro+interes_devengado)
        return dict(prestamo_id=p.id,cliente=p.cliente.nombre,fecha=fecha,dias_desde_ultimo_vencimiento=dias,
                    cuotas_vencidas_pendientes=vencidas,recargos_pendientes=recargos,
                    capital_futuro=capital_futuro,interes_devengado=interes_devengado,total=total,
                    tasa_mensual=p.tasa_mensual)


def limitar_reporte(reporte,ids):
    """Exporta las filas visibles sin incluir préstamos descartados por los filtros."""
    report={**reporte,'prestamos':[p for p in reporte['prestamos'] if p['id'] in ids]}
    valid=[p for p in report['prestamos'] if p['estado'] not in ('CANCELADO','BORRADOR')]
    quotas=[q for p in valid for q in p['cuotas']]
    report['totales']=totales_cartera(report['prestamos'])
    return report
