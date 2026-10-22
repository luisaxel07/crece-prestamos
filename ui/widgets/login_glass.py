"""Cristal del panel de login; no modifica otros diálogos ni el fondo."""
from PySide6.QtCore import Qt, QPoint, QPointF, QRectF
from PySide6.QtGui import QPainter, QPainterPath, QColor, QLinearGradient, QPen, QBrush
from ui.widgets.premium import GlassCard


class LoginGlassCard(GlassCard):
    def __init__(self, scene):
        super().__init__(scene)
        self.graphicsEffect().setColor(QColor(0,31,63,36))

    def paintEvent(self, event):
        painter=QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        bounds=QRectF(self.rect()).adjusted(.5,.5,-.5,-.5)
        clip=QPainterPath()
        clip.addRoundedRect(bounds,28,28)
        painter.setClipPath(clip)
        origin=self.mapTo(self.scene,QPoint())
        painter.drawPixmap(-origin.x(),-origin.y(),self.scene.blurred)
        # Align the existing scene's color layer with the cached, blurred photo.
        overlay=QLinearGradient(-origin.x(),0,self.scene.width()-origin.x(),0)
        dark=self.scene.theme=='dark'
        if dark:
            stops=[(0,QColor(0,31,63,220)),(.5,QColor(0,31,63,145)),(1,QColor(0,31,63,95))]
        else:
            stops=[(0,QColor(224,245,234,230)),(.5,QColor(224,245,234,175)),(1,QColor(255,255,255,90))]
        for position,color in stops:
            overlay.setColorAt(position,color)
        painter.fillPath(clip,overlay)
        painter.fillPath(clip,QColor(0,31,63,87) if dark else QColor(255,255,255,71))
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QColor(255,255,255,143 if dark else 163))
        painter.drawRoundedRect(bounds,28,28)
        light=QLinearGradient(0,0,self.width(),0)
        light.setColorAt(0,QColor(255,255,255,0))
        light.setColorAt(.5,QColor(255,255,255,220))
        light.setColorAt(1,QColor(255,255,255,0))
        painter.setPen(QPen(QBrush(light),1))
        painter.drawLine(QPointF(20,1),QPointF(self.width()-20,1))
