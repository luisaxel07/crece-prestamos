"""Vista previa del PDF oficial: mismo diseño en pantalla, archivo e impresora."""
from pathlib import Path
from tempfile import TemporaryDirectory
from PySide6.QtCore import Qt, QPointF, QSize, QRectF, QTimer, QBuffer, QIODevice
from PySide6.QtGui import QPainter, QPageLayout, QPageSize
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtPrintSupport import QPrinter, QPrintDialog, QAbstractPrintDialog
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QSpinBox, QMessageBox, QProgressDialog, QApplication)
from ui.workspace import label, button
from ui.export_worker import ExportWorker


def paginas_de_impresion(printer, total, actual=0):
    if printer.printRange() == QPrinter.CurrentPage:
        pages = [max(0, min(actual, total-1))]
    elif printer.printRange() == QPrinter.PageRange:
        start, end = max(1, printer.fromPage()), min(total, printer.toPage())
        pages = list(range(start-1, end))
    else:
        pages = list(range(total))
    if printer.pageOrder() == QPrinter.LastPageFirst:
        pages.reverse()
    copies = 1 if printer.supportsMultipleCopies() else max(1, printer.copyCount())
    if printer.collateCopies():
        return pages * copies
    return [page for page in pages for _ in range(copies)]


def imprimir_pdf(document, printer, actual=0, progreso=None):
    """Dibuja páginas completas sin redistribuir tablas ni depender del DPI del texto."""
    pages = paginas_de_impresion(printer, document.pageCount(), actual)
    if not pages:
        raise ValueError('El rango seleccionado no contiene páginas.')
    painter = QPainter()
    if not painter.begin(printer):
        raise OSError('No se pudo iniciar la impresora seleccionada.')
    try:
        for index, page in enumerate(pages):
            if progreso and progreso(index, len(pages)) is False:
                printer.abort()
                return False
            if index and not printer.newPage():
                raise OSError('La impresora no pudo continuar a la siguiente página.')
            size = document.pagePointSize(page)
            # Renderizar una página a la vez a 300 ppp evita imágenes enormes a 1200 ppp.
            image = document.render(page, QSize(round(size.width()*300/72), round(size.height()*300/72)))
            if image.isNull():
                raise OSError('No se pudo preparar una de las páginas.')
            area = QRectF(printer.pageRect(QPrinter.DevicePixel))
            scale = min(area.width()/image.width(), area.height()/image.height())
            target = QRectF(0, 0, image.width()*scale, image.height()*scale)
            target.moveCenter(area.center())
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            painter.fillRect(area, Qt.white)
            painter.drawImage(target, image)
        return True
    except Exception:
        printer.abort()
        raise
    finally:
        painter.end()


