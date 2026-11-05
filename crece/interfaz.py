"""Interfaz de escritorio de CRECE + PRÉSTAMOS."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPoint, QPropertyAnimation, QTimer, Qt
from PySide6.QtGui import QColor, QFont, QPixmap
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QComboBox, QDateEdit, QDialog, QFormLayout, QFrame,
    QGraphicsDropShadowEffect, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow, QFileDialog,
    QMessageBox, QPushButton, QGraphicsOpacityEffect, QSizePolicy, QStackedWidget, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget, QScrollArea, QInputDialog,
)

from ui.login_window import LoginWindow as DialogoAcceso
from ui.workspace import DataTable, Metric, label as workspace_label, button as workspace_button, surface as workspace_surface, normalized, workspace_styles
from ui.workspace_dashboard import Dashboard
from ui.workspace_simulator import PremiumSimulator
from ui.workspace_shell import sidebar as workspace_sidebar, header as workspace_header
from ui.widgets.premium import symbol, load_fonts

from crece.nucleo.amortizacion import calcular_tabla_francesa, calcular_tabla_mensual, calcular_tabla_credito, tasa_por_periodo, FRECUENCIAS, TASAS_TIPO_CREDITO, TIPOS_CREDITO
from crece.servicios.permisos import establecer_actor, restablecer_actor
from crece.servicios.gestion import obtener_cliente, actualizar_cliente, eliminar_cliente, actualizar_prestamo, eliminar_prestamo
from crece.servicios.cuentas_orm import actualizar_usuario, eliminar_usuario
from crece.servicios.reportes import obtener_reporte
from ui.report_dialog import ReportDialog
from ui.validacion_campos import configurar_campo, configurar_numero, enfocar_error, leer_numero, leer_plazo
from crece.servicios.clientes import ErrorConexionBaseDatos, listar_clientes, registrar_cliente
from crece.servicios.prestamos import listar_clientes_para_prestamo, listar_prestamos, registrar_prestamo_mensual, registrar_prestamo_periodico
from crece.servicios.operaciones import listar_cuotas_cobro, obtener_actividad_reciente, obtener_reporte_cartera, obtener_resumen, registrar_cobro
from crece.servicios.autenticacion import actualizar_correo_cliente_portal, cambiar_estado_usuario, configurar_administrador, crear_cuenta_cliente, crear_usuario_personal, hay_administrador_configurado, iniciar_sesion, listar_usuarios, obtener_cliente_para_cuenta
from crece.servicios.portal_cliente import listar_cuotas_cliente, obtener_resumen_cliente, solicitar_pago

AZUL_MARINO = "#003366"
AZUL_NOCHE = "#001F3F"
VERDE_ESMERALDA = "#00A651"
VERDE_OSCURO = "#006633"
GRIS_NEUTRO = "#666666"
FONDO = "#E9EEF0"
RUTA_ACTIVOS = Path(__file__).resolve().parents[1] / "assets"
RUTA_LOGO_VERTICAL = RUTA_ACTIVOS / "logo_crece.png"
RUTA_LOGO_HORIZONTAL = RUTA_ACTIVOS / "logo_horizontal_crece.png"
RUTA_FONDO_ACCESO = Path(__file__).resolve().parents[1] / "portal_web" / "static" / "images" / "fondo_acceso_botanico.png"

ESTILO_APLICACION = f"""
QMainWindow, QScrollArea, QFileDialog, QWidget {{ font-family: "Open Sans", "Segoe UI"; color: {AZUL_MARINO}; }}
QLabel {{ background: transparent; }}
QMainWindow {{ background: qradialgradient(cx:0.18, cy:0.06, radius:1.2, stop:0 #FFFFFF, stop:0.56 #EEF4F4, stop:1 #DFE8EA); }}
QFrame#contenedorPrincipal {{ background: rgba(255, 255, 255, 168); border: 1px solid rgba(255, 255, 255, 225); border-radius: 34px; }}
QFrame#barraLateral {{ background: rgba(255, 255, 255, 210); border: 1px solid rgba(255, 255, 255, 240); border-radius: 30px; }}
QFrame#barraSuperior {{ background: rgba(255, 255, 255, 224); border: 1px solid rgba(255, 255, 255, 245); border-radius: 22px; }}
QLineEdit, QDateEdit, QComboBox {{ background: rgba(255, 255, 255, 210); border: 1px solid #D9E5E6; border-radius: 15px; padding: 11px 14px; min-height: 20px; }}
QLineEdit:focus, QDateEdit:focus, QComboBox:focus {{ background: #FFFFFF; border: 2px solid {VERDE_ESMERALDA}; }}
QPushButton {{ border: 0; border-radius: 15px; padding: 11px 18px; font-weight: 700; background: {VERDE_ESMERALDA}; color: white; }}
QPushButton:hover {{ background: {VERDE_OSCURO}; }}
QTableWidget {{ background: rgba(255, 255, 255, 220); border: 1px solid rgba(255, 255, 255, 245); border-radius: 22px; gridline-color: #EDF2F6; selection-background-color: #DFF4E7; selection-color: {AZUL_MARINO}; padding: 8px; }}
QHeaderView::section {{ background: #EDF5F4; color: #5A7280; padding: 13px; border: 0; font-weight: 700; }}
QTableCornerButton::section {{ background: #EDF5F4; border: 0; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 8px; }}
QScrollBar::handle:vertical {{ background: #B7C9D0; border-radius: 4px; min-height: 30px; }}
QDialog {{ background: {FONDO}; }}
QDialog QLabel {{ background: transparent; color: {AZUL_MARINO}; }}
QComboBox {{ background: rgba(255,255,255,220); border: 0; border-radius: 14px; padding: 11px 14px; min-height: 20px; }}
QComboBox QAbstractItemView {{ background: #FFFFFF; color: {AZUL_MARINO}; selection-background-color: #E4F5EC; }}
"""


def etiqueta(texto: str, estilo: str = "") -> QLabel:
    control = QLabel(texto)
    control.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
    control.setStyleSheet(estilo)
    return control


def boton_secundario(texto: str) -> QPushButton:
    boton = QPushButton(texto)
    boton.setStyleSheet(f"background: rgba(255,255,255,210); color: {AZUL_MARINO}; border: 1px solid #D6E5E5;")
    return boton


def aplicar_sombra(control: QWidget, desenfoque: int = 28, desplazamiento_y: int = 8) -> None:
    sombra = QGraphicsDropShadowEffect(control)
    sombra.setBlurRadius(desenfoque)
    sombra.setOffset(0, desplazamiento_y)
    sombra.setColor(QColor(0, 51, 102, 50))
    control.setGraphicsEffect(sombra)


class AnimadorInterfaz(QObject):
    """Microinteracciones sutiles compartidas por toda la aplicación."""

    def __init__(self) -> None:
        super().__init__()
        self.animaciones: dict[tuple[int, bytes], QPropertyAnimation] = {}

    def _animar(self, objeto: QObject, propiedad: bytes, destino: object, duracion: int = 170) -> None:
        clave = (id(objeto), propiedad)
        if animacion_anterior := self.animaciones.get(clave):
            animacion_anterior.stop()
        animacion = QPropertyAnimation(objeto, propiedad, self)
        animacion.setDuration(duracion)
        animacion.setStartValue(objeto.property(propiedad.decode()))
        animacion.setEndValue(destino)
        animacion.setEasingCurve(QEasingCurve.OutCubic)
        self.animaciones[clave] = animacion
        animacion.finished.connect(lambda: self.animaciones.pop(clave, None))
        animacion.start()

    def _sombra_para(self, control: QWidget, color: QColor) -> QGraphicsDropShadowEffect:
        efecto = control.graphicsEffect()
        if not isinstance(efecto, QGraphicsDropShadowEffect):
            efecto = QGraphicsDropShadowEffect(control)
            efecto.setOffset(0, 5)
            efecto.setBlurRadius(8)
            control.setGraphicsEffect(efecto)
        efecto.setColor(color)
        return efecto

    def eventFilter(self, objeto: QObject, evento: QEvent) -> bool:
        # Hover and focus are painted by QSS. Attaching graphics effects here
        # nests them inside panel shadows and can erase the entire page in Qt.
        return False


def animar_flotacion(control: QWidget, altura: int = 5) -> None:
    """Da al logo un movimiento ambiental ligero sin modificar su identidad."""
    posicion = control.pos()
    animacion = QPropertyAnimation(control, b"pos", control)
    animacion.setDuration(3300)
    animacion.setStartValue(posicion)
    animacion.setKeyValueAt(0.5, QPoint(posicion.x(), posicion.y() - altura))
    animacion.setEndValue(posicion)
    animacion.setEasingCurve(QEasingCurve.InOutSine)
    animacion.setLoopCount(-1)
    control.animacion_flotacion = animacion
    animacion.start()


def cargar_logo_transparente(ruta: Path, ancho: int = 150, alto: int = 150) -> QPixmap:
    """Carga el activo oficial conservando su transparencia y proporciones."""
    return QPixmap(str(ruta)).scaled(ancho, alto, Qt.KeepAspectRatio, Qt.SmoothTransformation)


class TarjetaMetrica(QFrame):
    def __init__(self, titulo: str, valor: str, descripcion: str, color: str = VERDE_ESMERALDA) -> None:
        super().__init__()
        self.setObjectName("tarjetaMetrica")
        self.setStyleSheet("QFrame#tarjetaMetrica { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 rgba(255,255,255,245), stop:1 rgba(238,247,246,218)); border: 1px solid rgba(255,255,255,245); border-radius: 25px; }")
        aplicar_sombra(self, 26, 7)
        self.setMinimumHeight(142)
        distribucion = QVBoxLayout(self); distribucion.setContentsMargins(20, 18, 20, 18); distribucion.setSpacing(5)
        encabezado = QHBoxLayout()
        icono = QLabel("●")
        icono.setFixedSize(30, 30); icono.setAlignment(Qt.AlignCenter)
        icono.setStyleSheet(f"background: {color}; color: white; border-radius: 15px; font-size: 11px;")
        encabezado.addWidget(icono)
        encabezado.addSpacing(8)
        encabezado.addWidget(etiqueta(titulo, "font-size: 10px; color: #547182; font-weight: 800; letter-spacing: 0.6px;"))
        encabezado.addStretch()
        indicador = etiqueta("↗", f"background: #FFFFFF; color: {color}; border-radius: 13px; padding: 4px 8px; font-size: 14px; font-weight: 800;")
        encabezado.addWidget(indicador, alignment=Qt.AlignRight)
        distribucion.addLayout(encabezado)
        self.valor = etiqueta(valor, "font-size: 26px; font-weight: 800; padding-top: 8px;")
        self.descripcion = etiqueta(descripcion, "font-size: 10px; color: #6D8592;")
        distribucion.addWidget(self.valor)
        distribucion.addWidget(self.descripcion)

    def actualizar(self, valor: str, descripcion: str) -> None:
        self.valor.setText(valor)
        self.descripcion.setText(descripcion)


class PaginaInicio(Dashboard):
    def __init__(self, abrir_prestamos, abrir_clientes, abrir_simulador):
        super().__init__(abrir_prestamos, abrir_clientes, abrir_simulador)

    def cargar_resumen(self):
        self.load(obtener_resumen, obtener_actividad_reciente)


class PaginaListado(QWidget):
    def __init__(self, titulo, descripcion, accion, columnas, mensaje_vacio, al_accionar):
        super().__init__()
        self.columnas = columnas
        self.titulo_modulo = titulo
        self.mensaje_vacio = mensaje_vacio
        self.estado_col = columnas.index("ESTADO") if "ESTADO" in columnas else None
        self.money_col = next((columnas.index(name) for name in ("SALDO", "MONTO", "MONTO INICIAL") if name in columnas), None)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28,22,28,24)
        layout.setSpacing(18)
        heading = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(6)
        titles.addWidget(workspace_label('GESTIÓN / '+titulo.upper(),'workspaceEyebrow'))
        titles.addWidget(workspace_label(titulo,'workspaceTitle'))
        titles.addWidget(workspace_label(descripcion,wrap=True))
        heading.addLayout(titles,1)
        action = workspace_button(accion.lstrip('+ '),al_accionar)
        heading.addWidget(action)
        layout.addLayout(heading)
        summary = QHBoxLayout()
        summary.setSpacing(14)
        self.total_metric = Metric('REGISTROS',description='En este módulo',icon='document',compact=True)
        self.active_metric = Metric('ACTIVOS' if titulo in ('Clientes','Usuarios') else 'CUOTAS PENDIENTES' if titulo=='Cobros' else 'EN MORA',description='Según el estado registrado',icon='shield',compact=True)
        self.amount_metric = Metric(('SALDO TOTAL' if columnas[self.money_col]=='SALDO' else 'MONTO TOTAL') if self.money_col is not None else 'CON CORREO' if titulo=='Clientes' else 'INACTIVOS',description='Información de contacto' if titulo=='Clientes' else 'Cuentas deshabilitadas' if titulo=='Usuarios' else 'Importe de todos los registros',icon='coins' if self.money_col is not None else 'users',compact=True)
        for metric in (self.total_metric,self.active_metric,self.amount_metric): summary.addWidget(metric)
        layout.addLayout(summary)
        table_card = workspace_surface()
        self.table_card = table_card
        table_box = QVBoxLayout(table_card)
        table_box.setContentsMargins(1,1,1,1)
        table_box.setSpacing(0)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        toolbar.setContentsMargins(18,16,18,16)
        self.buscar = QLineEdit()
        self.buscar.setObjectName('workspaceSearch')
        self.buscar.setPlaceholderText('Buscar en '+titulo.lower()+'…')
        self.buscar.setAccessibleName('Buscar en '+titulo.lower())
        self.buscar.addAction(symbol('search'),QLineEdit.LeadingPosition)
        self.buscar.textChanged.connect(self.aplicar_filtros)
        toolbar.addWidget(self.buscar,1)
        self.filtro_estado = QComboBox()
        self.filtro_estado.setObjectName('workspaceFilter')
        self.filtro_estado.setAccessibleName('Filtrar por estado')
        self.filtro_estado.addItem('Todos los estados')
        self.filtro_estado.currentIndexChanged.connect(self.aplicar_filtros)
        toolbar.addWidget(self.filtro_estado)
        toolbar.addWidget(workspace_button('Limpiar',self.limpiar_filtros,False))
        table_box.addLayout(toolbar)
        self.tabla = DataTable(columnas)
        self.tabla.setMinimumHeight(230)
        self.tabla.contentChanged.connect(self.actualizar_presentacion)
        table_box.addWidget(self.tabla,1)
        footer = QHBoxLayout()
        footer.setContentsMargins(18,12,18,12)
        self.contador = workspace_label('Sin registros cargados','workspaceCount')
        footer.addWidget(self.contador)
        footer.addStretch()
        if 'ACCIÓN' in columnas:
            footer.addWidget(workspace_label('Doble clic en la acción para continuar','workspaceCount'))
        table_box.addLayout(footer)
        layout.addWidget(table_card)
        layout.addStretch(1)
        self.actualizar_presentacion()

    def actualizar_presentacion(self):
        current = self.filtro_estado.currentText()
        states = sorted({self.tabla.item(row,self.estado_col).text() for row in range(self.tabla.rowCount()) if self.estado_col is not None and self.tabla.item(row,self.estado_col)})
        self.filtro_estado.blockSignals(True)
        self.filtro_estado.clear()
        self.filtro_estado.addItems(['Todos los estados']+states)
        if current in states: self.filtro_estado.setCurrentText(current)
        self.filtro_estado.blockSignals(False)
        self.filtro_estado.setVisible(bool(states))
        total = self.tabla.rowCount()
        self.total_metric.actualizar(str(total))
        relevant = ('activo','activa') if self.titulo_modulo in ('Clientes','Usuarios') else ('pendiente','parcial','vencida') if self.titulo_modulo=='Cobros' else ('mora',)
        active = sum(1 for row in range(total) if self.estado_col is not None and self.tabla.item(row,self.estado_col) and self.tabla.item(row,self.estado_col).text().casefold() in relevant)
        self.active_metric.actualizar(str(active))
        if self.titulo_modulo=='Usuarios':
            inactive = sum(1 for row in range(total) if self.tabla.item(row,self.estado_col) and self.tabla.item(row,self.estado_col).text().casefold()=='inactivo')
            self.amount_metric.actualizar(str(inactive))
        elif self.titulo_modulo=='Clientes':
            email_col = self.columnas.index('CORREO')
            self.amount_metric.actualizar(str(sum(1 for row in range(total) if self.tabla.item(row,email_col) and '@' in self.tabla.item(row,email_col).text())))
        if self.money_col is not None:
            value = Decimal('0')
            for row in range(total):
                item = self.tabla.item(row,self.money_col)
                if item:
                    try: value += Decimal(item.text().replace('C$', '').replace(',', '').strip())
                    except InvalidOperation: pass
            self.amount_metric.actualizar(f'C$ {value:,.2f}')
        self.aplicar_filtros()

    def aplicar_filtros(self, *_):
        if not hasattr(self,'tabla'): return
        query = normalized(self.buscar.text().strip())
        state = self.filtro_estado.currentText()
        count = 0
        for row in range(self.tabla.rowCount()):
            texts = [self.tabla.item(row,column).text() if self.tabla.item(row,column) else '' for column in range(self.tabla.columnCount())]
            match = query in normalized(' '.join(texts)) and (state in ('','Todos los estados') or (self.estado_col is not None and texts[self.estado_col]==state))
            self.tabla.setRowHidden(row,not match)
            count += int(match)
        self.contador.setText(f'{count} de {self.tabla.rowCount()} registros')
        self.tabla.show_empty('' if count else ('No se encontraron coincidencias. Prueba otra búsqueda o limpia los filtros.' if self.tabla.rowCount() else self.mensaje_vacio))
        QTimer.singleShot(0,self.ajustar_altura_tabla)

    def ajustar_altura_tabla(self):
        visible = sum(not self.tabla.isRowHidden(row) for row in range(self.tabla.rowCount()))
        available = max(360,self.height()-self.table_card.y()-24)
        desired = max(360,(visible or 3)*52+170)
        height = min(available,desired)
        if self.table_card.height()!=height:
            self.table_card.setFixedHeight(height)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'table_card'):
            QTimer.singleShot(0,self.ajustar_altura_tabla)

    def limpiar_filtros(self):
        self.buscar.clear()
        self.filtro_estado.setCurrentIndex(0)
        self.aplicar_filtros()


class PaginaClientes(PaginaListado):
    def __init__(self, actor_id=None, version_sesion=1) -> None:
        super().__init__(
            "Clientes",
            "Administra la información y el historial de cada cliente.",
            "+  Nuevo cliente",
            ["CÉDULA", "NOMBRE", "TELÉFONO", "CORREO", "ESTADO", "ACCIÓN"],
            "Todavía no hay clientes. Registra el primero para iniciar la cartera.",
            self.abrir_formulario_cliente,
        )
        self.actor_id=actor_id
        self.version_sesion=version_sesion
        self.tabla.cellDoubleClicked.connect(self.abrir_ficha_cliente)
        actions=QHBoxLayout()
        actions.addWidget(workspace_button('Editar cliente',self.editar_seleccionado,False))
        self.boton_eliminar=workspace_button('Eliminar cliente',self.eliminar_seleccionado,False)
        self.boton_eliminar.setToolTip('Eliminar si no tiene préstamos; con historial se conserva y se inactiva. Solo administrador.')
        actions.addWidget(self.boton_eliminar)
        actions.addWidget(workspace_button('Préstamos / reporte del cliente',self.reporte_seleccionado,False))
        actions.addStretch()
        self.layout().insertLayout(1,actions)

    def _con_actor(self, operacion, *args, **kwargs):
        """Ejecuta la operaci?n con el usuario que inici? sesi?n en esta GUI."""
        token=establecer_actor(self.actor_id,self.version_sesion)
        try:
            return operacion(*args,**kwargs)
        finally:
            restablecer_actor(token)

    def cliente_seleccionado(self):
        row=self.tabla.currentRow()
        if row<0: raise ValueError('Selecciona un cliente.')
        return self.tabla.item(row,5).data(Qt.UserRole)

    def editar_seleccionado(self):
        try: self.abrir_formulario_cliente(self.cliente_seleccionado())
        except (ValueError,ErrorConexionBaseDatos) as error: QMessageBox.warning(self,'Cliente',str(error))

    def eliminar_seleccionado(self):
        try:
            id=self.cliente_seleccionado()
            if QMessageBox.question(self,'Eliminar cliente','Se eliminará si no tiene préstamos; si tiene historial quedará inactivo. ¿Continuar?')!=QMessageBox.Yes: return
            result=self._con_actor(eliminar_cliente,id)
            self.cargar_clientes()
            QMessageBox.information(self,'Cliente actualizado',result.capitalize())
        except (ValueError,ErrorConexionBaseDatos) as error: QMessageBox.warning(self,'Cliente',str(error))

    def reporte_seleccionado(self):
        try: ReportDialog(self._con_actor(lambda:obtener_reporte(cliente_id=self.cliente_seleccionado())),self).exec()
        except (ValueError,ErrorConexionBaseDatos) as error: QMessageBox.warning(self,'Reporte',str(error))


    def cargar_clientes(self) -> None:
        try:
            clientes = self._con_actor(listar_clientes)
        except (ValueError, ErrorConexionBaseDatos) as error:
            QMessageBox.warning(self, "Sin conexión", str(error))
            return
        self.tabla.setRowCount(len(clientes))
        for fila, cliente in enumerate(clientes):
            valores = (
                cliente["cedula"], cliente["nombre_completo"], cliente["telefono"],
                cliente["correo"] or "-", cliente["estado"].title(), "Ver ficha",
            )
            for columna, valor in enumerate(valores):
                celda = QTableWidgetItem(str(valor))
                celda.setTextAlignment(Qt.AlignCenter if columna in (4, 5) else Qt.AlignLeft | Qt.AlignVCenter)
                self.tabla.setItem(fila, columna, celda)
            self.tabla.item(fila, 5).setData(Qt.UserRole, cliente["id"])

    def abrir_ficha_cliente(self, fila: int, columna: int) -> None:
        if columna != 5:
            return
        try:
            cliente = self._con_actor(obtener_cliente_para_cuenta,self.tabla.item(fila, 5).data(Qt.UserRole))
        except (ValueError, ErrorConexionBaseDatos) as error:
            QMessageBox.warning(self, "No se pudo abrir la ficha", str(error))
            return
        dialogo = QDialog(self); dialogo.setWindowTitle("Cuenta de cliente | CRECE + PRÉSTAMOS"); dialogo.setMinimumWidth(420)
        distribucion = QVBoxLayout(dialogo)
        distribucion.addWidget(etiqueta(cliente["nombre"], "font-size: 21px; font-weight: 800;"))
        distribucion.addWidget(etiqueta(f"Cédula: {cliente['cedula']}", f"color: {GRIS_NEUTRO};"))
        if cliente["usuario_id"]:
            distribucion.addWidget(etiqueta("Esta cuenta ya existe. Confirma el correo que el cliente usará para ingresar al portal web.", f"background: #E6F5ED; color: {VERDE_OSCURO}; padding: 12px; border-radius: 8px;"))
            formulario = QFormLayout(); correo_existente = QLineEdit(cliente["correo"] or ""); configurar_campo(correo_existente,"correo")
            formulario.addRow("Correo electrónico", correo_existente); distribucion.addLayout(formulario)
            guardar_correo = QPushButton("Guardar correo de acceso"); distribucion.addWidget(guardar_correo)
            def actualizar_correo() -> None:
                try: self._con_actor(actualizar_correo_cliente_portal,cliente["id"], correo_existente.text())
                except (ValueError, ErrorConexionBaseDatos) as error: QMessageBox.warning(dialogo, "No se pudo actualizar", str(error)); return
                dialogo.accept(); self.cargar_clientes(); QMessageBox.information(self, "Correo actualizado", "El cliente ya puede acceder al portal web con su correo y contraseña.")
            guardar_correo.clicked.connect(actualizar_correo)
            dialogo.exec(); return
        distribucion.addWidget(etiqueta("Registra el correo y una contraseña. El cliente usará esos datos para ingresar únicamente a su portal.", f"color: {GRIS_NEUTRO};"))
        formulario = QFormLayout(); correo, contrasena = QLineEdit(cliente["correo"] or ""), QLineEdit(); contrasena.setEchoMode(QLineEdit.Password)
        configurar_campo(correo,"correo")
        formulario.addRow("Correo electrónico", correo); formulario.addRow("Contraseña", contrasena); distribucion.addLayout(formulario)
        crear = QPushButton("Crear cuenta de cliente"); distribucion.addWidget(crear)
        def guardar() -> None:
            try: self._con_actor(crear_cuenta_cliente,cliente["id"], correo.text(), contrasena.text())
            except (ValueError, ErrorConexionBaseDatos) as error: QMessageBox.warning(dialogo, "No se pudo crear", str(error)); return
            dialogo.accept(); self.cargar_clientes(); QMessageBox.information(self, "Cuenta creada", "El cliente ya puede iniciar sesión en su portal.")
        crear.clicked.connect(guardar); dialogo.exec()

    def abrir_formulario_cliente(self, cliente_id=None) -> None:
        dialogo = QDialog(self)
        dialogo.setWindowTitle("Registrar cliente | CRECE + PRÉSTAMOS")
        dialogo.setMinimumWidth(440)
        distribucion = QVBoxLayout(dialogo)
        distribucion.addWidget(etiqueta("Nuevo cliente", "font-size: 21px; font-weight: 800;"))
        distribucion.addWidget(etiqueta("Los campos con información básica son obligatorios.", f"color: {GRIS_NEUTRO};"))
        formulario = QFormLayout(); formulario.setSpacing(11)
        cedula, nombres, apellidos = QLineEdit(), QLineEdit(), QLineEdit()
        telefono, correo, direccion = QLineEdit(), QLineEdit(), QLineEdit()
        campos_persona=dict(cedula=cedula,nombres=nombres,apellidos=apellidos,telefono=telefono,correo=correo,direccion=direccion)
        ayudas={key:configurar_campo(field,key,requerido=key not in ("correo","direccion")) for key,field in campos_persona.items()}
        for titulo, campo in (("Cédula *", cedula), ("Nombres *", nombres), ("Apellidos *", apellidos), ("Teléfono *", telefono), ("Correo", correo), ("Dirección", direccion)):
            formulario.addRow(titulo, campo)
            key=next(k for k,v in campos_persona.items() if v is campo)
            formulario.addRow("",ayudas[key])
        estado=QComboBox()
        estado.addItems(['ACTIVO','INACTIVO','BLOQUEADO'])
        if cliente_id is not None:
            data=self._con_actor(obtener_cliente,cliente_id)
            for key,field in [('cedula',cedula),('nombres',nombres),('apellidos',apellidos),('telefono',telefono),('correo',correo),('direccion',direccion)]: field.setText(data[key] or '')
            estado.setCurrentText(data['estado'])
            formulario.addRow('Estado',estado)
            dialogo.setWindowTitle('Editar cliente | CRECE+ PRÉSTAMOS')
        contenido=QWidget();contenido.setLayout(formulario)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(contenido)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollArea > QWidget > QWidget { background: transparent; }")
        scroll.verticalScrollBar().setStyleSheet("QScrollBar:vertical { width: 10px; margin: 0px; } QScrollBar::handle:vertical { background: #00A651; min-height: 28px; border-radius: 4px; } QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }")
        distribucion.addWidget(scroll,1)
        dialogo.resize(570,min(740,dialogo.screen().availableGeometry().height()-80))
        acciones = QHBoxLayout(); acciones.addStretch()
        cancelar = boton_secundario("Cancelar"); cancelar.clicked.connect(dialogo.reject)
        guardar = QPushButton("Guardar cliente")
        acciones.addWidget(cancelar); acciones.addWidget(guardar); distribucion.addLayout(acciones)

        def guardar_cliente() -> None:
            try:
                values=(cedula.text(), nombres.text(), apellidos.text(), telefono.text(), correo.text(), direccion.text())
                if cliente_id is None: self._con_actor(registrar_cliente,*values)
                else: self._con_actor(actualizar_cliente,cliente_id,*values,estado.currentText())
            except (ValueError, ErrorConexionBaseDatos) as error:
                enfocar_error(dialogo,error)
                QMessageBox.warning(dialogo, "No se pudo guardar", str(error))
                return
            dialogo.accept()
            self.cargar_clientes()
            QMessageBox.information(self, "Cliente registrado", "El cliente fue guardado correctamente.")

        guardar.clicked.connect(guardar_cliente)
        dialogo.exec()


class PaginaPrestamos(PaginaListado):
    def __init__(self) -> None:
        super().__init__(
            "Préstamos",
            "Emite créditos, calcula cuotas francesas y consulta la cartera activa.",
            "+  Emitir préstamo",
            ["CÓDIGO", "CLIENTE", "MONTO", "CUOTA", "CUOTAS / FRECUENCIA", "ESTADO"],
            "No hay préstamos registrados. Emite el primero a un cliente activo.",
            self.abrir_formulario_prestamo,
        )

        self.tabla.cellDoubleClicked.connect(lambda *_:self.ver_detalle())
        actions=QHBoxLayout()
        actions.addWidget(workspace_button('Detalle / cuotas / imprimir',self.ver_detalle,False))
        actions.addWidget(workspace_button('Editar notas',self.editar_notas,False))
        actions.addWidget(workspace_button('Anular / eliminar',self.anular_seleccionado,False))
        actions.addStretch()
        self.layout().insertLayout(1,actions)

    def prestamo_seleccionado(self):
        row=self.tabla.currentRow()
        if row<0: raise ValueError('Selecciona un préstamo.')
        return self.tabla.item(row,0).data(Qt.UserRole)

    def ver_detalle(self, prestamo_id=None):
        try: ReportDialog(obtener_reporte(prestamo_id=prestamo_id or self.prestamo_seleccionado()),self).exec()
        except (ValueError,ErrorConexionBaseDatos) as error: QMessageBox.warning(self,'Préstamo',str(error))

    def editar_notas(self):
        try:
            id=self.prestamo_seleccionado()
            report=obtener_reporte(prestamo_id=id)
            value,ok=QInputDialog.getMultiLineText(self,'Notas del préstamo','Las condiciones emitidas se conservan. Observaciones:',report['prestamos'][0]['notas'] or '')
            if ok: actualizar_prestamo(id,value); self.cargar_prestamos()
        except (ValueError,ErrorConexionBaseDatos) as error: QMessageBox.warning(self,'Préstamo',str(error))

    def anular_seleccionado(self):
        try:
            id=self.prestamo_seleccionado()
            reason,ok=QInputDialog.getText(self,'Anular préstamo',f'Motivo para PR-{id:05d}. Los movimientos se conservan:')
            if not ok: return
            if QMessageBox.question(self,'Confirmar anulación',f'¿Anular PR-{id:05d}? Un borrador sin pagos se elimina; un préstamo emitido se conserva cancelado.')!=QMessageBox.Yes: return
            eliminar_prestamo(id,reason)
            self.cargar_prestamos()
        except (ValueError,ErrorConexionBaseDatos) as error: QMessageBox.warning(self,'Préstamo',str(error))

    def cargar_prestamos(self) -> None:
        try:
            prestamos = listar_prestamos()
        except (ValueError, ErrorConexionBaseDatos) as error:
            QMessageBox.warning(self, "Sin conexión", str(error))
            return
        self.tabla.setRowCount(len(prestamos))
        for fila, prestamo in enumerate(prestamos):
            valores = (
                f"PR-{prestamo['id']:05d}", prestamo["cliente"],
                f"C${prestamo['monto_principal']:,.2f}", f"C${prestamo['cuota_mensual']:,.2f}",
                f"{prestamo['plazo_meses']} cuotas · {prestamo.get('frecuencia','MENSUAL').lower()}", prestamo["estado"].title(),
            )
            for columna, valor in enumerate(valores):
                celda = QTableWidgetItem(str(valor))
                celda.setTextAlignment(Qt.AlignCenter if columna in (0, 2, 3, 4, 5) else Qt.AlignLeft | Qt.AlignVCenter)
                self.tabla.setItem(fila, columna, celda)
            self.tabla.item(fila,0).setData(Qt.UserRole,prestamo["id"])

    def abrir_formulario_prestamo(self) -> None:
        try:
            clientes = listar_clientes_para_prestamo()
        except (ValueError, ErrorConexionBaseDatos) as error:
            QMessageBox.warning(self, "Sin conexión", str(error))
            return
        if not clientes:
            QMessageBox.information(self, "Sin clientes activos", "Primero registra un cliente activo antes de emitir un préstamo.")
            return
        dialogo = QDialog(self)
        dialogo.setWindowTitle("Emitir préstamo | CRECE + PRÉSTAMOS")
        dialogo.setMinimumWidth(490)
        distribucion = QVBoxLayout(dialogo)
        distribucion.addWidget(etiqueta("Emitir préstamo", "font-size: 21px; font-weight: 800;"))
        distribucion.addWidget(etiqueta("Interes plano: cada cuota calcula intereses sobre el capital inicial.", f"color: {GRIS_NEUTRO};"))
        formulario = QFormLayout(); formulario.setSpacing(11)
        cliente = QComboBox()
        for registro in clientes:
            cliente.addItem(f"{registro['nombre']}  |  {registro['cedula']}", registro["id"])
        monto, tasa, plazo = QLineEdit("10000"), QLineEdit("12"), QLineEdit("12")
        tipo_credito=QComboBox()
        for codigo,nombre in TIPOS_CREDITO.items(): tipo_credito.addItem(f"{nombre} | {TASAS_TIPO_CREDITO[codigo]}% mensual",codigo)
        tasa.setReadOnly(True)
        frecuencia=QComboBox()
        for codigo,nombre in FRECUENCIAS.items():frecuencia.addItem(nombre,codigo)
        for field,tipo in [(monto,"monto"),(tasa,"tasa"),(plazo,"meses")]:configurar_numero(field,tipo)
        fecha_desembolso, fecha_primera_cuota = QDateEdit(), QDateEdit()
        for campo in (fecha_desembolso, fecha_primera_cuota):
            campo.setCalendarPopup(True)
        fecha_desembolso.setDate(date.today())
        fecha_primera_cuota.setDate(date.today() + timedelta(days=30))
        for titulo, campo in (("Cliente *", cliente), ("Modalidad *", tipo_credito), ("Monto principal (C$) *", monto), ("Tasa mensual fija", tasa), ("Frecuencia de pago *", frecuencia), ("Número de cuotas *", plazo), ("Fecha de desembolso", fecha_desembolso), ("Primera cuota", fecha_primera_cuota)):
            formulario.addRow(titulo, campo)
        distribucion.addLayout(formulario)
        vista_previa = etiqueta("Ingresa los datos para calcular la cuota periódica.", f"background: #E6F5ED; border-radius: 8px; padding: 13px; color: {VERDE_OSCURO};")
        vista_previa.setWordWrap(True)
        distribucion.addWidget(vista_previa)
        condiciones=etiqueta('Recargo único del 1 % sobre el capital pendiente de cada cuota después de 72 horas desde el final de su vencimiento. No se capitaliza. Un préstamo sin saldar por cliente. Quincenas de 15 días; semanas de 7 días; días calendario.')
        condiciones.setWordWrap(True)
        distribucion.addWidget(condiciones)

        def actualizar_vista_previa() -> None:
            try:
                tabla = calcular_tabla_credito(leer_numero(monto,"monto"), leer_numero(tasa,"tasa"), leer_plazo(plazo), fecha_primera_cuota.date().toPython(),frecuencia.currentData(),metodo_interes="PLANO")
                total = sum(cuota.pago for cuota in tabla)
                periodo=tasa_por_periodo(leer_numero(tasa,'tasa'),frecuencia.currentData())
                vista_previa.setText(f"Cuota inicial: <b>C${tabla[0].pago:,.2f}</b> | Interes plano por periodo: {periodo:.6f} % del capital inicial | Total: <b>C${total:,.2f}</b> | Ultima cuota: {tabla[-1].fecha_vencimiento:%d/%m/%Y}")
            except (ValueError, InvalidOperation):
                vista_previa.setText("Ingresa un monto, tasa y plazo válidos para calcular la cuota.")

        def actualizar_tasa_modalidad() -> None:
            tasa.setText(str(TASAS_TIPO_CREDITO[tipo_credito.currentData()]))
            actualizar_vista_previa()

        tipo_credito.currentIndexChanged.connect(actualizar_tasa_modalidad)
        monto.textChanged.connect(actualizar_vista_previa)
        plazo.textChanged.connect(actualizar_vista_previa)
        frecuencia.currentIndexChanged.connect(actualizar_vista_previa)
        fecha_primera_cuota.dateChanged.connect(actualizar_vista_previa)
        actualizar_vista_previa()
        acciones = QHBoxLayout(); acciones.addStretch()
        cancelar = boton_secundario("Cancelar"); cancelar.clicked.connect(dialogo.reject)
        guardar = QPushButton("Emitir préstamo")
        acciones.addWidget(cancelar); acciones.addWidget(guardar); distribucion.addLayout(acciones)

        def guardar_prestamo() -> None:
            try:
                monto_principal = leer_numero(monto,"monto")
                tasa_mensual = leer_numero(tasa,"tasa")
                plazo_meses = leer_plazo(plazo)
                fecha_inicio = fecha_desembolso.date().toPython()
                fecha_cuota = fecha_primera_cuota.date().toPython()
                if fecha_cuota <= fecha_inicio:
                    raise ValueError("La primera cuota debe ser posterior al desembolso.")
                codigo = registrar_prestamo_periodico(cliente.currentData(), monto_principal, tasa_mensual, plazo_meses, fecha_inicio, fecha_cuota,frecuencia.currentData(),tipo_credito=tipo_credito.currentData(),metodo_interes="PLANO")
            except (ValueError, InvalidOperation, ErrorConexionBaseDatos) as error:
                QMessageBox.warning(dialogo, "No se pudo emitir", str(error))
                return
            dialogo.accept()
            self.cargar_prestamos()
            if QMessageBox.question(self,'Préstamo emitido',f'PR-{codigo:05d} registrado con {plazo_meses} cuotas. ¿Abrir la ficha para guardar PDF/Excel o imprimir?')==QMessageBox.Yes:
                self.ver_detalle(codigo)

        guardar.clicked.connect(guardar_prestamo)
        dialogo.exec()


class PaginaCobros(PaginaListado):
    def __init__(self) -> None:
        super().__init__(
            "Cobros",
            "Registra pagos, actualiza saldos y controla las cuotas vencidas.",
            "+  Registrar cobro",
            ["CLIENTE", "PRÉSTAMO", "CUOTA", "VENCIMIENTO", "SALDO TOTAL", "TASA DEL PERÍODO EQUIVALENTE (C$)", "ESTADO", "RECARGO PENDIENTE"],
            "No hay cuotas pendientes de cobro.",
            self.abrir_formulario_cobro,
        )

        actions=QHBoxLayout()
        actions.addWidget(workspace_button('Historial / solicitudes de pago',self.historial_pagos,False))
        actions.addStretch()
        self.layout().insertLayout(1,actions)

    def historial_pagos(self):
        from ui.payments import PaymentsDialog
        PaymentsDialog(self).exec()
        self.cargar_cobros()

    def cargar_cobros(self) -> None:
        try:
            cuotas = listar_cuotas_cobro()
        except (ValueError, ErrorConexionBaseDatos) as error:
            QMessageBox.warning(self, "Sin conexión", str(error))
            return
        self.tabla.setRowCount(len(cuotas))
        for fila, cuota in enumerate(cuotas):
            valores = (
                cuota["cliente"], f"PR-{cuota['prestamo_id']:05d}", f"#{cuota['numero_cuota']}",
                cuota["fecha_vencimiento"].strftime("%d/%m/%Y"), f"C${cuota['saldo_cuota']:,.2f}", f"C${cuota['interes']:,.2f}", cuota["estado"].title(), f"C${cuota.get('recargo_pendiente',0):,.2f}",
            )
            for columna, valor in enumerate(valores):
                celda = QTableWidgetItem(str(valor))
                celda.setTextAlignment(Qt.AlignCenter if columna > 0 else Qt.AlignLeft | Qt.AlignVCenter)
                self.tabla.setItem(fila, columna, celda)

    def abrir_formulario_cobro(self) -> None:
        try:
            cuotas = listar_cuotas_cobro()
        except (ValueError, ErrorConexionBaseDatos) as error:
            QMessageBox.warning(self, "Sin conexión", str(error))
            return
        if not cuotas:
            QMessageBox.information(self, "Sin cuotas", "No hay cuotas pendientes de cobro.")
            return
        dialogo = QDialog(self)
        dialogo.setWindowTitle("Registrar cobro | CRECE + PRÉSTAMOS")
        dialogo.setMinimumWidth(480)
        distribucion = QVBoxLayout(dialogo)
        distribucion.addWidget(etiqueta("Registrar cobro", "font-size: 21px; font-weight: 800;"))
        distribucion.addWidget(etiqueta("El excedente adelanta las cuotas siguientes del mismo prestamo.", f"color: {GRIS_NEUTRO};"))
        formulario = QFormLayout(); formulario.setSpacing(11)
        cuota = QComboBox()
        for registro in cuotas:
            cuota.addItem(f"{registro['cliente']} | PR-{registro['prestamo_id']:05d} | cuota #{registro['numero_cuota']} | saldo C${registro['saldo_cuota']:,.2f}", registro)
        monto = QLineEdit()
        metodo = QComboBox(); metodo.addItems(["EFECTIVO", "TRANSFERENCIA", "TARJETA"])
        configurar_numero(monto,"monto")
        referencia = QLineEdit(); referencia.setMaxLength(100); referencia.setPlaceholderText("Número de recibo o transferencia (opcional)")
        formulario.addRow("Cuota pendiente *", cuota); formulario.addRow("Monto recibido (C$) *", monto); formulario.addRow("Método *", metodo); formulario.addRow("Referencia", referencia)
        distribucion.addLayout(formulario)
        saldo = etiqueta("", f"background: #E6F5ED; border-radius: 8px; padding: 12px; color: {VERDE_OSCURO};")
        distribucion.addWidget(saldo)

        def actualizar_saldo() -> None:
            registro = cuota.currentData()
            maximo = sum((r['saldo_cuota'] for r in cuotas if r['prestamo_id']==registro['prestamo_id'] and r['numero_cuota']>=registro['numero_cuota']), Decimal('0'))
            monto.setText(f"{registro['saldo_cuota']:.2f}")
            saldo.setText(f"Saldo de esta cuota: <b>C${registro['saldo_cuota']:,.2f}</b> | Recargo: C${registro.get('recargo_pendiente',0):,.2f}<br>Maximo desde esta cuota, incluyendo las siguientes: <b>C${maximo:,.2f}</b>")
            saldo.setWordWrap(True)

        cuota.currentIndexChanged.connect(actualizar_saldo)
        actualizar_saldo()
        acciones = QHBoxLayout(); acciones.addStretch()
        cancelar = boton_secundario("Cancelar"); cancelar.clicked.connect(dialogo.reject)
        guardar = QPushButton("Confirmar cobro")
        acciones.addWidget(cancelar); acciones.addWidget(guardar); distribucion.addLayout(acciones)

        def guardar_cobro() -> None:
            try:
                registro = cuota.currentData()
                registrar_cobro(registro["cuota_id"], leer_numero(monto,"monto"), metodo.currentText(), referencia.text())
            except (ValueError, InvalidOperation, ErrorConexionBaseDatos) as error:
                QMessageBox.warning(dialogo, "No se pudo registrar", str(error))
                return
            dialogo.accept()
            self.cargar_cobros()
            QMessageBox.information(self, "Cobro registrado", "El pago se distribuyo desde la cuota seleccionada hacia las siguientes, segun el saldo.")

        guardar.clicked.connect(guardar_cobro)
        dialogo.exec()


class PaginaReportes(PaginaListado):
    def __init__(self) -> None:
        super().__init__(
            "Reportes de cartera",
            "Consulta saldos por préstamo, clientes en mora y comportamiento de cartera.",
            "Actualizar reporte",
            ["PRÉSTAMO", "CLIENTE", "MONTO INICIAL", "SALDO", "MORA", "ESTADO"],
            "No hay préstamos para incluir en el reporte.",
            self.cargar_reporte,
        )

        actions=QHBoxLayout()
        self.cliente_reporte=QComboBox()
        self.cliente_reporte.setObjectName('workspaceFilter')
        self.cliente_reporte.setAccessibleName('Alcance del reporte por cliente')
        self.cliente_reporte.addItem('Reporte general',None)
        actions.addWidget(self.cliente_reporte,1)
        actions.addWidget(workspace_button('PDF / Excel / imprimir',self.abrir_exportacion,False))
        self.layout().insertLayout(1,actions)
        self.cliente_reporte.currentIndexChanged.connect(self.filtrar_cliente)
        self.buscar.textChanged.connect(self.filtrar_cliente)
        self.filtro_estado.currentIndexChanged.connect(self.filtrar_cliente)

    def filtrar_cliente(self,*_):
        self.aplicar_filtros()

    def aplicar_filtros(self,*_):
        super().aplicar_filtros()
        if not hasattr(self,'cliente_reporte'): return
        selected=self.cliente_reporte.currentData()
        for row in range(self.tabla.rowCount()):
            data=self.tabla.item(row,0).data(Qt.UserRole) or {}
            if selected is not None and data.get('cliente_id')!=selected: self.tabla.setRowHidden(row,True)
        count=sum(not self.tabla.isRowHidden(row) for row in range(self.tabla.rowCount()))
        self.contador.setText(f'{count} de {self.tabla.rowCount()} registros')
        self.tabla.show_empty('No hay préstamos que coincidan con los filtros.' if not count else '')

    def abrir_exportacion(self):
        try:
            report=obtener_reporte(cliente_id=self.cliente_reporte.currentData())
            visible={self.tabla.item(row,0).data(Qt.UserRole)['id'] for row in range(self.tabla.rowCount()) if not self.tabla.isRowHidden(row)}
            from crece.servicios.reportes import limitar_reporte
            report=limitar_reporte(report,visible)
            ReportDialog(report,self).exec()
        except (ValueError,ErrorConexionBaseDatos) as error: QMessageBox.warning(self,'Reporte',str(error))

    def cargar_reporte(self) -> None:
        try:
            registros = obtener_reporte_cartera()
        except (ValueError, ErrorConexionBaseDatos) as error:
            QMessageBox.warning(self, "Sin conexión", str(error))
            return
        current=self.cliente_reporte.currentData()
        self.cliente_reporte.blockSignals(True)
        self.cliente_reporte.clear()
        self.cliente_reporte.addItem('Reporte general',None)
        clients={r['cliente_id']:r['cliente'] for r in registros if 'cliente_id' in r}
        for id,name in sorted(clients.items(),key=lambda pair:pair[1]): self.cliente_reporte.addItem(name,id)
        self.cliente_reporte.setCurrentIndex(max(0,self.cliente_reporte.findData(current)))
        self.cliente_reporte.blockSignals(False)
        self.tabla.setRowCount(len(registros))
        for fila, registro in enumerate(registros):
            valores = (
                f"PR-{registro['id']:05d}", registro["cliente"], f"C${registro['monto_principal']:,.2f}",
                f"C${registro['saldo_pendiente']:,.2f}", str(registro["cuotas_vencidas"]), registro["estado"].title(),
            )
            for columna, valor in enumerate(valores):
                celda = QTableWidgetItem(str(valor))
                celda.setTextAlignment(Qt.AlignCenter if columna != 1 else Qt.AlignLeft | Qt.AlignVCenter)
                self.tabla.setItem(fila, columna, celda)
            self.tabla.item(fila,0).setData(Qt.UserRole,registro)

        self.filtrar_cliente()


class PaginaUsuarios(PaginaListado):
    def __init__(self) -> None:
        super().__init__("Usuarios", "Controla las cuentas y permisos del personal.", "+  Nuevo usuario", ["USUARIO", "ROL", "ESTADO", "ÚLTIMO ACCESO", "ACCIÓN"], "No hay usuarios configurados.", self.abrir_formulario_usuario)
        self.tabla.cellDoubleClicked.connect(self.cambiar_estado)
        actions=QHBoxLayout()
        actions.addWidget(workspace_button('Editar cuenta',self.editar_cuenta,False))
        actions.addWidget(workspace_button('Recuperar acceso',self.recuperar_acceso,False))
        actions.addWidget(workspace_button('Eliminar / desactivar',self.eliminar_cuenta,False))
        actions.addStretch()
        self.layout().insertLayout(1,actions)

    def recuperar_acceso(self):
        row=self.tabla.currentRow()
        if row<0:QMessageBox.information(self,'Cuenta','Selecciona una cuenta.');return
        from ui.admin_recovery import recuperar_cuenta
        recuperar_cuenta(self,self.tabla.item(row,4).data(Qt.UserRole),self.tabla.item(row,0).text())

    def editar_cuenta(self):
        row=self.tabla.currentRow()
        if row<0: QMessageBox.information(self,'Cuenta','Selecciona una cuenta.');return
        id=self.tabla.item(row,4).data(Qt.UserRole)
        name,ok=QInputDialog.getText(self,'Editar cuenta','Usuario de acceso:',text=self.tabla.item(row,0).text())
        if not ok:return
        password,ok=QInputDialog.getText(self,'Contraseña','Nueva contraseña (vacío conserva la actual):',QLineEdit.Password)
        if not ok:return
        try: actualizar_usuario(id,name,password);self.cargar_usuarios()
        except (ValueError,ErrorConexionBaseDatos) as error:QMessageBox.warning(self,'Cuenta',str(error))

    def eliminar_cuenta(self):
        row=self.tabla.currentRow()
        if row<0: QMessageBox.information(self,'Cuenta','Selecciona una cuenta.');return
        if QMessageBox.question(self,'Eliminar cuenta','¿Eliminar esta cuenta? Si tiene vínculos se desactiva conservando el historial.')!=QMessageBox.Yes:return
        try: eliminar_usuario(self.tabla.item(row,4).data(Qt.UserRole));self.cargar_usuarios()
        except (ValueError,ErrorConexionBaseDatos) as error:QMessageBox.warning(self,'Cuenta',str(error))


    def cargar_usuarios(self) -> None:
        try:
            usuarios = listar_usuarios()
        except (ValueError, ErrorConexionBaseDatos) as error:
            QMessageBox.warning(self, "Sin conexión", str(error)); return
        self.tabla.setRowCount(len(usuarios))
        for fila, usuario in enumerate(usuarios):
            ultimo_acceso = usuario["ultimo_acceso_en"].strftime("%d/%m/%Y %H:%M") if usuario["ultimo_acceso_en"] else "Nunca"
            valores = (usuario["nombre_usuario"], usuario["rol"].title(), "Activo" if usuario["activo"] else "Inactivo", ultimo_acceso, "Desactivar" if usuario["activo"] else "Activar")
            for columna, valor in enumerate(valores):
                celda = QTableWidgetItem(valor); celda.setTextAlignment(Qt.AlignCenter); self.tabla.setItem(fila, columna, celda)
            self.tabla.item(fila, 4).setData(Qt.UserRole, usuario["id"])

    def cambiar_estado(self, fila: int, columna: int) -> None:
        if columna != 4:
            return
        accion = self.tabla.item(fila, columna)
        try:
            cambiar_estado_usuario(accion.data(Qt.UserRole), accion.text() == "Activar")
        except (ValueError, ErrorConexionBaseDatos) as error:
            QMessageBox.warning(self, "No se pudo actualizar", str(error)); return
        self.cargar_usuarios()

    def abrir_formulario_usuario(self) -> None:
        dialogo = QDialog(self); dialogo.setWindowTitle("Crear usuario | CRECE + PRÉSTAMOS"); dialogo.setMinimumWidth(410)
        distribucion = QVBoxLayout(dialogo); distribucion.addWidget(etiqueta("Nuevo usuario", "font-size: 21px; font-weight: 800;"))
        formulario = QFormLayout(); nombre, contrasena, rol = QLineEdit(), QLineEdit(), QComboBox(); contrasena.setEchoMode(QLineEdit.Password); rol.addItems(["EMPLEADO", "ADMINISTRADOR"])
        formulario.addRow("Usuario", nombre); formulario.addRow("Contraseña", contrasena); formulario.addRow("Rol", rol); distribucion.addLayout(formulario)
        guardar = QPushButton("Crear cuenta"); distribucion.addWidget(guardar)
        def crear() -> None:
            try: crear_usuario_personal(nombre.text(), contrasena.text(), rol.currentText())
            except (ValueError, ErrorConexionBaseDatos) as error: QMessageBox.warning(dialogo, "No se pudo crear", str(error)); return
            dialogo.accept(); self.cargar_usuarios()
        guardar.clicked.connect(crear); dialogo.exec()


class SimuladorPrestamo(PremiumSimulator):
    def __init__(self):
        super().__init__(calcular_tabla_mensual)


from ui.appearance import bind_theme, theme_picker
from ui.widgets.premium import Scene


class PanelPrincipal(QMainWindow):
    def __init__(self, usuario: dict | None = None) -> None:
        super().__init__()
        self.usuario = usuario or {"nombre_usuario": "Administrador", "rol": "ADMINISTRADOR"}
        establecer_actor(self.usuario.get("id"),self.usuario.get("version_sesion",1))
        self.setWindowTitle("CRECE + PRÉSTAMOS | Gestión crediticia")
        self.resize(1400, 820)
        self.setMinimumSize(1120, 690)
        load_fonts()
        self.setObjectName('workspace')
        self.setStyleSheet(workspace_styles())
        raiz = Scene(workspace=True)
        distribucion = QHBoxLayout(raiz)
        distribucion.setContentsMargins(0,0,0,0)
        distribucion.setSpacing(0)
        self.setCentralWidget(raiz)
        distribucion.addWidget(workspace_sidebar(self))
        contenedor = QWidget()
        area = QVBoxLayout(contenedor)
        area.setContentsMargins(0,0,0,0)
        area.setSpacing(0)
        area.addWidget(self.crear_barra_superior())
        self.contenedor_paginas = QStackedWidget()
        area.addWidget(self.contenedor_paginas,1)
        distribucion.addWidget(contenedor,1)
        self.pagina_inicio = PaginaInicio(lambda:self.mostrar_pagina(2),lambda:self.mostrar_pagina(1),lambda:self.mostrar_pagina(4))
        self.pagina_clientes = PaginaClientes(self.usuario.get('id'),self.usuario.get('version_sesion',1))
        self.pagina_clientes.boton_eliminar.setVisible(self.usuario['rol']=='ADMINISTRADOR')
        self.pagina_prestamos = PaginaPrestamos()
        self.pagina_cobros = PaginaCobros()
        self.pagina_reportes = PaginaReportes()
        self.pagina_usuarios = PaginaUsuarios()
        self.paginas = [
            self.pagina_inicio,
            self.pagina_clientes,
            self.pagina_prestamos,
            self.pagina_cobros,
            SimuladorPrestamo(),
            self.pagina_reportes,
            self.pagina_usuarios,
        ]
        if self.usuario["rol"] == "ADMINISTRADOR":
            from ui.employees import EmployeesPage
            self.pagina_empleados=EmployeesPage()
            self.paginas.append(self.pagina_empleados)
        for indice,pagina in enumerate(self.paginas):
            if indice in (0,4):
                scroll = QScrollArea()
                scroll.setObjectName('workspaceScroll')
                scroll.setWidgetResizable(True)
                scroll.setFrameShape(QFrame.NoFrame)
                scroll.setWidget(pagina)
                self.contenedor_paginas.addWidget(scroll)
            else:
                self.contenedor_paginas.addWidget(pagina)
        bind_theme(self,raiz)
        self.mostrar_pagina(0)

    def animar_transicion_pagina(self) -> None:
        # Keep the stack free of compositing effects: its child cards already
        # have shadows, which conflict with a persistent parent opacity effect.
        self.contenedor_paginas.currentWidget().update()

    def crear_barra_superior(self):
        return workspace_header(self)

    def mostrar_pagina(self, indice: int) -> None:
        if indice in (6,7) and self.usuario["rol"] != "ADMINISTRADOR": return
        self.breadcrumb.setText('Espacio de trabajo  /  '+['Resumen','Clientes','Préstamos','Cobros','Simulador','Reportes','Usuarios','Empleados'][indice])
        self.contenedor_paginas.setCurrentIndex(indice)
        self.animar_transicion_pagina()
        boton = self.grupo_navegacion.button(indice)
        if boton:
            boton.setChecked(True)
            self.navigation_scroll.ensureWidgetVisible(boton,0,8)
        if indice == 0:
            self.pagina_inicio.cargar_resumen()
        if indice == 1:
            self.pagina_clientes.cargar_clientes()
        if indice == 2:
            self.pagina_prestamos.cargar_prestamos()
        if indice == 3:
            self.pagina_cobros.cargar_cobros()
        if indice == 5:
            self.pagina_reportes.cargar_reporte()
        if indice == 6:
            if self.usuario["rol"] != "ADMINISTRADOR": return
            self.pagina_usuarios.cargar_usuarios()
        if indice == 7 and self.usuario["rol"] == "ADMINISTRADOR":
            self.pagina_empleados.cargar_empleados()

    def cerrar_sesion(self) -> None:
        establecer_actor(None)
        self.close()
        acceso = DialogoAcceso()
        if acceso.exec() == QDialog.Accepted:
            self.siguiente_ventana = PanelPrincipal(acceso.usuario)
            self.siguiente_ventana.show()
        else:
            QApplication.quit()

    def mostrar_aviso_cliente(self) -> None:
        QMessageBox.information(self, "Próximo paso", "Conectaremos este formulario a MySQL después de comprobar tu conexión.")

    def mostrar_aviso_prestamo(self) -> None:
        QMessageBox.information(self, "Próximo paso", "Primero registra un cliente; después emitiremos su préstamo y las cuotas francesas.")

    def mostrar_aviso_cobro(self) -> None:
        QMessageBox.information(self, "Próximo paso", "El registro de cobros se habilitará al conectar los datos de cuotas en MySQL.")

    def mostrar_aviso_reporte(self) -> None:
        QMessageBox.information(self, "Próximo paso", "Los reportes estarán disponibles cuando existan préstamos y pagos registrados.")


class PanelCliente(QMainWindow):
    def __init__(self, usuario: dict) -> None:
        super().__init__(); self.usuario = usuario; establecer_actor(usuario.get("id"),usuario.get("version_sesion",1)); self.setWindowTitle("CRECE + PRÉSTAMOS | Mi portal"); self.resize(1120, 700); self.setMinimumSize(940, 620)
        load_fonts()
        self.setObjectName('workspace')
        pagina = Scene(workspace=True)
        self.setCentralWidget(pagina)
        exterior = QVBoxLayout(pagina)
        exterior.setContentsMargins(28,24,28,24)
        exterior.setSpacing(20)
        encabezado = QHBoxLayout()
        self.titulo = workspace_label('Mi cuenta','workspaceTitle')
        encabezado.addWidget(self.titulo)
        encabezado.addStretch()
        encabezado.addWidget(theme_picker(self))
        encabezado.addWidget(workspace_button('Cerrar sesión',self.cerrar_sesion,False))
        exterior.addLayout(encabezado)
        self.resumen = workspace_label('Cargando información de cuenta...','surfaceTitle',True)
        exterior.addWidget(self.resumen)
        fila = QHBoxLayout()
        fila.addWidget(workspace_label('Mis cuotas programadas','surfaceTitle'))
        fila.addStretch()
        fila.addWidget(workspace_button('Informar pago realizado',self.abrir_solicitud_pago))
        exterior.addLayout(fila)
        superficie = workspace_surface()
        distribucion = QVBoxLayout(superficie)
        distribucion.setContentsMargins(1,1,1,1)
        self.tabla = DataTable(['PRÉSTAMO','CUOTA','VENCIMIENTO','CUOTA ORDINARIA','SALDO TOTAL','TASA DEL PERÍODO EQUIVALENTE (C$)','ESTADO','RECARGO PENDIENTE'])
        distribucion.addWidget(self.tabla,1)
        exterior.addWidget(superficie,1)
        bind_theme(self,pagina)
        self.cargar_datos()

    def cargar_datos(self) -> None:
        try:
            resumen = obtener_resumen_cliente(self.usuario["id"]); cuotas = listar_cuotas_cliente(self.usuario["id"])
        except (ValueError, ErrorConexionBaseDatos) as error:
            QMessageBox.warning(self, "Cuenta no disponible", str(error)); return
        self.titulo.setText(f"Hola, {resumen['nombre']}")
        self.resumen.setText(f"Saldo pendiente total: C${resumen['saldo']:,.2f}  ·  Cuotas pendientes: {resumen['pendientes']}")
        self.tabla.setRowCount(len(cuotas))
        for fila, cuota in enumerate(cuotas):
            valores = (f"PR-{cuota['prestamo_id']:05d}", f"#{cuota['numero_cuota']}", cuota['fecha_vencimiento'].strftime('%d/%m/%Y'), f"C${cuota['cuota_programada']:,.2f}", f"C${cuota['saldo']:,.2f}", f"C${cuota['interes']:,.2f}", cuota['estado'].title(),f"C${cuota.get('recargo_pendiente',0):,.2f}")
            for columna, valor in enumerate(valores): self.tabla.setItem(fila, columna, QTableWidgetItem(str(valor)))
            self.tabla.item(fila, 0).setData(Qt.UserRole, cuota)

    def abrir_solicitud_pago(self) -> None:
        fila = self.tabla.currentRow()
        if fila < 0: QMessageBox.information(self, "Selecciona una cuota", "Selecciona una cuota de la tabla antes de solicitar el pago."); return
        cuota = self.tabla.item(fila, 0).data(Qt.UserRole)
        dialogo = QDialog(self); dialogo.setWindowTitle("Solicitar pago"); dialogo.setMinimumWidth(390); distribucion = QVBoxLayout(dialogo)
        distribucion.addWidget(etiqueta(f"Cuota #{cuota['numero_cuota']} · saldo C${cuota['saldo']:,.2f}", "font-size: 17px; font-weight: 800;")); monto, referencia = QLineEdit(f"{cuota['saldo']:.2f}"), QLineEdit(); configurar_numero(monto,"monto"); referencia.setMaxLength(100); referencia.setPlaceholderText("Número de transferencia o referencia")
        formulario = QFormLayout(); formulario.addRow("Monto", monto); formulario.addRow("Referencia", referencia); distribucion.addLayout(formulario)
        comprobante={"contenido":None}
        adjuntar=boton_secundario("Adjuntar foto del comprobante")
        nombre_archivo=etiqueta("JPG, PNG o WebP; hasta 5 MB. Campo obligatorio.")
        distribucion.addWidget(adjuntar);distribucion.addWidget(nombre_archivo)
        def elegir_comprobante():
            from crece.servicios.comprobantes import MAX_COMPROBANTE,preparar_comprobante
            ruta,_=QFileDialog.getOpenFileName(dialogo,"Adjuntar comprobante","","Imágenes (*.jpg *.jpeg *.png *.webp)")
            if not ruta:return
            try:
                with open(ruta,"rb") as archivo:contenido=archivo.read(MAX_COMPROBANTE+1)
                preparar_comprobante(contenido)
            except (ValueError,OSError) as error:QMessageBox.warning(dialogo,"Comprobante inválido",str(error));return
            comprobante["contenido"]=contenido;nombre_archivo.setText(Path(ruta).name)
        adjuntar.clicked.connect(elegir_comprobante)
        enviar = QPushButton("Enviar solicitud"); distribucion.addWidget(enviar)
        def enviar_pago() -> None:
            try: solicitar_pago(self.usuario['id'], cuota['id'], leer_numero(monto,"monto"), referencia.text(),comprobante=comprobante["contenido"])
            except (ValueError, InvalidOperation, ErrorConexionBaseDatos) as error: QMessageBox.warning(dialogo, "No se pudo enviar", str(error)); return
            dialogo.accept(); QMessageBox.information(self, "Solicitud enviada", "Un empleado verificará tu pago antes de aplicarlo.")
        enviar.clicked.connect(enviar_pago); dialogo.exec()

    def cerrar_sesion(self) -> None:
        self.close(); QApplication.quit()


def ejecutar_aplicacion() -> int:
    aplicacion = QApplication([])
    aplicacion.setStyleSheet(ESTILO_APLICACION)
    aplicacion.setFont(QFont("Open Sans", 10))
    acceso = DialogoAcceso()
    if acceso.exec() != QDialog.Accepted:
        return 0
    ventana = PanelCliente(acceso.usuario) if acceso.usuario["rol"] == "CLIENTE" else PanelPrincipal(acceso.usuario)
    ventana.show()
    return aplicacion.exec()
