# Portal web por roles

Este módulo permite entrar como CLIENTE, EMPLEADO o ADMINISTRADOR con las mismas cuentas de escritorio. El servidor determina el área y los permisos. La aplicación PySide6 continúa disponible.

## Qué puede hacer el cliente

- Iniciar y cerrar sesión con el correo electrónico registrado por el administrador y su contraseña.
- Consultar su saldo, préstamos, cuotas y fechas de vencimiento.
- Enviar una solicitud de pago con referencia textual y foto obligatoria del comprobante.
- Ver el estado de las solicitudes enviadas.

## Controles incluidos

- Cada consulta se filtra por el identificador de la sesión autenticada.
- Los clientes solo consultan datos propios. El personal activo entra a `/gestion/` para operar clientes, préstamos, cobros y reportes.
- Empleados y cuentas, activación y bajas administrativas requieren rol ADMINISTRADOR. El servidor vuelve a consultar estado y rol en cada solicitud privada.
- Las sesiones usan cookies `HttpOnly`, `SameSite=Lax` y vencen tras cuatro horas.
- Los formularios sensibles incluyen protección CSRF.
- Una solicitud no confirma un pago: permanece en `PENDIENTE_VERIFICACION` hasta que el equipo administrativo la valide.

## Ejecución local

Desde la carpeta principal del proyecto:

```powershell
python -m pip install -r requirements.txt
python portal_web/app_web.py
```

Luego abre `http://127.0.0.1:5000`.

## Publicación responsable

Para que clientes y personal accedan desde Internet hace falta un hosting o servidor con HTTPS, una clave de sesión persistente configurada como `SECRETO_PORTAL_WEB`, y acceso a MySQL mediante una red privada o un servicio administrado. El modo de ejecución incluido está destinado a desarrollo local; no se debe publicar con `debug=True`.

La guía de operaciones, permisos y publicación está en `../docs/guia_acceso_web_personal.md`. Reiniciar el portal para cargar los cambios si ya estaba en ejecución.

## Recuperación de acceso

El login ofrece recuperación asistida por administrador con código temporal de un solo uso. Las cuentas se crean únicamente desde administración. Ver `../docs/recuperacion_asistida.md`.
