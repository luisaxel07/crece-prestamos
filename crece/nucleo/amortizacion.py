"""Cálculo reproducible del método francés usando Decimal, nunca float."""
from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

CENTAVO = Decimal("0.01")


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
    monto_principal = Decimal(monto_principal)
    tasa_anual = Decimal(tasa_anual)
    if not monto_principal.is_finite() or not tasa_anual.is_finite() or monto_principal <= 0 or not 1 <= plazo_meses <= 600 or tasa_anual < 0:
        raise ValueError("Monto, plazo y tasa inválidos")
    monto_principal = redondear_moneda(monto_principal)
    if monto_principal <= 0:
        raise ValueError("El monto debe ser al menos un centavo")
    tasa_mensual = tasa_anual / Decimal("1200")
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
        tabla.append(Cuota(numero, sumar_meses(fecha_primera_cuota, numero - 1), saldo, pago, abono_capital, interes, saldo_final))
        saldo = saldo_final
    return tabla


def calcular_tabla_mensual(monto_principal: Decimal, tasa_mensual: Decimal, plazo_meses: int, fecha_primera_cuota: date) -> list[Cuota]:
    """Tasa mensual nominal: 2 % mensual equivale a 24 % nominal anual."""
    return calcular_tabla_francesa(monto_principal, Decimal(tasa_mensual)*Decimal('12'), plazo_meses, fecha_primera_cuota)
