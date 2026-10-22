# Recuperación asistida de cuentas

Actualizado el 22/10/2026. El mismo servicio ORM funciona en web y PySide6. No se envían correos ni se inicia sesión con el código de recuperación.

## Procedimiento para el administrador

1. Verifica la identidad del titular contra su expediente, de forma presencial o por un canal autorizado. Saber el correo o la cédula no prueba la identidad.
2. Abre **Cuentas y permisos → Recuperar acceso** en web, o **Usuarios → Recuperar acceso** en escritorio, y selecciona la cuenta activa.
3. Escribe una breve constancia de la verificación, confirma la casilla e introduce tu propia contraseña administrativa.
4. Entrega el código mostrado al titular mediante un canal privado. Se muestra una sola vez, caduca a los 15 minutos y un código nuevo invalida cualquier anterior. No lo publiques en capturas de la defensa.

Emitir el código no cambia la contraseña ni bloquea la cuenta. Las cuentas inactivas no pueden recuperarse por esta vía; primero deben seguir el procedimiento administrativo de reactivación.

## Procedimiento para el titular

1. Desde el login, pulsa **¿Olvidaste tu contraseña?** en web o escritorio.
2. Escribe el **usuario de acceso** indicado por el administrador, el código completo y una nueva contraseña de entre 10 y 128 caracteres. Confírmala sin modificar espacios ni mayúsculas.
3. Después del mensaje de éxito, inicia sesión con la contraseña nueva. El código queda consumido y las sesiones anteriores se rechazan en su siguiente operación privada, tanto en web como en escritorio.

Si el código vence o ya fue usado, el administrador deberá emitir uno nuevo. Si todas las cuentas administrativas pierden acceso, este procedimiento requiere otro administrador autorizado: no existe una clave maestra ni una vía pública para eludir la verificación. Mantener al menos dos administradores designados permite atender ese caso sin compartir credenciales.

## Controles implementados y evidencia

- Código aleatorio de 256 bits, almacenado únicamente como SHA-256; la contraseña usa PBKDF2 con sal aleatoria.
- Emisión restringida a administrador activo, nueva comprobación de su contraseña y constancia de identidad verificada. Un administrador no puede emitirse su propio código.
- Código vinculado a una cuenta, vencimiento de 15 minutos calculado con el reloj UTC de MySQL, consumo de una sola vez y bloqueo de fila InnoDB dentro de una transacción. Dos consumos concurrentes producen un único cambio.
- Invalidación de los códigos pendientes al completar una recuperación o cambiar una contraseña desde administración.
- Número de versión de sesión persistido en MySQL para revocar accesos anteriores. No se guardan contraseñas ni códigos en cookies, URL, auditoría, QSettings o almacenamiento del navegador.
- CSRF en formularios web, respuestas privadas sin caché y mensajes genéricos para usuario/código inválido, vencido o utilizado.
- Auditoría de emisión y finalización, con actor y cuenta; sin el código ni las contraseñas.

Código: `crece/servicios/recuperacion.py`, `permisos.py`, `portal_web/seguridad_web.py`, `ui/recovery_dialog.py` y `ui/admin_recovery.py`. Pruebas: `tests/test_recovery.py` y `tests/test_native_recovery.py`.

Referencia técnica: [OWASP Forgot Password Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html). La verificación humana de identidad sigue siendo responsabilidad del administrador; el sistema exige dejar constancia, pero no sustituye ese procedimiento.

## Instalación

Ejecuta `python database/actualizar_orm.py --aplicar` y reinicia escritorio y servidor web. La migración añade `usuarios.version_sesion` y crea `recuperaciones_contrasena` si falta. No recalcula préstamos ni cambia contraseñas existentes. Las sesiones web anteriores a esta actualización deben volver a autenticarse.

El registro público se presenta como **Solicita tu acceso**: las cuentas se crean en administración, vinculadas al expediente. No existe un formulario que aparente registrar sin guardar.
