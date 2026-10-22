# Validaciones de entrada en web y escritorio

Las reglas de clientes y empleados se aplican tanto al crear como al editar. Los servicios compartidos validan antes de escribir en la base de datos. Las restricciones de captura se aplican al escribir y pegar; omitir JavaScript o enviar un formulario manipulado no permite guardar datos inválidos.

| Campo | Regla y ejemplo válido |
| --- | --- |
| Nombres y apellidos | Letras y espacios, incluidas tildes y ñ. Ejemplos: María José / Pérez López. No admite números, emojis, guiones ni otros signos. Máximo 80 caracteres por campo. |
| Cédula nicaragüense | `000-DDMMAA-0000A`. Tres dígitos, seis de fecha, cuatro de serie y una letra de A a Z. Ejemplo: `001-150890-0001A`. Los guiones aparecen al escribir; la letra se convierte a mayúscula. También se puede pegar el número completo sin guiones. |
| Fecha en cédula | La combinación día/mes/año debe existir en el calendario. Se rechazan 31 de febrero, mes 13, día 00 y 29 de febrero en un año no bisiesto. Los dos dígitos del año no permiten determinar el siglo o la edad sin otro dato; no se inventa esa información. |
| Teléfono | Entre 8 y 15 dígitos, sin letras ni separadores. Ejemplo local: `88888888`. |
| Correo | Dirección válida sin espacios, con usuario y dominio. Ejemplo: `nombre@correo.com`. Se guarda en minúscula; vacío únicamente si el campo es opcional. |
| Cargo | Letras y espacios; ejemplo: Asesor de crédito. Hasta 80 caracteres. |
| Dirección | Texto libre hasta 255 caracteres. Puede incluir letras y números, porque una dirección necesita ambos. |
| Usuario de acceso | Se distingue del nombre de la persona. Conserva su regla de 4 a 60 caracteres y admite números. |
| Importes, tasa y plazo | Importes numéricos de hasta 2 decimales, tasa de hasta 4 decimales y plazo entero de 1 a 600 meses. Las reglas de saldo, fechas y límites del préstamo continúan verificándose en los servicios. |

Los ejemplos no se utilizan como valores iniciales en los datos personales. Las etiquetas indican qué campos son obligatorios; los textos de ayuda explican el dato admitido y el error identifica el campo a corregir. El botón de guardar permanece utilizable después de corregir un dato.

En ambos canales, las cédulas `0011508900001a` y `001-150890-0001a` se guardan como `001-150890-0001A`. Las restricciones existentes de unicidad de la base siguen evitando duplicados. No se modificaron automáticamente los registros existentes; una ficha editada debe cumplir las reglas al volver a guardarse.

La validación comprueba la estructura solicitada y el calendario. No consulta al CSE ni acredita que una cédula haya sido emitida. No se impone una lista de códigos municipales ni un cálculo de letra verificadora no solicitado.

## Organización

- `crece/nucleo/validaciones.py`: validación y normalización común.
- `portal_web/static/reglas-formularios.json`: límites, patrones, ejemplos y ayudas utilizados por Python, Qt y web.
- `ui/validacion_campos.py`: restricciones y ayuda de captura en PySide6.
- `portal_web/static/validaciones.js`: restricciones al escribir/pegar, formato automático, calendario y mensajes accesibles.
- `tests/test_validations.py`: pruebas de reglas, servicios ORM, formularios y teclado/pegado Qt.

Ejecutar `python -m unittest discover -s tests -v`. Las pruebas usan MySQL en un esquema temporal exclusivo y no cambian la base del proyecto.
## Verificación de la actualización

La comprobación completa incluye web, escritorio, permisos, ORM, reportes, validaciones y recuperación. El resultado vigente se documenta en la justificación académica. Las comprobaciones de PySide6 incluyen escritura, pegado y borrado junto a los guiones. En el navegador se comprobó el rechazo de números en nombres, la fecha de la cédula, la letra final mayúscula guardada, la recuperación del formulario después de un error, el simulador y una vista móvil de 390 px, sin errores de JavaScript ni desbordamiento horizontal.
