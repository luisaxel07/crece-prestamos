# Temas claro y oscuro · CRECE+ PRÉSTAMOS

La web y PySide6 usan las mismas dos fotografías y la misma identidad: azul #003366, verde #00A651, blanco #FFFFFF, azul noche #001F3F, verde oscuro #006633 y gris #666666. Los verdes suaves son mezclas del verde institucional con blanco. Se conservan Montserrat, Open Sans y los archivos originales del logotipo.

## Cambiar el fondo

- Web: botón de apariencia junto a la cuenta, arriba a la derecha. Su texto indica el tema que se activará; en móvil se muestra el icono con su nombre accesible. Disponible también en login, registro y recuperación. El login conserva su composición exterior y selector; solo su panel central contiene los cuatro elementos de acceso solicitados.
- Desktop: selector «Claro / Oscuro» en la barra superior y dentro de la tarjeta de acceso. También se aplica a registro, recuperación y al portal nativo de clientes.
- Claro: la oficina al mediodía, superficies verde suave y blanco, textos azules.
- Oscuro: la oficina al anochecer, superficies azul noche y detalles verdes.

La preferencia se recuerda en cada entorno: `crece.appearance` en el navegador y `Apariencia/theme` de QSettings en Desktop. Solo se guarda `light` o `dark`. Las ventanas nativas abiertas comparten el cambio; las pestañas web del mismo origen reciben los cambios mediante el evento `storage`. El navegador y Desktop conservan preferencias independientes, sin sincronización por cuenta. Sin preferencia previa se utiliza oscuro.

Alternar no recarga páginas, consulta MySQL ni reinicia formularios, filtros, selección de módulo o resultados del simulador. La autenticación y la revisión de pagos conservan sus comprobaciones del servidor.

## Ejecutar y actualizar

Desde la carpeta `CRECE Prestamos`:

```powershell
python main.py
```

Para web:

```powershell
python portal_web/app_web.py
```

Reabrir Desktop después de actualizar los archivos. En web, reiniciar el servidor y usar Ctrl+F5. Las páginas estáticas de `portal_web/static/auth/` también se pueden abrir con Live Server, conservando las carpetas hermanas `images` y el archivo `appearance.js`.

## Archivos principales

- `ui/appearance.py`: preferencia, selectores y aplicación de estilos nativos.
- `styles/appearance-light.qss`, `styles/appearance-dark.qss`: superficies, textos y controles.
- `ui/widgets/premium.py`: fotografía nativa, capas y tarjeta de acceso.
- `portal_web/static/appearance.js`: cambio y almacenamiento del tema web.
- `portal_web/static/portal-claro.css`, `portal-nocturno.css`: variantes del portal.
- `portal_web/static/auth/appearance.css`: variantes de las tres páginas de acceso.

Los fondos se comparten entre web y Desktop desde:

- `portal_web/static/images/fondo_portal_mediodia.png`
- `portal_web/static/images/fondo_portal_premium.png`

Se aplica el equivalente de `cover` con recorte centrado. Los textos permanecen en componentes reales; la fotografía no contiene interfaces ni marcas. En fondos oscuros se usa la versión blanca original del logotipo horizontal; el logotipo vertical del acceso tiene una superficie clara que permite conservar sus colores originales.

## Imagen de mediodía

Edición realizada con la herramienta integrada de generación de imágenes y la habilidad `imagegen`, usando el fondo nocturno existente como objetivo de edición. El resultado se copió al proyecto; el fondo nocturno se conserva.

Prompt utilizado:

> Use case: lighting-weather. Edit target: the supplied premium financial office photograph. Create its matching LIGHT THEME background by changing ONLY lighting, time of day and atmospheric color to clear NOON around 12:00. Preserve camera, perspective, exact composition, desk, laptop at left, notebook and pen, coin stacks and wooden house at right, plant, window frames, skyline and mountains. Neutral natural white daylight from high sun, soft short shadows, fresh green leaves, natural walnut wood, pale blue sky, visible city architecture. Calm premium financial atmosphere, realistic material textures. No morning mist, no sunrise or sunset orange, no evening blue cast, no night lights. Keep broad calm center suitable behind interface cards. Landscape same aspect ratio, photographic quality. No text, no logos, no UI, no watermark.

## Verificación

21 pruebas automatizadas: autenticación, CSRF, autorización por cliente, datos y cálculos, estabilidad de renderizado, botones de ventana, persistencia del tema y conservación de estado. Las pruebas de preferencias utilizan un archivo aislado y restauran la apariencia previa.

Revisión del portal con navegador real: las tres vistas en ambos temas y cuatro anchos (1440, 1024, 390 y 320 px), filtros, navegación, formulario, validación y cambio de tema con formulario abierto. Revisión de los accesos web en móvil y del login nativo en 1440 y 390 px. Datos ficticios, sin acceso a MySQL ni solicitudes reales de pago.

Capturas de revisión: `../tmp/portal_temas/` y `../tmp/desktop_temas/`.
