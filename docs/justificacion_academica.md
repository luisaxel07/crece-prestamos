# Justificación académica: CRECE+ PRÉSTAMOS

Fecha: 22 de octubre de 2026.

Informe de revisión e implementación. Corte: 22 de octubre de 2026. El documento justifica lo que puede localizarse en el código y demostrarse en la aplicación, diferenciando funciones existentes, incorporaciones y límites de la comprobación.

## 1. Resultado de la revisión

Se revisaron los 34 PDF disponibles en la carpeta Sesiones Programacion de Aplicaciones de Escritorio: 393 páginas en total. El material abarca sesiones 2–11 y 13–36. No se recibieron PDF de las sesiones 1 y 12. El archivo identificado como sesión 33 tiene un encabezado interno que dice sesión 32; aquí se identifica por su nombre de archivo y su contenido de refactorización.

| Área | Antes de esta ampliación | Aplicación actual |
| --- | --- | --- |
| Persistencia | Consultas SQL directas en los servicios. | Entidades SQLAlchemy, relaciones, repositorios y transacciones. |
| Reportes | Listado de cartera sin exportación administrativa. | Alcance general, por cliente o préstamo; PDF, Excel e impresión. |
| Personal | Cuentas por rol, sin expediente de empleado. | Perfil de empleado vinculado a credenciales y estado activo. |
| CRUD | Predominaban altas y consultas. | Edición y bajas con validación, permisos y conservación del historial. |
| Interés | Captura anual en emisión y simulador. | Captura mensual nominal y tasa visible por cuota; condiciones históricas intactas. |

El diseño visual previamente aprobado se conserva. La ampliación añade funciones de gestión y sus controles, utilizando los componentes y temas ya existentes.

---

## 2. Interfaz gráfica: sesiones 2–11

Estas bases ya estaban presentes y se reutilizaron en los módulos nuevos. No se añadieron controles sin utilidad operativa solo para completar una lista de temas.

| Sesión / material | Aplicación verificable | Evidencia en el proyecto |
| --- | --- | --- |
| 2 · Estructura GUI | QApplication, QMainWindow, ventanas y navegación de páginas. | crece/interfaz.py: ejecutar_aplicacion y PanelPrincipal. |
| 3 · Controles básicos | Etiquetas, botones y campos de cliente, préstamo y empleado. | ui/workspace.py y ui/employees.py. |
| 4 · Selección | QComboBox para cliente, estado autorizado, método de pago y tema. | PaginaReportes, EmployeesPage.editar y selector de apariencia. |
| 5 · Contenedores | Layouts anidados, QFormLayout, QFrame y QScrollArea. | ui/workspace_shell.py; formularios en crece/interfaz.py. |
| 6 · Eventos | clicked, textChanged, currentIndexChanged y doble clic conectan acciones. | Filtros, formularios y apertura de ficha de préstamo. |
| 7 · Validación | Nombres alfabéticos, cédula nicaragüense con fecha válida, teléfono numérico, correo, importes, plazos y contraseña. | validaciones.py; reglas-formularios.json; validacion_campos.py y validaciones.js. |
| 8 · Organización de comandos | Aplicación parcial: navegación y acciones agrupadas por módulo. No se declara uso de QMenuBar, QToolBar o QStatusBar. | Barra lateral y acciones de los módulos. |
| 9 · Diálogos | Confirmaciones, selección de destino, edición y vista previa. | QMessageBox, QFileDialog, QInputDialog y ReportDialog. |
| 10 · QTableWidget | Tablas de cartera, clientes, empleados y cuotas; selección por ID. | DataTable; Qt.UserRole guarda identificadores. |
| 11 · QSS | Estilos compartidos, temas y estados de los componentes. | styles/workspace*.qss y ui/appearance.py. |

La sesión 8 se cubre conceptualmente de forma parcial. No se afirma que los botones personalizados sean una instancia de las clases nativas de menú o barra de herramientas. Tampoco se necesitan selectores de fuente o color para la operación financiera.

---

## 3. Base relacional y CRUD: sesiones 13–21

