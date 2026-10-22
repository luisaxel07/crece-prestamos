"""Visor privado del comprobante: no utiliza carpetas públicas ni servicios externos."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QScrollArea,QFileDialog,QMessageBox
from ui.workspace import button,label

class ComprobanteDialog(QDialog):
    def __init__(self,datos,parent=None):
        super().__init__(parent)
        if parent:self.setProperty('appearance',parent.window().property('appearance'))
        self.datos=datos;self.factor=1;self.ajustado=True
        self.setWindowTitle('Comprobante de pago | CRECE+ PRÉSTAMOS');self.resize(920,740)
        box=QVBoxLayout(self);box.addWidget(label('Comprobante de pago','workspaceTitle'))
        box.addWidget(label('Compara el monto, la referencia y el ingreso en la cuenta antes de confirmar.',wrap=True))
        controls=QHBoxLayout()
        controls.addWidget(button('Ajustar al ancho',self.ajustar,False));controls.addWidget(button('Zoom −',lambda:self.zoom(.8),False));controls.addWidget(button('Zoom +',lambda:self.zoom(1.25),False));controls.addStretch();controls.addWidget(button('Guardar imagen',self.guardar,False));box.addLayout(controls)
        self.original=QPixmap()
        if not self.original.loadFromData(datos['contenido']):raise ValueError('No se pudo mostrar el comprobante.')
        self.imagen=QLabel();self.imagen.setAlignment(Qt.AlignCenter);self.imagen.setAccessibleName('Foto del comprobante adjunto')
        self.scroll=QScrollArea();self.scroll.setAlignment(Qt.AlignCenter);self.scroll.setWidget(self.imagen)
        box.addWidget(self.scroll,1);box.addWidget(button('Cerrar',self.accept,False));self.ajustar()
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'original') and self.ajustado:self.ajustar()
    def ajustar(self):
        self.ajustado=True;self.factor=min(1,max(100,self.scroll.viewport().width()-24)/self.original.width());self.pintar()
    def zoom(self,multiplicador):
        self.ajustado=False;self.factor=min(3,max(.1,self.factor*multiplicador));self.pintar()
    def pintar(self):
        scaled=self.original.scaled(max(1,int(self.original.width()*self.factor)),max(1,int(self.original.height()*self.factor)),Qt.KeepAspectRatio,Qt.SmoothTransformation)
        self.imagen.setPixmap(scaled);self.imagen.resize(scaled.size())
    def guardar(self):
        ruta,_=QFileDialog.getSaveFileName(self,'Guardar comprobante',self.datos['nombre'],'Imagen JPEG (*.jpg)')
        if not ruta:return
        try:
            from pathlib import Path
            Path(ruta).write_bytes(self.datos['contenido'])
        except OSError:QMessageBox.warning(self,'No se pudo guardar','Comprueba la carpeta elegida e inténtalo otra vez.')
