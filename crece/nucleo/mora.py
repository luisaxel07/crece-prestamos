"""Recargo simple por cuota; calendario de Nicaragua y pagos verificados.

La gracia empieza al terminar el día de vencimiento. Los pagos se imputan
primero al interés ordinario, después al capital y por último al recargo.
"""
from datetime import datetime,time,timedelta,timezone
from decimal import Decimal
from .amortizacion import redondear_moneda

NICARAGUA=timezone(timedelta(hours=-6))

def ahora_local():
    # MySQL DATETIME guarda segundos: la evaluación y el recibo usan la misma
    # precisión, evitando cobrar por fracciones que el historial no conservaría.
    return datetime.now(timezone.utc).astimezone(NICARAGUA).replace(tzinfo=None,microsecond=0)

def limite_gracia(fecha,horas=72):
    return datetime.combine(fecha+timedelta(days=1),time.min)+timedelta(hours=horas)

def detalle_mora(cuota,ahora=None):
    ahora=ahora or ahora_local()
    p=cuota.prestamo
    tasa=p.recargo_porcentaje or Decimal('0')
    limite=limite_gracia(cuota.fecha_vencimiento,p.gracia_horas or 72)
    saldo_base=max(Decimal('0'),cuota.cuota_programada-cuota.monto_pagado)
    base=Decimal('0');recargo=Decimal('0')
    if tasa>0 and ahora>limite and p.estado not in ('CANCELADO','BORRADOR'):
        temprano=sum((pg.monto-(pg.monto_recargo or Decimal('0')) for pg in cuota.pagos
                      if pg.estado=='CONFIRMADO' and pg.fecha_pago<=limite),Decimal('0'))
        capital_pagado=max(Decimal('0'),temprano-cuota.interes)
        base=max(Decimal('0'),cuota.abono_capital-capital_pagado)
        recargo=redondear_moneda(base*tasa/Decimal('100'))
    pagado=cuota.recargo_pagado or Decimal('0')
    pendiente=max(Decimal('0'),recargo-pagado)
    aviso=''
    if saldo_base+pendiente>0 and p.estado not in ('CANCELADO','BORRADOR'):
        if ahora.date()==cuota.fecha_vencimiento:aviso='VENCE_HOY'
        elif ahora.date()>cuota.fecha_vencimiento:
            aviso='EN_GRACIA' if tasa>0 and ahora<=limite else 'VENCIDA'
    return dict(recargo=recargo,recargo_pagado=pagado,recargo_pendiente=pendiente,
                capital_base_mora=base,saldo_ordinario=saldo_base,saldo_total=saldo_base+pendiente,
                limite_gracia=limite,aviso_pago=aviso)
