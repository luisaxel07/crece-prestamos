from pathlib import Path
import os
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QPropertyAnimation, QEasingCurve, QRectF
from PySide6.QtGui import QPainter, QPainterPath, QColor, QPixmap, QIcon, QFont, QFontDatabase
from PySide6.QtWidgets import (QFrame, QLineEdit, QGraphicsBlurEffect, QGraphicsScene,
                              QGraphicsOpacityEffect, QGraphicsDropShadowEffect, QLabel)

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'portal_web/static/auth/assets'
BLUE, GREEN, NIGHT, DARK_GREEN, GRAY = '#003366', '#00A651', '#001F3F', '#006633', '#666666'


def reduced_motion():
    if os.environ.get('CRECE_REDUCED_MOTION') == '1':
        return True
    if os.name == 'nt':
        import ctypes
        enabled = ctypes.c_int(1)
        ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(enabled), 0)
        return not enabled.value
    return False


def load_fonts():
    for path in (ROOT / 'assets/fonts').glob('*.ttf'):
        QFontDatabase.addApplicationFont(str(path))


def title_font(size=20):
    font = QFont('Montserrat', size, QFont.Bold)
    font.setFamilies(['Montserrat', 'Segoe UI', 'sans-serif'])
    return font


def symbol(name, color=BLUE, size=24):
    # Interface icons only. Brand marks always use the supplied original PNGs.
    from PySide6.QtSvg import QSvgRenderer
    paths = {
        'grid': '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
        'users': '<circle cx="9" cy="7" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3M16 4a3 3 0 0 1 0 6m2 5a5 5 0 0 1 3 5"/>',
        'coins': '<ellipse cx="9" cy="5" rx="6" ry="3"/><path d="M3 5v5c0 4 12 4 12 0V5M3 10v5c0 3 6 4 10 2M16 11c7-1 8 7 4 9-4 2-8-1-7-5"/>',
        'calculator': '<rect x="5" y="2" width="14" height="20" rx="2"/><path d="M8 6h8M8 11h1m6 0h1M8 15h1m6 0h1M8 19h1m6 0h1"/>',
        'chart': '<path d="M3 3v18h18M7 16l4-5 4 2 5-7"/>',
        'search': '<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/>',
        'logout': '<path d="M10 3H4v18h6M8 12h13m-5-5 5 5-5 5"/>',
        'user': '<circle cx="12" cy="7" r="4"/><path d="M4 22v-3a8 8 0 0 1 16 0v3"/>',
        'lock': '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V6a4 4 0 0 1 8 0v4M12 14v3"/>',
        'eye': '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
        'arrow': '<path d="M4 12h16m-6-6 6 6-6 6"/>',
        'shield': '<path d="m12 2 8 4v6c0 5-8 10-8 10S4 17 4 12V6Z"/><path d="m8 12 3 3 5-6"/>',
        'document': '<path d="M14 2H5v20h14V7Z"/><path d="M14 2v6h5M8 12h8M8 16h6"/>',
        'growth': '<path d="M4 20v-4m6 4v-8m6 8V8M3 11l7-6 5 2 6-5m-5 0h5v5"/>',
        'mail': '<rect x="2" y="4" width="20" height="16" rx="3"/><path d="m3 6 9 7 9-7"/>'
    }
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{paths[name]}</svg>'
    pixmap = QPixmap(size * 2, size * 2)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    QSvgRenderer(svg.encode()).render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(2)
    return QIcon(pixmap)


class Field(QLineEdit):
    def __init__(self, placeholder, name, password=False, icon='user'):
        super().__init__()
        self.setObjectName('authField')
        self.setProperty('premiumAuth',True)
        self.setPlaceholderText(placeholder)
        self.setAccessibleName(name)
        self.setMinimumHeight(60)
        self.setMaxLength(128 if password else 254)
        from ui.appearance import appearance
        self.setProperty('appearanceIcon',icon)
        color = '#FFFFFF' if appearance().theme == 'dark' else BLUE
        self.addAction(symbol(icon,color), QLineEdit.LeadingPosition)
        if password:
            self.setEchoMode(QLineEdit.Password)
            self.toggle_action = self.addAction(symbol('eye',color), QLineEdit.TrailingPosition)
            self.toggle_action.setCheckable(True)
            self.toggle_action.setText('Mostrar contraseña')
            self.toggle_action.setToolTip('Mostrar contraseña')
            self.toggle_action.toggled.connect(self.toggle_password)

    def toggle_password(self, visible):
        self.setEchoMode(QLineEdit.Normal if visible else QLineEdit.Password)
        self.toggle_action.setText('Ocultar contraseña' if visible else 'Mostrar contraseña')
        self.toggle_action.setToolTip(self.toggle_action.text())


