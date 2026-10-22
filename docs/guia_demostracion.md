# Demostración de CRECE+ PRÉSTAMOS ante el jurado

Usa expedientes ficticios y credenciales de demostración. No proyectes comprobantes, datos de clientes reales ni códigos de recuperación vigentes.

## Recorrido recomendado

1. Explica la arquitectura: PySide6 y Flask comparten servicios, entidades SQLAlchemy, repositorios y MySQL. Muestra una entidad, una relación y `transaccion()` con rollback.
2. Inicia sesión como administrador. En Empleados, crea un asesor ficticio con cédula válida, nombres alfabéticos, cargo, usuario propio y contraseña. Edita su expediente. Las mismas credenciales funcionan en web y escritorio.
3. Ingresa como asesor y muestra gestión de clientes, emisión, cobros y reportes. Las cuentas, empleados y bajas administrativas no están autorizadas para ese rol.
4. Demuestra validaciones: rechaza números en nombres, fecha imposible en cédula y monto con letras. Usa un ejemplo ficticio válido como `001-150890-0001A`; explica los guiones automáticos y la letra final mayúscula. El guardado vuelve a validar aunque se manipule la interfaz.
5. Registra un cliente ficticio y emite C$ 10,000 con 2 % mensual y 3 meses. La primera cuota debe ser posterior al desembolso. Explica que es una tasa nominal mensual y que los préstamos históricos no se recalculan.
6. Abre la ficha del préstamo: cliente, responsable, tasa de cada cuota, capital inicial, interés, amortización y saldo. Guarda PDF/Excel y abre la vista previa A4 horizontal con zoom y páginas. En Excel revisa el logo de cada hoja, bordes, filtros, fechas y números.
7. En Reportes, elige alcance general, cliente y préstamo. Aplica un filtro y comprueba que el archivo contiene ese alcance. Explica el saldo programado, que incluye capital e interés pendientes.
8. Habilita la cuenta vinculada al cliente e ingresa en web. Adjunta una foto ficticia del comprobante y una referencia textual para informar un pago ya realizado. La solicitud queda pendiente; el saldo no disminuye por enviar la foto.
9. Ingresa como empleado y abre la solicitud, compara la imagen y referencia y confirma solo después de comprobar el ingreso. Muestra que una segunda confirmación no vuelve a aplicar dinero. El administrador puede anular con motivo y conservar el historial.
10. Muestra CRUD: crear, leer, actualizar y eliminar un cliente sin préstamos. Con historial, la baja inactiva y conserva relaciones. Un préstamo emitido sin pagos se anula conservando cuotas; con movimientos se protege. No modifiques contratos reales para demostrarlo.
11. Con el administrador, abre Usuarios/Cuentas y permisos → Recuperar acceso para la cuenta ficticia del asesor. Verifica su identidad, deja constancia, confirma tu contraseña y emite un código. El titular abre ¿Olvidaste tu contraseña?, elige una contraseña nueva y vuelve a iniciar sesión. El código no funciona dos veces y las sesiones anteriores se rechazan. No publiques el código en las evidencias.
12. Desactiva al asesor y comprueba que no puede iniciar sesión ni operar con una sesión previa. Termina mostrando auditoría, las pruebas y la correspondencia con las sesiones 28–36 de ORM y reportes. Git/GitHub se demostrará aparte con comandos y commits ejecutados por el responsable.

## Verificación reproducible

Desde `CRECE Prestamos`, ejecuta `python -m unittest discover -s tests -v`.

Las pruebas de integración utilizan exclusivamente MySQL/InnoDB en un esquema temporal `crece_pruebas_<identificador aleatorio>`. Crean datos ficticios y eliminan únicamente ese esquema. Se necesitan permisos CREATE/DROP DATABASE; las tablas del proyecto no se vacían ni se usan como datos de prueba. Las comprobaciones de interfaz sin persistencia usan servicios controlados.

Las huellas de conservación están en `database/verificacion_migracion_orm.json`, `verificacion_migracion_comprobantes.json` y `verificacion_migracion_recuperacion.json`. El procedimiento de recuperación se detalla en `docs/recuperacion_asistida.md`. La justificación académica y su PDF están actualizados al 22/10/2026.

Los archivos en `../output/` son ejemplos ficticios. La comprobación no sustituye impresión física, prueba de carga ni una certificación de operación financiera regulada.
