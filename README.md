# CRECE + PRÉSTAMOS

Evolución de Brainrot Company hacia una aplicación de escritorio para administrar clientes, préstamos, cuotas y cobros. La interfaz usa PySide6 y la base de datos está diseñada para MySQL 8+.

## Funciones actuales

- Método francés implementado con `Decimal`: cuota fija, redondeo monetario y saldo final exacto.
- Esquema relacional: usuarios por rol, clientes, préstamos, cuotas, pagos y auditoría.
- Persistencia con SQLAlchemy ORM, relaciones, repositorios y transacciones con rollback.
- CRUD de clientes, empleados y cuentas; préstamos con edición de observaciones y anulación que conserva historial.
- Empleados con credenciales propias y autorización vigente antes de cada operación.
- Tasa mensual nominal en préstamos nuevos y simulador; contratos y cuotas existentes conservados.
- Reportes generales, por cliente y por préstamo; PDF, Excel y vista previa de impresión con todas las cuotas.
- Cobros, revisión de avisos de pago, corrección de referencias y anulación administrativa con motivo.
- Temas claro y oscuro, identidad corporativa y contraseñas con PBKDF2.

## Puesta en marcha

1. Solo para una instalación nueva, crea la base ejecutando `database/schema.sql` en MySQL Workbench. No lo ejecutes sobre una base ya poblada.
2. En una instalación nueva, copia `conexion.example.py` como `conexion.py` y configura las variables de entorno `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_HOST` y `MYSQL_DATABASE` del equipo. En la instalación existente conserva tu conexión local. `conexion.py` queda excluido de Git.
3. Instala dependencias: `python -m pip install -r requirements.txt`.
4. Si aún no está aplicada la migración de seguridad, ejecuta `python database/aplicar_migracion_seguridad.py`.
5. Ejecuta `python database/actualizar_orm.py --aplicar`. Crea las tablas de empleados, comprobantes y recuperación que falten, y añade la versión de sesión; no recalcula préstamos ni cuotas.
6. Ejecuta `python app.py` (o `python main.py`).

Las migraciones son aditivas. Las verificaciones de conservación de datos están en `database/verificacion_migracion_orm.json`, `database/verificacion_migracion_comprobantes.json` y `database/verificacion_migracion_recuperacion.json`.

## Uso administrativo

- **Empleados:** añadir, editar perfil o credenciales y activar/desactivar. La baja conserva al empleado si tiene operaciones. El empleado accede al mismo escritorio con su propio usuario, sin administrar empleados ni usuarios.
- **Clientes:** seleccionar fila y usar editar, eliminar/inactivar o estado de cuenta.
- **Préstamos:** emitir indicando tasa mensual; al terminar se ofrece abrir la ficha. También se abre con doble clic. Contiene PDF, Excel e impresión. Las condiciones financieras emitidas se conservan; se editan observaciones. Un préstamo con movimientos no se elimina físicamente.
- **Reportes:** escoger reporte general o un cliente y aplicar búsqueda/estado; PDF / Excel / imprimir exporta ese mismo alcance visible.
- **Cobros:** registrar un cobro o abrir historial y solicitudes para confirmar, rechazar, corregir referencia o anular un pago confirmado con motivo (solo administrador).

El saldo programado incluye capital e interés pendientes. La tasa mensual es nominal: 2 % mensual equivale a 24 % nominal anual, sin cambiar las cuotas históricas. Las cuotas muestran tanto la tasa como el interés monetario correspondiente.

La vista previa de impresión muestra el mismo PDF corporativo, en A4 horizontal. Incluye navegación por página, ajuste al ancho y zoom; el botón Imprimir permite escoger impresora, rango y copias. No se envía nada hasta confirmar. Excel incorpora el logo en las tres hojas, bordes de celdas, filas alternadas y encabezados inmovilizados. Los archivos exportados anteriormente deben volver a generarse para obtener el formato nuevo.

## Comprobación y documentación académica

Ejecuta `python -m unittest discover -s tests -v`. Las pruebas de integración usan exclusivamente MySQL en un esquema temporal `crece_pruebas_<identificador aleatorio>`. Crean sus propios datos ficticios y eliminan únicamente ese esquema al terminar. La cuenta de pruebas necesita permisos CREATE/DROP DATABASE; nunca se limpian las tablas del proyecto. Las pruebas de interfaz sin persistencia utilizan servicios controlados.