class Task(QThread):
    result = Signal(object)
    failed = Signal(str)

    def __init__(self, callback, parent):
        super().__init__(parent)
        self.callback = callback

    def run(self):
        try:
            self.result.emit(self.callback())
        except Exception as error:
            # Only validation and known connectivity messages may reach the user.
            from crece.servicios.clientes import ErrorConexionBaseDatos
            message = str(error) if isinstance(error, (ValueError, ErrorConexionBaseDatos)) else 'El servicio no está disponible en este momento. Intenta más tarde.'
            self.failed.emit(message)
        finally:
            self.callback = None


class Scene(QFrame):
    def __init__(self, parent=None, workspace=False):
        super().__init__(parent)
        self.workspace = workspace
        self.theme = 'dark'
        self.original = QPixmap()
        self.background = QPixmap()
        self.blurred = QPixmap()
        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.refresh_background)

    def set_theme(self, theme):
        self.theme = theme
        filename = 'fondo_portal_mediodia.png' if theme == 'light' else 'fondo_portal_premium.png'
        self.original = QPixmap(str(ROOT / 'portal_web/static/images' / filename))
        self.refresh_background()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resize_timer.start(80)

    def refresh_background(self):
        if self.original.isNull():
            return
        image = self.original.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        image = image.copy((image.width()-self.width())//2, (image.height()-self.height())//2, self.width(), self.height())
        self.background = image
        if self.workspace:
            self.update()
            return
        scene = QGraphicsScene()
        item = scene.addPixmap(image)
        effect = QGraphicsBlurEffect()
        effect.setBlurRadius(22)
        item.setGraphicsEffect(effect)
        scene.setSceneRect(QRectF(image.rect()))
        self.blurred = QPixmap(image.size())
        self.blurred.fill(Qt.transparent)
        painter = QPainter(self.blurred)
        scene.render(painter)
        painter.end()
        self.update()
        for card in self.findChildren(GlassCard):
            card.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(NIGHT))
        if not self.background.isNull():
            painter.drawPixmap(self.rect(), self.background)
        from PySide6.QtGui import QLinearGradient
        overlay = QLinearGradient(0, 0, self.width(), 0)
        if self.theme == 'light':
            overlay.setColorAt(0, QColor(224,245,234,230))
            overlay.setColorAt(.5, QColor(224,245,234,175))
            overlay.setColorAt(1, QColor(255,255,255,90))
        else:
            overlay.setColorAt(0, QColor(0,31,63,220))
            overlay.setColorAt(.5, QColor(0,31,63,145))
            overlay.setColorAt(1, QColor(0,31,63,95))
        painter.fillRect(self.rect(), overlay)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QColor(0,166,81,110))
        curve = QPainterPath()
        curve.moveTo(self.width()*.55,self.height())
        curve.cubicTo(self.width()*.75,self.height()*.82,self.width()*.9,self.height(),self.width(),self.height()*.77)
        painter.drawPath(curve)


class GlassCard(QFrame):
    def __init__(self, scene):
        super().__init__()
        self.scene = scene
        self.setObjectName('glassCard')
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(45)
        shadow.setOffset(0,14)
        shadow.setColor(QColor(0,31,63,65))
        self.setGraphicsEffect(shadow)

    def paintEvent(self, event):
        from PySide6.QtCore import QPoint
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        bounds = QRectF(self.rect()).adjusted(.5,.5,-.5,-.5)
        clip = QPainterPath()
        clip.addRoundedRect(bounds,24,24)
        painter.setClipPath(clip)
        origin = self.mapTo(self.scene, QPoint(0,0))
        painter.drawPixmap(-origin.x(),-origin.y(),self.scene.blurred)
        painter.fillPath(clip,QColor(0,31,63,233) if self.scene.theme == 'dark' else QColor(235,249,241,228))
        curve = QPainterPath()
        curve.moveTo(0,self.height())
        curve.quadTo(self.width()*.8,self.height(),self.width(),self.height()-130)
        curve.lineTo(self.width(),self.height())
        painter.fillPath(curve,QColor(0,166,81,18))
        painter.setPen(QColor(255,255,255,190))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(bounds,24,24)


def brand_label(width=144, dark=False):
    label = QLabel()
    label.setAccessibleName('CRECE+ PRÉSTAMOS')
    pix = QPixmap(str(ASSETS / ('logo-oscuro.png' if dark else 'logo-vertical.png')))
    scaled = pix.scaledToWidth(width, Qt.SmoothTransformation)
    label.setPixmap(scaled)
    # The clear space is part of the widget, not an effect on the logo.
    margin = round(width/4) if not dark else round(width*2/13)
    label.setContentsMargins(margin,margin,margin,margin)
    label.setFixedSize(width+2*margin,scaled.height()+2*margin)
    label.setAlignment(Qt.AlignCenter)
    return label


def fade(widget, delay=0):
    if reduced_motion():
        return
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(0)
    widget.setGraphicsEffect(effect)
    animation = QPropertyAnimation(effect,b'opacity',widget)
    animation.setDuration(400)
    animation.setStartValue(0.)
    animation.setEndValue(1.)
    animation.setEasingCurve(QEasingCurve.OutCubic)
    widget._entrance = animation
    QTimer.singleShot(delay,animation.start)
