"""Preferencia de apariencia compartida por las ventanas nativas."""
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QSettings, Qt
from PySide6.QtGui import QPalette, QColor, QPixmap, QRegion
from PySide6.QtWidgets import QComboBox, QLabel, QPushButton, QLineEdit

ROOT = Path(__file__).resolve().parents[1]
_controller = None


class Appearance(QObject):
    changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.settings = QSettings('CRECE Prestamos', 'Apariencia')
        self.theme = self.settings.value('theme', 'dark', str)
        if self.theme not in ('light', 'dark'):
            self.theme = 'dark'

    def set_theme(self, theme):
        if theme not in ('light', 'dark') or theme == self.theme:
            return
        self.theme = theme
        self.settings.setValue('theme', theme)
        self.settings.sync()
        self.changed.emit(theme)


def appearance():
    global _controller
    if _controller is None:
        _controller = Appearance()
    return _controller


def theme_picker(parent):
    picker = QComboBox(parent)
    picker.setObjectName('appearancePicker')
    picker.setAccessibleName('Tema de apariencia')
    picker.setToolTip('Cambiar entre fondo claro y oscuro')
    picker.addItem('Claro', 'light')
    picker.addItem('Oscuro', 'dark')
    picker.setCurrentIndex(picker.findData(appearance().theme))
    picker.currentIndexChanged.connect(lambda _: appearance().set_theme(picker.currentData()))
    def reflect(theme):
        picker.blockSignals(True)
        picker.setCurrentIndex(picker.findData(theme))
        picker.blockSignals(False)
    appearance().changed.connect(reflect)
    # Context-bound connection is removed automatically with the widget.
    picker.destroyed.connect(lambda: _disconnect(reflect))
    return picker


def _disconnect(callback):
    try:
        appearance().changed.disconnect(callback)
    except (RuntimeError, TypeError):
        pass


class ThemeBinding(QObject):
    def __init__(self, window, scene, auth=False):
        super().__init__(window)
        self.window, self.scene, self.auth = window, scene, auth
        appearance().changed.connect(self.apply)
        self.apply(appearance().theme)

    def apply(self, theme):
        from ui.widgets.premium import ASSETS, symbol
        dark = theme == 'dark'
        self.window.setProperty('appearance', theme)
        self.scene.set_theme(theme)
        base = 'theme.qss' if self.auth else 'workspace.qss'
        css = (ROOT / 'styles' / base).read_text(encoding='utf-8')
        css += '\n' + (ROOT / 'styles' / ('appearance-dark.qss' if dark else 'appearance-light.qss')).read_text(encoding='utf-8')
        self.window.setStyleSheet(css.replace('__ASSETS__', ASSETS.as_posix()))
        palette = QPalette(self.window.palette())
        for role, value in [(QPalette.Window,'#001F3F' if dark else '#EBF9F1'),
                            (QPalette.Base,'#001F3F' if dark else '#FFFFFF'),
                            (QPalette.AlternateBase,'#003366' if dark else '#EBF9F1'),
                            (QPalette.Text,'#FFFFFF' if dark else '#001F3F'),
                            (QPalette.WindowText,'#FFFFFF' if dark else '#003366'),
                            (QPalette.ButtonText,'#FFFFFF' if dark else '#003366'),
                            (QPalette.PlaceholderText,'#BFD2DF' if dark else '#666666'),
                            (QPalette.Highlight,'#006633'),(QPalette.HighlightedText,'#FFFFFF')]:
            palette.setColor(role,QColor(value))
        self.window.setPalette(palette)
        for nav in self.window.findChildren(QPushButton):
            name = nav.property('appearanceIcon')
            if name:
                nav.setIcon(symbol(name,'#FFFFFF' if dark or nav.property('appearancePrimary') else '#003366',19))
        for mark in self.window.findChildren(QLabel):
            name = mark.property('appearanceSymbol')
            if name:
                mark.setPixmap(symbol(name,'#B0E3CA' if dark else '#006633',20).pixmap(20,20))
        brand = self.window.findChild(QLabel,'appearanceBrand')
        if brand:
            path = ASSETS / 'logo-oscuro.png' if dark else ROOT / 'assets/logo_horizontal_crece.png'
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                pixmap = pixmap.copy(QRegion(pixmap.mask()).boundingRect())
                brand.setPixmap(pixmap.scaledToWidth(164,Qt.SmoothTransformation))
        # Input icons remain readable on both surfaces; their geometry never changes.
        for field in self.window.findChildren(QLineEdit):
            icon = field.property('appearanceIcon') or ('search' if field.objectName() == 'workspaceSearch' else None)
            if icon and field.actions():
                field.actions()[0].setIcon(symbol(icon,'#FFFFFF' if dark else '#003366'))
            if hasattr(field,'toggle_action'):
                field.toggle_action.setIcon(symbol('eye','#FFFFFF' if dark else '#003366'))
        self.window.update()


def bind_theme(window, scene, auth=False):
    window.appearance_binding = ThemeBinding(window, scene, auth)
