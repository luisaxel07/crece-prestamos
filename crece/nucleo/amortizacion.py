"""Cálculo reproducible del método francés usando Decimal, nunca float."""
from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date,timedelta
from decimal import Decimal, ROUND_HALF_UP

CENTAVO = Decimal("0.01")
FRECUENCIAS = {'MENSUAL':'Mensual','QUINCENAL':'Quincenal (cada 15 días)','SEMANAL':'Semanal (cada 7 días)','DIARIO':'Diario'}
TIPOS_CREDITO={'ASALARIADO':'Asalariado','COMERCIAL':'Credito comercial'}
TASAS_TIPO_CREDITO={'ASALARIADO':Decimal('12'),'COMERCIAL':Decimal('14')}
METODOS_INTERES={'FRANCES':'Frances sobre saldo','PLANO':'Plano sobre capital inicial'}

def normalizar_metodo_interes(metodo):
    valor=str(metodo).strip().upper()
    if valor not in METODOS_INTERES: raise ValueError('Selecciona un metodo de interes valido.')
    return valor


def normalizar_frecuencia(frecuencia):
    valor=str(frecuencia).strip().upper()
    if valor not in FRECUENCIAS:raise ValueError('Selecciona una frecuencia mensual, quincenal, semanal o diaria.')
    return valor

def fecha_cuota(primera,indice,frecuencia):
    frecuencia=normalizar_frecuencia(frecuencia)
    if frecuencia=='MENSUAL':return sumar_meses(primera,indice)
    return primera+timedelta(days={'QUINCENAL':15,'SEMANAL':7,'DIARIO':1}[frecuencia]*indice)


def redondear_moneda(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def sumar_meses(fecha: date, meses: int) -> date:
    indice = fecha.month - 1 + meses
    anio, mes = fecha.year + indice // 12, indice % 12 + 1
    return date(anio, mes, min(fecha.day, monthrange(anio, mes)[1]))


@dataclass(frozen=True)
class Cuota:
    numero: int
    fecha_vencimiento: date
    saldo_inicial: Decimal
    pago: Decimal
    abono_capital: Decimal
    interes: Decimal
    saldo_final: Decimal


def calcular_tabla_francesa(monto_principal: Decimal, tasa_anual: Decimal, plazo_meses: int, fecha_primera_cuota: date) -> list[Cuota]:
    """Calcula las cuotas francesas y ajusta solo la última por redondeo monetario."""
    tasa_anual = Decimal(tasa_anual)
    return _calcular_tabla(monto_principal,tasa_anual/Decimal('1200'),plazo_meses,fecha_primera_cuota,'MENSUAL')


def calcular_tabla_periodica(monto_principal: Decimal, tasa_periodica: Decimal, numero_cuotas: int, fecha_primera_cuota: date, frecuencia: str, metodo_interes="FRANCES") -> list[Cuota]:
    """El interés recibido es el porcentaje del período elegido, no una tasa anual."""
    return _calcular_tabla(monto_principal,Decimal(tasa_periodica)/Decimal('100'),numero_cuotas,fecha_primera_cuota,frecuencia,metodo_interes)


def _calcular_tabla(monto_principal,tasa_mensual,plazo_meses,fecha_primera_cuota,frecuencia,metodo_interes="FRANCES"):
    frecuencia=normalizar_frecuencia(frecuencia)
    metodo_interes=normalizar_metodo_interes(metodo_interes)
    monto_principal = Decimal(monto_principal)
    if not isinstance(plazo_meses,int) or isinstance(plazo_meses,bool) or not isinstance(fecha_primera_cuota,date):
        raise ValueError('Indica un número entero de cuotas y una fecha válida.')
    if not monto_principal.is_finite() or not tasa_mensual.is_finite() or monto_principal <= 0 or not 1 <= plazo_meses <= 600 or tasa_mensual < 0:
        raise ValueError("Monto, plazo y tasa inválidos")
    monto_principal = redondear_moneda(monto_principal)
    if monto_principal <= 0:
        raise ValueError("El monto debe ser al menos un centavo")
    tabla: list[Cuota] = []
    saldo = monto_principal
    if metodo_interes=='PLANO':
        capital_periodo=redondear_moneda(monto_principal/plazo_meses)
        interes_periodo=redondear_moneda(monto_principal*tasa_mensual)
        for numero in range(1,plazo_meses+1):
            abono_capital=saldo if numero==plazo_meses else min(saldo,capital_periodo)
            interes=interes_periodo
            pago=redondear_moneda(abono_capital+interes)
            saldo_final=redondear_moneda(saldo-abono_capital)
            tabla.append(Cuota(numero,fecha_cuota(fecha_primera_cuota,numero-1,frecuencia),saldo,pago,abono_capital,interes,saldo_final))
            saldo=saldo_final
        return tabla
    if tasa_mensual == 0:
        pago_fijo = redondear_moneda(monto_principal / plazo_meses)
    else:
        factor = (Decimal("1") + tasa_mensual) ** plazo_meses
        pago_fijo = redondear_moneda(monto_principal * (tasa_mensual * factor) / (factor - Decimal("1")))
    tabla: list[Cuota] = []
    saldo = monto_principal
    for numero in range(1, plazo_meses + 1):
        interes = redondear_moneda(saldo * tasa_mensual)
        pago = pago_fijo
        abono_capital = redondear_moneda(pago - interes)
        if numero == plazo_meses:
            abono_capital = saldo
            pago = redondear_moneda(abono_capital + interes)
        saldo_final = redondear_moneda(saldo - abono_capital)
        tabla.append(Cuota(numero, fecha_cuota(fecha_primera_cuota, numero - 1, frecuencia), saldo, pago, abono_capital, interes, saldo_final))
        saldo = saldo_final
    return tabla


def calcular_tabla_mensual(monto_principal: Decimal, tasa_mensual: Decimal, plazo_meses: int, fecha_primera_cuota: date, metodo_interes="FRANCES") -> list[Cuota]:
    """Calcula una tabla mensual con tasa nominal y metodo de interes seleccionable."""
    return _calcular_tabla(monto_principal,Decimal(tasa_mensual)/Decimal('100'),plazo_meses,fecha_primera_cuota,'MENSUAL',metodo_interes)

def tasa_por_periodo(tasa_mensual,frecuencia):
    frecuencia=normalizar_frecuencia(frecuencia)
    tasa=Decimal(str(tasa_mensual))
    if not tasa.is_finite() or tasa<0:raise ValueError('Ingresa una tasa mensual válida y no negativa.')
    if frecuencia=='QUINCENAL':return tasa/Decimal('2')
    if frecuencia=='SEMANAL':return tasa*Decimal('12')/Decimal('52')
    if frecuencia=='DIARIO':return tasa/Decimal('30')
    return tasa

def calcular_tabla_credito(monto,tasa_mensual,numero_cuotas,primera_cuota,frecuencia='MENSUAL',metodo_interes='FRANCES'):
    frecuencia=normalizar_frecuencia(frecuencia)
    metodo_interes=normalizar_metodo_interes(metodo_interes)
    if frecuencia=='MENSUAL':return calcular_tabla_mensual(monto,tasa_mensual,numero_cuotas,primera_cuota,metodo_interes)
    return calcular_tabla_periodica(monto,tasa_por_periodo(tasa_mensual,frecuencia),numero_cuotas,primera_cuota,frecuencia,metodo_interes)
