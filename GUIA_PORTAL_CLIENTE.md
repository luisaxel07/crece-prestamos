# Portal del cliente · Diseño institucional fotográfico

Inicio, Mis préstamos y Cuotas y pagos usan una fotografía de oficina al atardecer, azul noche y verde institucional. Las tarjetas translúcidas mantienen un relieve discreto y bordes visibles. El logotipo oficial para fondo oscuro se muestra sin sombras, rotación ni efectos.

Preferencia visual del proyecto: evitar grandes superficies blancas; dar protagonismo a la paleta corporativa y a fondos fotográficos financieros, siguiendo la dirección del login.

## Cambios

- Marca horizontal oficial, Montserrat y Open Sans, navegación activa y barra inferior para móvil.
- Fondo financiero generado específicamente para el portal, con superposición azul noche, superficies de cristal azul y bloques verdes para saldo y próxima cuota.
- Saludo breve, títulos contenidos y tarjetas uniformes. El relieve combina sombras suaves y luces discretas, sin animaciones constantes.
- Próxima cuota destacada con importe, fecha y enlace a su préstamo; ayuda para informar pagos ya realizados.
- Préstamos con datos agrupados, porcentajes a dos decimales y acceso directo a su plan.
- Cuotas ordenadas por vencimiento ascendente. Con JavaScript, se muestran inicialmente las pendientes, salvo que el plan elegido solo tenga cuotas pagadas. Todas las cuotas siguen disponibles mediante el filtro.
- Filtros por préstamo y por estado, contador accesible y selección visual de una cuota enlazada desde Inicio.
- En móvil, las tablas se presentan como registros verticales y los controles tienen áreas de interacción cómodas.
- Acciones «Informar pago» y un formulario que explica la revisión posterior. Se mantienen el token CSRF, los límites de importe y el servicio existente de solicitud de pago.

El portal no cobra ni confirma un pago al enviar el formulario. El servidor registra el aviso con `PENDIENTE_VERIFICACION` y el equipo debe validarlo. Las consultas continúan limitadas al usuario autenticado; los filtros del navegador solo ocultan o muestran filas que el servidor ya autorizó.

## Archivos

- `portal_web/templates/base.html`: navegación, marca y estructura.
- `portal_web/templates/partials/ui.html`: iconos SVG y estados compartidos.
- `portal_web/templates/inicio.html`, `prestamos.html`, `cuotas.html`: las tres vistas.
- `portal_web/static/portal.css`: estilos limpios, responsive y neumorfismo sutil.
- `portal_web/static/portal-nocturno.css`: apariencia fotográfica azul y verde, también para el formulario y la navegación móvil.
- `portal_web/static/portal.js`: filtros y formulario de aviso.
- `portal_web/app_web.py`: recurso horizontal original, formato de porcentaje y orden del calendario.

El login conserva su composición y comparte el selector claro/oscuro con el portal. Consultar `GUIA_TEMAS.md` para los dos fondos, preferencias y archivos actuales.

## Ejecutar

Desde `CRECE Prestamos`:

```powershell
python portal_web/app_web.py
```

Abrir `http://127.0.0.1:5000`. Si el servidor está abierto, reiniciarlo y recargar el navegador con Ctrl+F5 para renovar los estilos.

## Verificación

Pruebas automatizadas: `python -m unittest discover -s tests -v`. Se comprobaron los tres diseños en anchos de 1440, 1024, 390 y 320 px; navegación activa, ausencia de desbordamiento horizontal, filtros, enlace a un plan, apertura/cierre del formulario, devolución del foco, límite de importe y envío de los campos con CSRF.

Las capturas en `../tmp/portal_minimal/` usan datos ficticios de una cuenta `vista.de.prueba@example.test`. No se enviaron avisos reales ni se modificó MySQL durante las pruebas.

Las vistas finales con fotografía están en `../tmp/portal_fotografico/`. Las vistas anteriores se conservan para comparación. Se verificaron las tres páginas en cuatro anchos, los filtros, la validación del monto, el foco del formulario y los campos enviados con CSRF.

## Fotografía generada

Recurso utilizado: `portal_web/static/images/fondo_portal_premium.png`. Se creó con la herramienta integrada de generación de imágenes y se copió al proyecto. Es una fotografía independiente, sin textos, logotipos ni interfaz incrustada. El PNG original permanece en la biblioteca de imágenes generadas.

Prompt utilizado:

> Use case: photorealistic-natural. Asset type: full-screen photographic background for CRECE+ PRÉSTAMOS client financial portal, no interface. Generate a refined ultra-wide cinematic photograph, landscape 1536 x 1024 or wider 16:9. A high-end financial advisory office at blue hour: panoramic glass windows with defocused city lights, rich walnut desk in the lower foreground, cropped premium laptop far left, dark notebook and fountain pen lower left, modest neatly stacked coins and a small wooden house at the far right beside an elegant green plant. Central two thirds have calm dark blue architectural negative space, office details concentrated near frame edges and lower third, so actual dashboard cards can be overlaid separately. Deep navy #001F3F and corporate blue #003366 in the architecture and shadows, subtle natural institutional green #006633 accents from plants, warm restrained amber desk highlights. Real material texture, beautiful expensive architectural editorial photography, sophisticated atmospheric light and depth. No people, NO text, NO logo, NO watermark, NO charts, NO UI, NO cards or buttons. Do not paint an application screenshot. Background photo only.
