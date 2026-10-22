# Espacio administrativo CRECE+ PRÉSTAMOS

Se rediseñaron Resumen, Clientes, Préstamos, Cobros, Simulador, Reportes y Usuarios en Qt Widgets. La navegación lateral azul noche, el verde institucional, los logotipos originales y las fuentes Montserrat/Open Sans conectan visualmente la aplicación con el login. Las áreas de trabajo priorizan lectura de datos y acciones claras.

## Cambios

- Barra lateral con iconos SVG, selección visible y cierre de sesión; encabezado con ubicación, usuario y rol reales. Usuarios se muestra en la navegación solo para administradores.
- Superficies blancas con bordes discretos y radios consistentes. Se mantienen eliminados los efectos anidados que ocultaban contenido.
- Resumen con cuatro indicadores existentes, movimientos con fecha, proporción de mora calculada y accesos a Clientes y Simulador. Se retiró la gráfica de barras con valores decorativos.
- Listas con búsqueda inmediata que ignora mayúsculas y tildes, filtro de estado, limpieza, contador de coincidencias y altura acorde con los registros y la ventana.
- Indicadores derivados de las filas cargadas: registros, activos/con correo en Clientes, activos/inactivos en Usuarios, monto total en Préstamos y saldo total en Cobros/Reportes. Los indicadores representan todos los registros cargados; el contador inferior representa los visibles tras filtrar.
- Tablas de lectura con filas alternas, selección por fila, importes alineados a la derecha, estados/roles diferenciados y texto completo en tooltip cuando se recorta visualmente. Las acciones conservan los controladores existentes.
- Mensajes de ausencia de registros solo cuando no hay filas, y mensajes distintos cuando una búsqueda no encuentra coincidencias.
- Simulador con formulario compacto, cuota/interés/total calculados y calendario. Si cambian los parámetros, se avisa que el plan requiere recalcularse.
- Desplazamiento vertical en Resumen y Simulador cuando la altura disponible lo requiere.

## Archivos

`styles/workspace.qss` centraliza la presentación. `ui/workspace.py` contiene superficies, métricas, tablas y renderizado de estados; `ui/workspace_shell.py`, la navegación y el encabezado; `ui/workspace_dashboard.py`, el resumen; `ui/workspace_simulator.py`, la presentación del cálculo. `crece/interfaz.py` conecta estas vistas con los servicios existentes.

Se preservan los servicios de MySQL, el motor de amortización con Decimal y las operaciones de registro y cobro. No se agregó información de demostración a la aplicación ni se escribieron datos en MySQL durante la revisión.

## Ejecutar y comprobar

Cerrar la aplicación abierta y, desde `CRECE Prestamos`, ejecutar:

```powershell
python main.py
```

`python app.py` sigue siendo compatible. Con las dependencias del proyecto instaladas:

```powershell
python -m unittest discover -s tests -v
```

Las pruebas de diseño inicial verificaron autenticación, CSRF, estabilidad al mover el cursor, controles de ventana, filtros y totales con servicios controlados. La suite actual añade integración real en un esquema MySQL temporal; consulta docs/justificacion_academica.md para el alcance vigente.

Se revisaron visualmente las siete pantallas con datos ficticios y tamaños 1536×1000, 1280×800 y 1120×690. Las capturas están en `../tmp/revision_premium/` y muestran la identidad «Datos de prueba». El código que las genera está en `../tmp/preview_workspace_premium.py`.