| Sesión | Correspondencia con el sistema | Evidencia |
| --- | --- | --- |
| 13 · Arquitectura de datos | Separación entre vistas, servicios y persistencia. | crece/interfaz.py → servicios → infraestructura. |
| 14 · Modelo relacional y DML | Tablas, claves primarias/foráneas, estados e importes. | database/schema.sql y modelos.py. |
| 15 · Consultas SELECT | Búsqueda, filtrado, ordenamiento y alcance por cliente. | Repositorio y PrestamosRepositorio.cartera. |
| 16 · Python y MySQL | Se conserva mysql-connector-python como driver bajo Engine. | base_datos.py: obtener_motor; conexión existente reutilizada. |
| 17 · INSERT | Alta de cliente, empleado/cuenta, préstamo/cuotas y pago. | gestion.py: registrar_cliente, guardar_empleado y registrar_prestamo. |
| 18 · SELECT y tabla | Lectura de entidades y presentación en QTableWidget. | cargar_clientes, cargar_prestamos y cargar_empleados. |
| 19 · UPDATE | Edición de cliente, empleado, credenciales, notas y referencia. | actualizar_cliente, guardar_empleado, actualizar_usuario y resolver_pago. |
| 20 · DELETE | Confirmación y borrado físico cuando no hay dependencias; bajas lógicas en expedientes con historia. | eliminar_cliente, eliminar_empleado, eliminar_usuario y eliminar_prestamo. |
| 21 · Integración CRUD | Las vistas llaman casos de uso y recargan registros tras guardar. | Formularios y acciones administrativas conectados a ORM. |

Se conservan los objetivos de las prácticas SQL, pero las operaciones de negocio se refactorizan a SQLAlchemy conforme a las sesiones posteriores. No se mantienen dos rutas de escritura independientes para la misma entidad.

## CRUD con integridad financiera

Eliminar no significa borrar indiscriminadamente. Un cliente sin préstamos o un empleado sin operaciones puede eliminarse físicamente. Si tiene historia, la baja conserva las relaciones. Un préstamo emitido se anula sin borrar cuotas; si tiene registros de pago, su eliminación se bloquea. Los pagos confirmados se anulan con motivo y reversión de saldo; no se destruye el comprobante histórico.

La actualización de un préstamo emitido se limita a sus observaciones. Cambiar tasa, monto o plazo de un contrato ya emitido requeriría un proceso de reestructuración y autorización específico, que no forma parte de esta entrega.

---

## 4. Énfasis en ORM: sesiones 28–33

| Sesión | Concepto aplicado | Implementación |
| --- | --- | --- |
| 28 · Introducción | Engine y pool; traducción entre objetos y tablas. | base_datos.py: motor reutilizable, pre_ping y manejo de errores. |
| 29 · Modelos | DeclarativeBase, tipos y restricciones. | modelos.py: Usuario, Empleado, Cliente, Prestamo, CuotaModel, Pago, ComprobantePago, RecuperacionContrasena y Auditoria. |
| 30 · Consultas | sessionmaker, select, where, orden y extracción de resultados. | repositorios.py, cuentas_orm.py y portal_orm.py. |
| 31 · CRUD y transacciones | Unit of Work, add/flush/delete y rollback automático. | transaccion(): contexto Session.begin; errores no dejan altas parciales. |
| 32 · Relaciones | ForeignKey, relationship y back_populates. | Cliente → préstamos → cuotas → pagos; Usuario → empleado. |
| 33 · Refactorización | Persistencia desacoplada y carga anticipada de relaciones. | Fachadas públicas preservadas; joinedload/selectinload en la cartera. |

Cada operación usa su propia Session, cerrada al terminar. El Engine es compartido; la Session no se comparte con el hilo de exportación. Un préstamo y todas sus cuotas se registran dentro de una sola transacción, junto con la auditoría. Si falla un dato o una restricción, se revierte la unidad completa.

Numeric y Decimal conservan importes y tasas sin usar float en los cálculos del préstamo. Las exportaciones convierten los valores únicamente para representarlos en celdas Excel. Las claves foráneas mantienen la relación entre expediente, contrato, cuotas y pagos.

El material usa PyMySQL en algunos ejemplos. El proyecto conserva mysql-connector-python, que ya utilizaba, mediante el dialecto mysql+mysqlconnector de SQLAlchemy. Se aplica el mismo patrón ORM sin cambiar innecesariamente el driver ni las credenciales existentes.

