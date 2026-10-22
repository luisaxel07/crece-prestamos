from datetime import date
from decimal import Decimal

from crece.nucleo.amortizacion import calcular_tabla_francesa


def probar_saldo_final_y_capital():
    tabla = calcular_tabla_francesa(Decimal("10000"), Decimal("24"), 12, date(2026, 1, 15))
    assert len(tabla) == 12
    assert tabla[-1].saldo_final == Decimal("0.00")
    assert sum(cuota.abono_capital for cuota in tabla) == Decimal("10000.00")
    assert tabla[0].pago == tabla[1].pago


def probar_tasa_cero():
    tabla = calcular_tabla_francesa(Decimal("1200"), Decimal("0"), 12, date(2026, 1, 31))
    assert all(cuota.pago == Decimal("100.00") for cuota in tabla)
    assert tabla[1].fecha_vencimiento.isoformat() == "2026-02-28"
