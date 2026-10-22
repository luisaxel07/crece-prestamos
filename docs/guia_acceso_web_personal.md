# Acceso web para administración y personal

Actualización del 22/10/2026. La aplicación de escritorio continúa disponible. Ambos canales operan sobre los mismos registros, cuentas y servicios SQLAlchemy; esta mejora no requiere otra base ni recalcular cuotas históricas.

## Entrar

1. Desde la carpeta del proyecto, ejecutar `python portal_web/app_web.py`.
2. Abrir `http://127.0.0.1:5000/acceso` en el mismo equipo.
3. Introducir el usuario y contraseña existentes de escritorio. Los clientes mantienen su acceso habitual. El correo también sirve si identifica una sola cuenta vinculada; si es ambiguo, usar el nombre de usuario.
4. El servidor dirige al cliente a `/inicio` y al personal activo a `/gestion/`.

No hace falta crear otro administrador. Una cuenta de empleado creada desde cualquiera de las aplicaciones funciona en ambas. Solo el administrador puede otorgar o revocar acceso al personal.

## Permisos

| Operación | Cliente | Empleado activo | Administrador |
| --- | --- | --- | --- |
| Consultar datos y avisos propios del cliente | Sí | Área administrativa | Área administrativa |
| Consultar cartera y clientes | No | Sí | Sí |
| Crear/editar clientes y crear acceso de cliente | No | Sí | Sí |
| Emitir préstamos con tasa mensual y editar notas | No | Sí | Sí |
| Registrar cobros y confirmar/rechazar solicitudes | No | Sí | Sí |
| Corregir referencia de pagos | No | Sí | Sí |
| Reportes generales, por cliente y préstamo | No | Sí | Sí |
| PDF, Excel y vista para imprimir | No | Sí | Sí |
| Crear/editar/bajar empleados y cuentas | No | No | Sí |
| Anular préstamos o pagos y dar de baja clientes | No | No | Sí, según reglas del servicio |

Los préstamos emitidos conservan sus condiciones. La baja de registros con historial los desactiva o anula según corresponda. Los préstamos con pagos no se pueden anular. No se borran movimientos para ocultar operaciones.

## Trabajar desde web

- **Resumen:** cartera, cuotas, solicitudes por revisar e índice de mora, con actividad real.
- **Clientes:** buscar, crear, editar, abrir ficha, ver sus préstamos o generar su estado de cuenta. Si aún no tiene cuenta, crear su acceso y entregar las credenciales por un canal privado.
- **Préstamos:** emitir indicando cliente, capital, tasa mensual, plazo y fechas. Después de guardar se abre el detalle con cuotas, intereses y acciones para PDF, Excel e impresión. El simulador calcula una proyección sin emitir.
- **Cobros:** escoger una cuota, verificar el importe recibido y registrar el método y referencia. La sección Pagos y solicitudes permite revisar los avisos enviados por clientes. Enviar un aviso no equivale a confirmar un ingreso.
- **Reportes:** filtrar por cliente, estado y búsqueda. Las descargas reflejan el mismo alcance. Incluyen logotipo oficial, detalle de cuotas y formato corporativo. Vista previa abre el PDF horizontal; desde el visor del navegador se puede imprimir.
- **Empleados y cuentas:** el administrador registra datos del trabajador y sus credenciales, modifica sus datos y activa o desactiva su cuenta. Las cuentas adicionales de administrador se crean desde Cuentas y permisos. No se puede desactivar la propia sesión administrativa ni dejar sin administradores activos al sistema.

Las vistas conservan las fotografías, el selector claro/oscuro y la identidad del portal. El diseño del login se conserva; el campo de acceso ahora admite usuario además de correo.

## Sesiones y comprobación

Las contraseñas se verifican mediante el hash existente. El navegador no decide el rol ni el autor de los movimientos. Cada solicitud privada consulta de nuevo el usuario y su estado en la base de datos. Las operaciones modificadoras requieren CSRF. El actor de los servicios se establece por solicitud y se libera al terminar; las sesiones de distintos usuarios no comparten su identidad.

Las respuestas privadas usan `Cache-Control: no-store`. Las cookies son HttpOnly y SameSite=Lax. Para HTTPS se configura `PORTAL_WEB_HTTPS=1`. Las cuentas de cliente inactivas o bloqueadas tampoco pueden entrar. Una petición durante una interrupción de la base no permite continuar sin verificar el acceso.

Ejecutar `python -m unittest discover -s tests -v`. Las pruebas de roles, operaciones y exportaciones usan MySQL en un esquema temporal exclusivo; no alteran los registros de la base del proyecto.

## Acceso fuera del lugar de trabajo

Esta entrega implementa el área web; no publica el equipo local en Internet. Para acceder desde otra ubicación debe ejecutarse el portal en un servidor accesible con dominio/HTTPS y un servidor WSGI de producción. El servidor web y la aplicación de escritorio deben conectarse a la misma base MySQL por una conexión autorizada; no se debe crear una copia independiente si se espera compartir la operación.

Configurar una variable `SECRETO_PORTAL_WEB` privada, larga y estable en el servidor, y `PORTAL_WEB_HTTPS=1`. Sin una clave estable, reiniciar el portal invalida las sesiones. No publicar contraseñas ni la base MySQL en el navegador. El servidor de desarrollo que se abre con el comando local es para ejecución local, no para alojar el servicio público.

## Resultado de verificación de esta entrega

La revisión actual se ejecuta con `python -m unittest discover -s tests -v`, usando MySQL/InnoDB para la integración real y servicios controlados para pruebas de interfaz. Incluye roles, confirmación única de pagos, comprobantes, validaciones y recuperación asistida. Las comprobaciones previas de diseño en navegador se conservan como evidencia visual histórica, sin atribuirles los resultados de esta nueva ejecución.

## Recuperación y alta de cuentas

El administrador puede emitir un código desde Cuentas y permisos → Recuperar acceso después de verificar la identidad y confirmar su contraseña. La cuenta se recupera desde el login. Ver `recuperacion_asistida.md`. El alta pública se presenta como información para solicitar una cuenta; el expediente y el acceso se habilitan desde administración.