La migración es aditiva: crea empleados, comprobantes y recuperación cuando faltan, y añade version_sesion a usuarios. No ejecuta create_all sobre la base existente ni sustituye tablas de cartera. La columna anual histórica sigue almacenando el equivalente nominal de la tasa mensual nueva, por compatibilidad.

---

## 5. Concurrencia y reportes: sesiones 22–27 y 34–36

| Sesión | Aplicación necesaria | Evidencia |
| --- | --- | --- |
| 22 · Bloqueos GUI | El trabajo de exportación se separa del ciclo de eventos. | ReportDialog.guardar y ExportWorker. |
| 23 · QThread | Generación de PDF/Excel en un hilo de trabajo. | ui/export_worker.py: ExportWorker.run. |
| 24 · Ciclo de vida | Inicio, finalización y liberación del hilo. | start, finished, deleteLater y cierre diferido del diálogo. |
| 25 · Señales | Progreso, éxito, error y cancelación viajan por señales. | progreso, completado, fallo y cancelado. |
| 26 · Cancelación | requestInterruption y comprobaciones cooperativas. | guardar_atomico y callbacks de los exportadores. |
| 27 · Integración | La GUI permanece operativa; el archivo solo se publica al terminar. | QProgressDialog y archivo temporal con os.replace. |
| 34 · ReportLab | Documento compuesto por elementos de flujo y tablas. | exportar_pdf: Paragraph, Table y SimpleDocTemplate. |
| 35 · ORM a PDF | Una instantánea relacional alimenta el reporte. | obtener_reporte → exportar_pdf; cabeceras repetidas y paginación. |
| 36 · Excel | Libro editable con datos tipados y formato. | exportar_excel: openpyxl; hojas Resumen, Préstamos y Cuotas. |

Los tres destinos (PDF, Excel e impresión) se basan en la misma instantánea. El usuario puede elegir cartera general, cliente o préstamo y filtrar lo visible antes de exportar. Los totales excluyen borradores y cancelados, y el saldo programado distingue que incluye capital e interés pendientes.

Excel incorpora el logotipo oficial en las tres hojas, bordes de celda y filas alternadas. Conserva números, fechas y porcentajes, con filtros, panel inmovilizado y configuración de impresión. Los textos se escriben como texto para evitar que un nombre o una referencia se interprete como fórmula. El guardado cancelado no reemplaza un archivo previo por uno incompleto.

La cancelación es cooperativa: una operación interna de escritura que ya está en curso puede tardar en devolver el control. Antes de publicar el archivo se vuelve a comprobar la cancelación. La vista previa usa QPdfDocument y QPdfView para mostrar el PDF corporativo A4 horizontal, con navegación, zoom y ajuste al ancho. QPrinter permite elegir impresora, rango y copias; requiere confirmación antes de imprimir.

---

## 6. Reglas de préstamo, empleados y autorización

Decisión aceptada por el responsable del proyecto: tasa mensual para préstamos nuevos y conservación de los préstamos existentes. Se usa tasa mensual nominal; 2 % mensual equivale a 24 % nominal anual. No se está calculando una tasa efectiva anual ni cobrando doce meses en un crédito de tres meses.

| Ejemplo ficticio de tres meses | Resultado calculado |
| --- | --- |
| Principal / tasa / plazo | C$ 10,000.00 / 2 % mensual / 3 meses |
| Primera cuota | C$ 3,467.55 |
| Total de cuotas | C$ 10,402.64 |
| Interés total | C$ 402.64 |
| Saldo de capital final | C$ 0.00 |

Cada fila muestra la tasa mensual nominal constante y el interés monetario calculado sobre el saldo inicial de capital de esa cuota. En el método francés, la tasa permanece igual mientras el importe del interés disminuye al amortizar capital. La última cuota absorbe diferencias de redondeo en centavos.

| Operación | Administrador | Empleado activo |
| --- | --- | --- |
| Clientes, emisión, cobros y reportes | Permitido | Permitido |
| Administración de empleados y cuentas | Permitido | No permitido |
| Bajas protegidas y anulación de pago | Permitido con reglas y motivo | No permitido |
| Cuenta desactivada | Acceso rechazado | Acceso y operaciones rechazados |

