# Frecuencias, préstamo vigente y mora

Las reglas son compartidas por el portal web y la aplicación PySide6. El servidor valida las operaciones; los formularios no pueden saltarse las restricciones.

## Condiciones de préstamos nuevos

El personal elige la frecuencia y un número entero de 1 a 600 cuotas. La primera fecha se selecciona explícitamente y debe ser posterior al desembolso.

| Frecuencia | Calendario | Tasa del período desde la tasa mensual |
| --- | --- | --- |
| Mensual | Mismo día del mes, ajustado al último día cuando corresponda | Tasa mensual |
| Quincenal | Cada 15 días calendario | Mensual / 2 |
| Semanal | Cada 7 días calendario | Mensual × 12 / 52 |
| Diario | Cada día calendario, incluidos fines de semana | Mensual / 30 |

Las conversiones son nominales proporcionales aprobadas para el proyecto. Se usa Decimal y amortización francesa con ajuste de centavos en la última cuota. La tasa del período se muestra junto con el interés monetario. La proyección excluye recargos futuros.

Por compatibilidad, las columnas históricas `plazo_meses` y `cuota_mensual` guardan respectivamente el número de cuotas y el importe periódico; la frecuencia determina su significado. Las interfaces los presentan como «Número de cuotas» y «Cuota periódica». La columna anual conserva el equivalente nominal mensual × 12. No se recalculan contratos anteriores.

## Un préstamo sin saldar por cliente

Antes de emitir se bloquea la fila del cliente en una transacción MySQL. Se revisan todos sus contratos no cancelados ni borradores, incluyendo los recargos pendientes. Si existe deuda, se muestra el código del préstamo y se explica que debe saldarse primero. La comprobación también cubre dos operadores emitiendo simultáneamente.

Los préstamos cancelados no bloquean nuevas emisiones. Un contrato totalmente saldado conserva su historial y permite emitir otro.

## Gracia y recargo

- Aviso en el portal desde el día del vencimiento.
- Gracia de 72 horas completas desde el final de ese día, en horario de Nicaragua.
- Durante la gracia no se aplica recargo.
- Después se cobra una sola vez el 1 % del capital de esa cuota que seguía pendiente al terminar la gracia, redondeado a centavos.
- No se cobra recargo sobre interés ordinario ni sobre otro recargo. No aumenta diariamente ni modifica la tasa pactada.
- Los pagos se distribuyen primero al interés ordinario, luego al capital y finalmente al recargo. La base del recargo se reconstruye con los pagos confirmados dentro de la gracia, por lo que un abono posterior no genera otra multa ni borra la ya causada.
- También se aplica a la última cuota. El préstamo no se considera saldado mientras quede un recargo pendiente.

Ejemplo: una cuota vence el 1 de octubre. La gracia termina el 5 de octubre a las 00:00; solo después de ese instante puede aplicarse el recargo. Si la cuota tiene C$ 1,000 de capital y C$ 20 de interés, y se pagan C$ 520 dentro de la gracia, quedan C$ 500 de capital y el recargo único es C$ 5.

## Transferencias, revisión y anulaciones

Enviar un comprobante no confirma el ingreso. Una solicitud confirmada conserva la fecha de envío para evaluar la gracia; así una revisión tardía no penaliza al cliente. Las solicitudes pendientes, rechazadas o anuladas no se consideran pagos recibidos.

Mientras exista una solicitud pendiente para una cuota, el personal debe revisarla antes de registrar otro cobro. Esto evita duplicar pagos y modificar la base de mora durante la revisión. Los pagos confirmados guardan por separado el importe destinado a recargo; su anulación revierte ambos componentes y deja auditoría.

El saldo total, el recargo pendiente y los importes ordinarios se distinguen en web, escritorio, PDF y Excel. Los recordatorios aparecen al consultar o recargar el portal; no se simulan correos ni notificaciones externas.

## Instalación y datos anteriores

Con MySQL disponible, ejecutar desde la carpeta de la aplicación:

```console
python database/actualizar_frecuencias_mora.py --aplicar
```

La migración añade columnas con frecuencia MENSUAL y recargo 0 para los contratos ya existentes. Compara el número de registros y la huella SHA-256 de todas las columnas previas de clientes, préstamos, cuotas y pagos; guarda el resultado en `database/verificacion_migracion_frecuencias.json`. Es aditiva e idempotente. Reiniciar web y escritorio después de actualizar.

Pruebas específicas: `test_frecuencias.py`, `test_mora.py`, `test_prestamo_unico.py` y `test_frecuencia_mora_mysql.py`, además de las comprobaciones de formularios web, simulador Qt e impresión. La integración usa únicamente un esquema MySQL temporal creado por las pruebas.

Verificación realizada el 22/10/2026: calendarios y conversiones, pagos parciales y completos, gracia exacta, revisión tardía de transferencias, anulación y distribución del recargo, bloqueo con operadores simultáneos, formularios por rol, simulador Qt, PDF e impresión y Excel con datos tipados. La revisión en navegador cubrió 15 combinaciones de pantalla y tamaño (1440, 390 y 320 px), sin desbordamiento horizontal ni errores de JavaScript. Los recordatorios tienen un resumen visible y detalle desplegable.
