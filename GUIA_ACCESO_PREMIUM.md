# Acceso CRECE+ PRÉSTAMOS: web y escritorio

Actualizado el 22/10/2026. Se conserva el diseño aprobado, la fotografía, los logotipos oficiales y los temas claro/oscuro. El login ofrece enlaces discretos para recuperar acceso o solicitar una cuenta.

## Ejecución

Instala `requirements.txt`, configura la conexión local a MySQL y aplica las migraciones indicadas en `README.md`. Ejecuta `python app.py` para escritorio o `python portal_web/app_web.py` para el portal y abre `http://127.0.0.1:5000`.

Web admite cliente, empleado activo y administrador; determina el rol en el servidor. El escritorio administrativo admite empleados activos y administradores. El cliente web solo consulta su expediente. Ambos canales usan SQLAlchemy y MySQL; no hay un segundo almacén de usuarios.

## Altas y recuperación

**Solicita tu acceso** explica el procedimiento: el personal verifica el expediente y crea la cuenta vinculada. Los empleados se registran desde administración. No hay alta pública automática.

**¿Olvidaste tu contraseña?** abre el formulario de usuario, código temporal, contraseña nueva y confirmación. El código debe emitirlo un administrador tras verificar la identidad y confirmar su propia contraseña. Caduca a los 15 minutos, solo se utiliza una vez y revoca las sesiones anteriores al completarse. No se envían correos ni se inicia sesión automáticamente. Ver `docs/recuperacion_asistida.md`.

## API de autenticación

Todos los POST requieren CSRF. Las plantillas reciben la configuración serializada por Flask; Fetch envía las cookies al mismo origen.

| Método | Ruta | Datos y respuesta |
| --- | --- | --- |
| POST | `/api/auth/login` | `{username,password,remember}` → sesión validada y destino según rol |
| GET | `/api/auth/session` | Revalida cuenta y versión de sesión; devuelve estado, CSRF y destino |
| POST | `/api/auth/logout` | Cierra la sesión actual |
| POST | `/api/auth/register` | HTTP 409: alta controlada desde administración, sin afirmar éxito |
| POST | `/api/auth/recover` | `{username,code,password,confirm}` → cambio confirmado, sin sesión automática |

La recuperación responde HTTP 400 ante datos/código inválidos y 503 ante indisponibilidad de MySQL. Las respuestas sensibles no se guardan en caché. El código y las contraseñas no se incluyen en URL, cookie, auditoría, localStorage o QSettings. Las sesiones web utilizan HttpOnly/SameSite; la publicación requiere HTTPS y una clave de servidor persistente.

## Organización

- `ui/login_window.py`, `register_window.py`, `recovery_dialog.py`, `admin_recovery.py`: acceso nativo y recuperación.
- `services/auth_service.py`: adaptador de acceso a los servicios ORM.
- `crece/servicios/cuentas_orm.py`, `recuperacion.py`, `permisos.py`: cuentas, códigos y autorización.
- `portal_web/app_web.py`, `seguridad_web.py`, `personal.py`: rutas y permisos de servidor.
- `portal_web/templates/` y `static/auth/`: páginas integradas y vistas autónomas.
- `styles/login.qss`, `static/auth/login.css` y `appearance.css`: composición y temas existentes.

Live Server permite revisar `static/auth/index.html`, `registro.html` y `recuperar.html`. Para operaciones reales se usa Flask o se configura una API compatible en `config.js`; sin conexión no se simulan envíos ni accesos.

## Comprobación

Ejecuta `python -m unittest discover -s tests -v`. La integración usa MySQL/InnoDB en un esquema temporal; las pruebas visuales sin persistencia usan servicios controlados. Incluye permisos, CSRF, estados de cuenta, versión de sesión, recuperación concurrente de un solo uso y validación de los diálogos PySide6. La documentación de defensa está en `docs/justificacion_academica.md`.
