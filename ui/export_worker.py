"""Exportación cancelable fuera del hilo gráfico, con publicación atómica."""
import os
import tempfile
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from crece.infraestructura.exportadores import exportar_pdf, exportar_excel


class ExportacionCancelada(Exception):
    pass


def guardar_atomico(reporte, destino, formato, progreso=None, cancelado=None):
    destino = Path(destino)
    def avanzar(porcentaje):
        if cancelado and cancelado():
            raise ExportacionCancelada()
        if progreso:
            progreso(porcentaje)
    descriptor, temporal = tempfile.mkstemp(prefix='.crece-', suffix='.' + formato, dir=destino.parent)
    os.close(descriptor)
    try:
        avanzar(0)
        (exportar_pdf if formato == 'pdf' else exportar_excel)(reporte, temporal, avanzar)
        avanzar(99)
        os.replace(temporal, destino)
        if progreso:
            progreso(100)
    finally:
        if os.path.exists(temporal):
            os.unlink(temporal)
    return str(destino)


class ExportWorker(QThread):
    progreso = Signal(int)
    completado = Signal(str)
    fallo = Signal(str)
    cancelado = Signal()

    def __init__(self, reporte, destino, formato, parent=None):
        super().__init__(parent)
        self.reporte, self.destino, self.formato = reporte, destino, formato

    def run(self):
        try:
            resultado = guardar_atomico(self.reporte, self.destino, self.formato,
                                        self.progreso.emit, self.isInterruptionRequested)
            self.completado.emit(resultado)
        except ExportacionCancelada:
            self.cancelado.emit()
        except Exception:
            self.fallo.emit('No se pudo guardar el reporte. Revisa el espacio disponible, los permisos y que el archivo no esté abierto.')