La justificación de las sesiones está en `docs/justificacion_academica.md`; la guía de demostración está en `docs/guia_demostracion.md`. La copia PDF y los ejemplos ficticios se encuentran en `../output/`.

## Portal web por roles

La misma entrada web admite clientes, empleados y administradores, en computadora, tablet y móvil. El servidor verifica las credenciales, consulta el rol y estado actual, y abre el área autorizada. Web y escritorio usan las mismas cuentas, servicios ORM y base de datos. Cada cliente sigue limitado a sus propios datos.

- **Cliente:** Inicio, Mis préstamos y Cuotas y pagos.
- **Empleado activo:** Resumen, clientes, préstamos, cobros, revisión de solicitudes, simulador y reportes PDF/Excel/impresión.
- **Administrador:** todo lo anterior, empleados, cuentas, activación/desactivación y bajas administrativas.

Entra con el usuario y contraseña que ya utilizas en escritorio. También se admite el correo de cliente o empleado si identifica una sola cuenta. No se escoge el rol en el navegador. Los permisos se verifican en cada solicitud; desactivar una cuenta bloquea su siguiente acceso privado. Reinicia el servidor si estaba abierto al aplicar esta actualización. La guía completa está en `docs/guia_acceso_web_personal.md`.

1. Instala las dependencias actualizadas: `python -m pip install -r requirements.txt`.
2. Comprueba que MySQL está activo y que `conexion.py` tiene la contraseña correcta.
3. Ejecuta `python portal_web/app_web.py` desde esta carpeta.
4. En el navegador del mismo equipo, abre `http://127.0.0.1:5000`.

Para publicarlo en Internet se debe configurar un dominio, HTTPS, una variable `SECRETO_PORTAL_WEB` en el servidor y una conexión segura a MySQL. No es recomendable exponer directamente una base de datos local de Workbench a Internet.

## Nota sobre pagos de cliente

Un cobro digital real requiere escoger una pasarela o banco y sus credenciales. El sistema ya modela el estado `PENDIENTE_VERIFICACION` para no marcar un pago como recibido antes de validarlo.

## Validaciones de datos

Web y escritorio restringen nombres/apellidos a letras y espacios (con tildes y ñ), cédula nicaragüense con fecha válida y letra final mayúscula, teléfonos numéricos y correos válidos. Los guiones de la cédula se insertan al escribir; la validación también se ejecuta en los servicios al guardar. Los ejemplos y mensajes se detallan en `docs/validaciones_datos.md`.

## Comprobantes de pago y eliminación de clientes

Las solicitudes nuevas de cliente incluyen referencia escrita y una foto JPG, PNG o WebP (hasta 5 MB). El personal consulta la imagen desde Pagos y solicitudes en web o Historial y solicitudes en escritorio antes de confirmar el ingreso. La carga no aplica dinero automáticamente. La acción Eliminar cliente está directamente en el listado web del administrador y en Clientes de escritorio; con historial se inactiva para conservar los movimientos.

La tabla `comprobantes_pago` se crea con `python database/actualizar_orm.py --aplicar`. Reiniciar ambos canales después de actualizar. Ver `docs/comprobantes_y_baja_clientes.md`.

## Recuperación de cuentas

Un administrador activo verifica la identidad del titular, confirma su propia contraseña y emite un código temporal desde Cuentas y permisos/Usuarios → Recuperar acceso. El titular lo utiliza en ¿Olvidaste tu contraseña? para elegir una contraseña nueva. Dura 15 minutos, funciona una sola vez y al utilizarse se revocan las sesiones anteriores. No se envían correos ni se permite el registro público: las cuentas se habilitan desde administración. Procedimiento completo: `docs/recuperacion_asistida.md`.

La demostración y justificación académica están actualizadas al 22/10/2026. El control de versiones y la publicación en GitHub se realizarán manualmente por el responsable del proyecto, con commits reales por bloques; no forman parte de las migraciones ni de las pruebas.