Cada empleado tiene un perfil asociado a un Usuario con rol EMPLEADO. La contraseña se guarda con el mecanismo PBKDF2 existente. El estado autorizado se consulta de nuevo en los servicios antes de operar; ocultar un botón no es la única protección. creado_por registra al usuario que emitió realmente el préstamo.

La copia de Brainrot Company disponible sirve como antecedente de CRUD y gestión de préstamos por consola. No contiene el módulo de empleados descrito verbalmente; por tanto, el expediente y la autorización del personal se implementaron para CRECE+, sin atribuir al antecedente funciones que no se encontraron.

---

## 7. Demostración práctica

1. Con un administrador, abrir Empleados y crear un asesor de prueba. Editar sus datos y credenciales. Iniciar sesión con el asesor y mostrar que puede emitir, pero no administrar personal.

2. Crear un cliente ficticio y emitir un crédito usando tasa mensual y un plazo corto. Abrir la ficha ofrecida después de emitir; comprobar cliente, responsable y cada cuota. Guardar PDF/Excel y abrir la vista previa de impresión.

3. En Reportes, elegir al cliente, buscar o filtrar y exportar. Verificar que el alcance coincide con las filas visibles. En Cobros, mostrar el historial, la confirmación de un aviso y la anulación con motivo bajo administración.

4. Desactivar al empleado y comprobar que sus credenciales dejan de permitir acceso u operaciones. Demostrar la diferencia entre borrar un expediente sin movimientos y dar de baja uno con historia. La guía ampliada está en docs/guia_demostracion.md.

5. Demostrar las validaciones al escribir y guardar: nombres alfabéticos, cédula nicaragüense con fecha real y letra final mayúscula, teléfono numérico e importes válidos. Explicar que web y escritorio comparten las reglas y que el servicio vuelve a validar.

6. Habilitar la cuenta de un cliente ficticio y abrir su portal web. Informar un pago con referencia y foto de comprobante; mostrar que queda pendiente. Como empleado, revisar la imagen y confirmar el ingreso una sola vez antes de que cambie el saldo.

7. Recuperar una cuenta ficticia con asistencia del administrador: verificar identidad, confirmar la contraseña administrativa y emitir un código. El titular elige su contraseña desde el login. Comprobar que el código caduca, no se reutiliza y revoca las sesiones anteriores.

---

## 8. Validación y límites de la evidencia

Verificación del 22/10/2026: 94 casos distintos revisados. Tras corregir la conexión MySQL y la carga de la vista previa, se repitieron las suites afectadas: las 12 pruebas de recuperación y las 4 de impresión/Excel finalizaron sin fallos. La integración se ejecuta exclusivamente en MySQL/InnoDB, con datos ficticios en un esquema aleatorio creado para la prueba. Al finalizar se elimina solo ese esquema. No se insertan datos de demostración en la base del proyecto; la interfaz sin persistencia usa servicios controlados.

| Verificación | Resultado / alcance |
| --- | --- |
| Conservación de cuotas | Equivalencia 24 % anual nominal / 2 % mensual; editar observaciones no modifica cuotas persistidas. |
| Credenciales y permisos | Empleado inactivo rechazado; personal sin permiso no administra empleados; protección de la propia cuenta administrativa. |
| CRUD y rollback | Duplicados revierten la operación; bajas conservan vínculos cuando hay historia. |
| Cobros | Sobrepago bloqueado; confirmación única; anulación restaura saldo y conserva el registro. |
| Portal | Solo datos del titular; pago ajeno rechazado; aviso pendiente no disminuye saldo hasta confirmarse. |
| Reportes | Filtro por cliente y por filas visibles; total programado = cobrado + saldo. |
| Archivos y GUI | PDF reabiertos y revisados; Excel con celdas tipadas; QPrinter genera salida paginada; el hilo permite continuar eventos de interfaz. |
| Migración MySQL real | Migraciones aditivas verificadas mediante huellas SHA-256 antes/después de clientes, préstamos, cuotas y pagos. No se alteraron importes ni condiciones históricas. |