class PrintPreviewDialog(QDialog):
    def __init__(self, reporte, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Vista previa e impresión | CRECE+ PRÉSTAMOS')
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinMaxButtonsHint)
        self.resize(1280, 880)
        self.setMinimumSize(880, 600)
        if parent:
            self.setProperty('appearance', parent.window().property('appearance'))
        self.reporte = reporte
        self.temporal = TemporaryDirectory(prefix='crece-impresion-')
        self.archivo = Path(self.temporal.name) / 'reporte.pdf'
        self.worker = None
        self.cierre_pendiente = False
        self.imprimiendo = False
        self.documento = QPdfDocument(self)
        self.documento.statusChanged.connect(self.estado_documento)
        self.buffer = QBuffer(self)
        box = QVBoxLayout(self)
        box.setContentsMargins(18, 16, 18, 16)
        box.addWidget(label('Vista previa de impresión', 'workspaceTitle'))
        self.estado = label('Preparando el documento con el logotipo y el plan de cuotas…', wrap=True)
        box.addWidget(self.estado)
        controls = QHBoxLayout()
        self.imprimir_button = button('Imprimir…', self.imprimir)
        self.imprimir_button.setEnabled(False)
        controls.addWidget(self.imprimir_button)
        self.anterior = button('Anterior', lambda: self.ir_pagina(self.pagina.value()-1), False)
        self.siguiente = button('Siguiente', lambda: self.ir_pagina(self.pagina.value()+1), False)
        controls.addWidget(self.anterior)
        self.pagina = QSpinBox()
        self.pagina.setAccessibleName('Número de página')
        self.pagina.setStyleSheet('QSpinBox, QSpinBox QLineEdit { background: #FFFFFF; color: #003366; } QSpinBox { border: 1px solid #94ADA4; border-radius: 6px; padding: 8px; min-width: 100px; }')
        self.pagina.setPrefix('Página ')
        self.pagina.setRange(1, 1)
        self.pagina.valueChanged.connect(self.ir_pagina)
        controls.addWidget(self.pagina)
        self.cantidad = label('de —')
        controls.addWidget(self.cantidad)
        controls.addWidget(self.siguiente)
        controls.addStretch()
        self.zoom = QComboBox()
        self.zoom.setAccessibleName('Ampliación de la vista previa')
        for text, value in [('Ajustar al ancho', 'width'), ('Página completa', 'page'),
                            ('75 %', .75), ('100 %', 1.), ('125 %', 1.25), ('150 %', 1.5), ('200 %', 2.)]:
            self.zoom.addItem(text, value)
        self.zoom.currentIndexChanged.connect(self.cambiar_zoom)
        controls.addWidget(self.zoom)
        box.addLayout(controls)
        self.vista = QPdfView(self)
        self.vista.setDocument(self.documento)
        self.vista.setPageMode(QPdfView.PageMode.SinglePage)
        self.vista.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self.vista.setStyleSheet('QPdfView { background: #D9E4E1; border: 1px solid #94ADA4; }')
        self.vista.pageNavigator().currentPageChanged.connect(self.reflejar_pagina)
        box.addWidget(self.vista, 1)
        footer = QHBoxLayout()
        footer.addWidget(label('El zoom solo cambia la vista. Imprimir… permite elegir impresora, páginas y copias.', wrap=True), 1)
        footer.addWidget(button('Cerrar', self.reject, False))
        box.addLayout(footer)
        self.anterior.setEnabled(False)
        self.siguiente.setEnabled(False)
        for control in (self.anterior,self.siguiente):
            control.setStyleSheet('QPushButton:disabled { color: #94ADA4; border-color: #547182; }')
        QTimer.singleShot(0, self.preparar)

    def preparar(self):
        if self.cierre_pendiente:
            return
        self.worker = ExportWorker(self.reporte, str(self.archivo), 'pdf', self)
        self.worker.progreso.connect(lambda value: self.estado.setText(f'Preparando documento… {value} %'))
        self.worker.completado.connect(self.cargar)
        self.worker.fallo.connect(self.error)
        self.worker.finished.connect(self.preparacion_terminada)
        self.worker.start()

    def cargar(self, path):
        # El visor trabaja en memoria: sus tareas de render no retienen el archivo
        # temporal bloqueado en Windows al cerrar la ventana.
        self.buffer.setData(Path(path).read_bytes())
        self.buffer.open(QIODevice.ReadOnly)
        self.documento.load(self.buffer)

    def estado_documento(self, status):
        # QIODevice puede cargar de forma asíncrona. No confundir Loading con error.
        if status == QPdfDocument.Status.Error:
            self.error('No se pudo abrir la vista previa del documento.')
            return
        if status != QPdfDocument.Status.Ready:
            return
        count = self.documento.pageCount()
        if not count:
            self.error('No se pudo abrir la vista previa del documento.')
            return
        self.estado.setText(f'A4 horizontal · {count} página(s) · {self.reporte["titulo"]}')
        self.cantidad.setText(f'de {count}')
        self.pagina.setMaximum(count)
        self.imprimir_button.setEnabled(True)
        self.reflejar_pagina(0)

    def error(self, message):
        self.estado.setText(message)
        self.imprimir_button.setEnabled(False)

    def preparacion_terminada(self):
        self.worker.deleteLater()
        self.worker = None
        if self.cierre_pendiente:
            self.done(QDialog.Rejected)

    def cambiar_zoom(self, *_):
        value = self.zoom.currentData()
        if value in ('width', 'page'):
            self.vista.setZoomMode(QPdfView.ZoomMode.FitToWidth if value == 'width' else QPdfView.ZoomMode.FitInView)
        else:
            self.vista.setZoomMode(QPdfView.ZoomMode.Custom)
            self.vista.setZoomFactor(value)

    def ir_pagina(self, number):
        if 1 <= number <= self.documento.pageCount():
            self.vista.pageNavigator().jump(number-1, QPointF())

    def reflejar_pagina(self, index):
        self.pagina.blockSignals(True)
        self.pagina.setValue(index+1)
        self.pagina.blockSignals(False)
        self.anterior.setEnabled(index > 0)
        self.siguiente.setEnabled(index+1 < self.documento.pageCount())

    def imprimir(self):
        if not self.documento.pageCount() or self.imprimiendo:
            return
        printer = QPrinter(QPrinter.HighResolution)
        printer.setResolution(300)
        printer.setPageSize(QPageSize(QPageSize.A4))
        printer.setPageOrientation(QPageLayout.Landscape)
        printer.setDocName(self.reporte['titulo'])
        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle('Elegir impresora y páginas | CRECE+ PRÉSTAMOS')
        dialog.setMinMax(1, self.documento.pageCount())
        dialog.setFromTo(1, self.documento.pageCount())
        dialog.setOption(QAbstractPrintDialog.PrintPageRange, True)
        dialog.setOption(QAbstractPrintDialog.PrintCurrentPage, True)
        if dialog.exec() != QDialog.Accepted:
            return
        printer.setPageOrientation(QPageLayout.Landscape)
        progress = QProgressDialog('Preparando impresión…', 'Cancelar', 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        def avanzar(index, total):
            progress.setLabelText(f'Enviando página {index+1} de {total}…')
            QApplication.processEvents()
            return not progress.wasCanceled()
        self.imprimiendo = True
        try:
            if imprimir_pdf(self.documento, printer, self.pagina.value()-1, avanzar):
                self.estado.setText('Documento enviado a la impresora seleccionada.')
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, 'No se pudo imprimir', str(error))
        finally:
            progress.close()
            self.imprimiendo = False

    def done(self, result):
        if self.imprimiendo:
            return
        self.cierre_pendiente = True
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
            return
        self.vista.setDocument(None)
        self.documento.close()
        self.buffer.close()
        self.temporal.cleanup()
        super().done(result)
