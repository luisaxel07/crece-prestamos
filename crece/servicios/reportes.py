"""Una instantánea ORM alimenta vista, PDF, Excel e impresión sin recalcular contratos."""
from datetime import datetime
from decimal import Decimal
from crece.infraestructura.base_datos import transaccion
from crece.infraestructura.modelos import Cliente
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

def limitar_reporte(reporte,ids):
    """Exporta las filas visibles sin incluir préstamos descartados por los filtros."""
    report={**reporte,'prestamos':[p for p in reporte['prestamos'] if p['id'] in ids]}
    valid=[p for p in report['prestamos'] if p['estado'] not in ('CANCELADO','BORRADOR')]
    quotas=[q for p in valid for q in p['cuotas']]
    report['totales']=totales_cartera(report['prestamos'])
    return report
