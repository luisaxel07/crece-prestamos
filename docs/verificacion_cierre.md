# Verificación de cierre · 22/10/2026

## Pruebas y correcciones

Se revisaron 94 casos distintos de autenticación, roles, ORM, datos, interfaces, reportes y recuperación. La revisión integral detectó un problema de MySQL al contar filas sin cambios, que se corrigió con FOUND_ROWS; la siguiente comprobación completa confirmó esa corrección y detectó un caso de carga de la vista previa. Se corrigió la espera del estado Ready del visor PDF y se amplió la espera acotada de su prueba para equipos con carga.

Las suites afectadas se repitieron después de las correcciones:

| Comprobación final | Resultado |
| --- | --- |
| Contrato MySQL para UPDATE sin cambios | 1 prueba correcta |
| Impresión, PDF, Excel y marca | 4 pruebas correctas |
| Recuperación, consumo concurrente y revocación de sesiones | 12 pruebas correctas, con el reloj UTC de MySQL |
| Diálogos nativos de recuperación y alta informativa | 3 pruebas correctas dentro de la revisión integral |
| Navegador con ORM MySQL | Emisión administrativa, cambio de contraseña e ingreso con la nueva clave correctos |
| Adaptación del formulario web | 1440, 1024, 390 y 320 px, sin desbordamiento horizontal ni errores de JavaScript |

Los 94 casos cuentan funciones distintas; las repeticiones no aumentan ese número. Se documentan los resultados de la revisión y las repeticiones, sin presentarlos como una única ejecución integral limpia posterior a todos los ajustes. Para repetir la suite completa: `python -m unittest discover -s tests -v`.

La integración se realizó exclusivamente en esquemas MySQL temporales con datos ficticios, no en las tablas del proyecto. El código no admite un motor alternativo. Las pruebas visuales que no necesitan persistencia utilizan servicios controlados.

## Datos existentes

La migración aditiva de recuperación se aplicó correctamente. `database/verificacion_migracion_recuperacion.json` registra huellas SHA-256 idénticas antes y después para 3 clientes, 1 préstamo, 12 cuotas y 3 pagos. No se modificaron condiciones financieras ni contraseñas existentes.

## Documentación y entrega

La justificación académica contiene 11 páginas con correspondencia de sesiones, énfasis en ORM/reportes, extensiones actuales y recuperación asistida. Se verificó su composición y el logo en sus páginas. La fuente editable está en `docs/justificacion_academica.md`, la copia PDF en `docs/justificacion_academica_CRECE_PRESTAMOS.pdf` y el generador en `tools/generar_justificacion.py`.

La guía `docs/control_versiones_git.md` contiene comandos por bloques para que el responsable genere personalmente sus commits y evidencias. Solo se prepararon la guía, .gitignore y un ejemplo público de conexión. No se ejecutaron comandos Git, no se crearon commits y no se publicó en GitHub.

Reiniciar escritorio y servidor web para cargar esta entrega. No se envió nada a una impresora física ni se simularon correos de recuperación.