Pruebas y evidencias: tests/test_orm_management.py, test_mysql_backend.py, test_staff_web.py, test_validations.py, test_payment_receipts.py, test_print_exports.py, test_recovery.py y test_native_recovery.py; verificaciones de migración en database/. Los ejemplos de salida contienen dos préstamos ficticios con 18 cuotas en total y una ficha individual de 12 cuotas. Se generaron desde el ORM, no desde una imagen del formulario.

Límites: no se imprimió papel ni se ejecutó una prueba de carga de múltiples operadores sobre MySQL. Se verificaron en InnoDB el consumo concurrente de un código y la conservación de registros; esto no equivale a una prueba de carga de la organización. Los reportes son estados operativos de cartera, no un contrato jurídico ni asesoría contable. La recuperación es asistida por administrador; no se envían correos. Una pasarela bancaria no forma parte de esta entrega.

Para una instalación nueva: instalar requirements.txt, crear el esquema base, aplicar la migración de seguridad y ejecutar database/actualizar_orm.py --aplicar. Las migraciones de esta entrega ya están aplicadas en este equipo. Reiniciar escritorio y portal para cargar el código actualizado.

---

## 9. Extensiones actuales y coherencia entre canales

La web es un canal adicional; la aplicación PySide6 sigue siendo el núcleo de la asignatura. Ambos canales usan los mismos servicios ORM, las mismas cuentas y MySQL. El servidor decide el rol y revalida el estado de la cuenta antes de autorizar datos u operaciones.

| Función | Regla y evidencia |
| --- | --- |
| Acceso por rol | Cliente: datos propios. Empleado activo: gestión financiera. Administrador: personal, cuentas y bajas. Evidencia: portal_web/seguridad_web.py y servicios/permisos.py. |
| Validación compartida | Nombres con letras y espacios; cédula 000-000000-0000A con fecha ddmmaa válida, guiones automáticos y letra final mayúscula. Mismas reglas al escribir y guardar en ambos canales. |
| Comprobante de pago | Foto JPG/PNG/WebP de hasta 5 MB y referencia obligatorias. Imagen verificada, normalizada sin EXIF y guardada en MySQL. Solo titular y personal activo autorizado pueden verla. No aplica dinero hasta confirmación. |
| CRUD visible | La acción Eliminar cliente está en ambos listados administrativos. Sin historial se elimina; con préstamos se inactiva. Se preservan cuotas y pagos. |
| Informes de marca | PDF y vista previa A4 horizontal con datos del cliente/préstamo y cuotas. Excel con logo en todas las hojas, bordes, filtros, fechas y valores tipados. |

Estas extensiones se justifican por necesidades del sistema financiero. No se afirma que Flask, la carga de comprobantes o la recuperación asistida aparezcan como temas independientes en las guías docentes: aplican y amplían los principios de validación, eventos, separación de responsabilidades, MySQL y ORM ya estudiados.

---

## 10. Recuperación asistida y prueba de defensa

El administrador verifica la identidad contra el expediente, deja constancia y confirma su propia contraseña. El sistema emite un código aleatorio de 256 bits, válido durante 15 minutos y de un solo uso. Solo guarda su SHA-256; no registra el código ni las contraseñas en la auditoría, URL o cookie.

El titular abre Recuperar acceso desde el login, introduce su usuario y el código, y elige y confirma una nueva contraseña de 10 a 128 caracteres. El administrador no necesita conocerla. Al consumirse el código, una transacción InnoDB invalida los demás códigos y aumenta la versión de sesión. Web y escritorio rechazan sesiones anteriores en su siguiente operación privada; se exige iniciar sesión de nuevo.

Se comprobaron caducidad, código incorrecto, reutilización, cuenta inactiva, confirmación de contraseña, permisos de administrador y consumo concurrente único. La verificación de identidad es un procedimiento humano: conocer correo o cédula no basta. Si un administrador pierde su acceso, debe asistirlo otro administrador autorizado; no hay una contraseña maestra pública.

El registro público se presenta como Solicita tu acceso, con instrucciones para contactar al personal. Las altas de clientes y empleados y el vínculo con sus credenciales se realizan desde administración. No se muestran formularios que simulen guardar ni enviar correos.

