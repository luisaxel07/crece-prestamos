# Solicitudes de pago con foto y baja de clientes

## Cliente: informar un pago

En **Cuotas y pagos**, escoger **Informar pago** y completar el importe recibido, la referencia escrita y una foto del voucher o recibo. Las nuevas solicitudes requieren referencia y foto: JPG, PNG o WebP, hasta 5 MB. El formulario muestra una vista previa antes del envío. En escritorio, el portal del cliente también permite seleccionar la foto.

La solicitud queda **En revisión**. Adjuntar una imagen no prueba por sí mismo que el dinero ingresó ni descuenta el saldo. El historial del cliente incluye **Ver comprobante** para consultar su propio adjunto.

## Administrador o empleado: verificar

En web, abrir **Pagos y solicitudes → Revisar**. Se muestra la referencia, el importe, la foto y las opciones para ampliar o descargar la imagen. Comparar el comprobante con el ingreso real en la cuenta y entonces confirmar o rechazar. Confirmar aplica el importe una sola vez; rechazar conserva el saldo y la evidencia.

En escritorio, abrir **Cobros → Historial y solicitudes**, seleccionar el pago y pulsar **Ver comprobante**. El visor permite ajustar al ancho, ampliar, reducir y guardar una copia. Las imágenes se comparten entre ambos canales a través de la misma base.

Las solicitudes anteriores que no tenían foto siguen visibles y muestran **Sin adjunto**. No se inventan comprobantes para esos registros.

## Eliminar un cliente

La acción **Eliminar cliente** está directamente en el listado web para administradores. También se encuentra en la ficha y en la barra de acciones de Clientes del escritorio. Primero se escoge el cliente y se confirma la operación.

- Sin préstamos: se elimina su ficha y se desactiva su cuenta vinculada, si existe.
- Con préstamos o historial de pagos: se conserva la ficha y se inactiva el cliente para mantener los contratos y movimientos.
- Los empleados no pueden ejecutar esta baja administrativa.

Abrir la confirmación no elimina datos. Guardar la baja requiere autorización de administrador y, en web, protección CSRF.

## Almacenamiento y actualización

La tabla ORM `comprobantes_pago` vincula una única imagen a cada pago. El contenido se guarda como binario privado en MySQL; no hay una carpeta pública de recibos. Las consultas de listados leen únicamente la existencia del adjunto; los bytes se recuperan al abrirlo, tras comprobar permisos. Un cliente no puede consultar adjuntos ajenos y el personal debe mantener su cuenta activa.

El servidor verifica el contenido real de la imagen, rechaza archivos corruptos o animados y limita tamaño y resolución. Procesa la orientación y guarda una copia JPEG con solo los píxeles, sin metadatos EXIF/GPS ni archivos adicionales adjuntos al original. La copia conserva su relación con el aviso aun después de ser confirmado o rechazado.

La actualización del equipo se aplica mediante `python database/actualizar_orm.py --aplicar`. Es aditiva y se puede repetir; crea la tabla si falta. La verificación de clientes, préstamos, cuotas y pagos anteriores queda en `database/verificacion_migracion_comprobantes.json`. Para otras instalaciones, ejecutar esa actualización antes de abrir la nueva versión. No ejecutar `schema.sql` sobre bases existentes.

Tras actualizar, reiniciar escritorio y servidor web. Las dependencias incluyen Pillow para comprobar y procesar imágenes.

## Pruebas

`python -m unittest discover -s tests -v`

Las pruebas comprueban carga multipart, archivos inválidos y demasiado grandes, referencia y CSRF obligatorios, lectura por propietario y personal activo, rechazo de acceso ajeno, preservación del saldo hasta la confirmación, rechazo sin perder evidencia y las dos clases de baja del cliente. Usan MySQL en un esquema temporal exclusivo y comprobantes ficticios; no registran pagos reales en la base del proyecto.

Resultado de esta entrega: 78 pruebas correctas. En el navegador se verificó el envío con vista previa móvil, la apertura de la imagen por un empleado, la confirmación del pago y la acción visible de eliminar para administrador, sin errores de JavaScript. Las capturas y comprobantes utilizados fueron ficticios.