Demostración sugerida: mostrar las tablas y una transacción ORM; rechazar un nombre con números y una cédula con fecha imposible; emitir un préstamo mensual de plazo corto; exportar PDF/Excel con marca; enviar foto y referencia desde la cuenta del cliente y validar como empleado; recuperar una cuenta ficticia y comprobar que el código no se reutiliza. El procedimiento detallado está en docs/guia_demostracion.md y docs/recuperacion_asistida.md.

La evidencia corresponde a una aplicación académica funcional. No certifica operación regulada, contabilidad institucional, integración bancaria, alta disponibilidad ni impresión física. La revisión de esta entrega se limita a las funciones solicitadas y la recuperación de cuentas. Git/GitHub se documentará con comandos ejecutados personalmente por el responsable y commits reales por bloques, sin fabricar historial.

---

## 11. Inventario de material revisado y referencias

Fuentes docentes locales: carpeta Sesiones Programacion de Aplicaciones de Escritorio. Se indica el total de páginas revisadas de cada archivo; las matrices anteriores remiten a su sesión. Los contenidos introductorios de cada guía están en su primera página.

| Archivo PDF | Páginas revisadas |
| --- | --- |
| Guia_Practica_Sesion_19_PAE.pdf | 1–7 |
| Guia_Practica_Sesion_20_PAE.pdf | 1–7 |
| Guia_Practica_Sesion_21_PAE.pdf | 1–9 |
| Guia_Practica_Sesion_25_PAE_Dual.pdf | 1–14 |
| Guia_Practica_Sesion_26_PAE.pdf | 1–15 |
| Guia_Practica_Sesion_27_PAE_.pdf | 1–15 |
| Guia_Sesion_22_PAE_Dual.pdf | 1–11 |
| PAE_GuiaEstudio_Sesion28_MySQL.pdf | 1–5 |
| PAE_GuiaEstudio_Sesion29_MySQL.pdf | 1–6 |
| PAE_GuiaEstudio_Sesion30_MySQL.pdf | 1–4 |
| PAE_GuiaEstudio_Sesion31_MySQL.pdf | 1–5 |
| PAE_GuiaEstudio_Sesion32_MySQL.pdf | 1–5 |
| PAE_GuiaEstudio_Sesion33_MySQL.pdf | 1–6 |
| PAE_GuiaEstudio_Sesion34_MySQL.pdf | 1–7 |
| PAE_GuiaEstudio_Sesion35_MySQL.pdf | 1–4 |
| PAE_GuiaEstudio_Sesion36_MySQL.pdf | 1–3 |
| PAE_Tema2.pdf | 1–14 |
| PAE_Tema3.pdf | 1–29 |
| PAE_Tema4.pdf | 1–17 |
| PAE_Tema5.pdf | 1–47 |
| PAE_Tema6.pdf | 1–25 |
| PAE_Tema7.pdf | 1–13 |
| PAE_Tema8.pdf | 1–15 |
| PAE_Tema9.pdf | 1–15 |
| Sesion10_ContenidoTeorico_QTableWidget.pdf | 1–13 |
| Sesion11_ContenidoTeorico_QtStyleSheets.pdf | 1–16 |
| Sesion13_ContenidoTeorico_.pdf | 1–4 |
| Sesion14_ContenidoTeorico_.pdf | 1–4 |
| Sesion15_ContenidoTeorico_.pdf | 1–5 |
| Sesion16_ContenidoTeorico_Python_con_MySQL.pdf | 1–8 |
| Sesion17_ContenidoTeorico_.pdf | 1–7 |
| Sesion18_ContenidoTeorico_.pdf | 1–11 |
| Sesion_23_PAE_Dual_Edilberto_Lacayo.pdf | 1–15 |
| Sesion_24_PAE_Dual_Edilberto_Lacayo.pdf | 1–12 |

Referencia de recuperación: OWASP Forgot Password Cheat Sheet (cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html). Referencias técnicas de apoyo: SQLAlchemy 2.0, Session Basics (docs.sqlalchemy.org/en/20/orm/session_basics.html); Qt for Python, QtPrintSupport (doc.qt.io/qtforpython-6/PySide6/QtPrintSupport/index.html). La evidencia principal es el código y las verificaciones del proyecto.
