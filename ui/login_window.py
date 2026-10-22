from PySide6.QtCore import Qt, QTimer, QSettings
from PySide6.QtGui import QPixmap, QRegion, QPalette, QColor
from PySide6.QtWidgets import QLabel
from ui.access_dialog import AccessDialog
from ui.widgets.premium import Field, ROOT, ASSETS
from ui.appearance import appearance


class LoginWindow(AccessDialog):
    def __init__(self, parent=None, service=None):
        super().__init__(parent,service,minimal_login=True)
        self.usuario = None
        self.setup_mode = None
        self.submit_text = 'Iniciar sesión'
        self.username = self.add_field('Usuario o correo electrónico',Field('Usuario o correo electrónico','Usuario o correo electrónico'))
        self.password = self.add_field('Contraseña',Field('Contraseña','Contraseña',True,'lock'))
        self.confirm_label = QLabel('Confirmar contraseña')
        self.confirm = Field('Repite tu contraseña','Confirmar contraseña',True,'lock')
        self.confirm_label.setBuddy(self.confirm)
        self.form.addWidget(self.confirm_label)
        self.form.addWidget(self.confirm)
        self.confirm.hide()
        self.confirm_label.hide()
        self.settings = QSettings('CRECE Prestamos','Acceso')
        self.username.setText(self.settings.value('remembered_user','',str))
        self.help_links=QLabel()
        self.help_links.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.help_links.setAlignment(Qt.AlignCenter)
        self.help_links.setWordWrap(True)
        self.help_links.setAccessibleName('Recuperar acceso o solicitar una cuenta')
        self.help_links.linkActivated.connect(lambda destino:self.open_recovery() if destino=='recuperar' else self.open_register())
        self.links.addWidget(self.help_links)
        appearance().changed.connect(self.apply_login_theme)
        self.apply_login_theme(appearance().theme)
        self.submit.clicked.connect(self.authenticate)
        self.password.returnPressed.connect(self.authenticate)
        self.confirm.returnPressed.connect(self.authenticate)
        self.username.returnPressed.connect(self.password.setFocus)
        QTimer.singleShot(0,self.check_setup)

    def apply_login_theme(self, theme):
        dark = theme == 'dark'
        css = (ROOT / 'styles/login.qss').read_text(encoding='utf-8')
        values = {
            '__FIELD_BACKGROUND__': 'rgba(0,31,63,77)' if dark else 'rgba(255,255,255,138)',
            '__TEXT__': '#FFFFFF' if dark else '#001F3F',
            '__BORDER__': 'rgba(255,255,255,143)' if dark else 'rgba(255,255,255,204)',
        }
        for name,value in values.items():
            css = css.replace(name,value)
        self.card.setStyleSheet(css)
        color='#FFFFFF' if dark else '#003366'
        self.help_links.setText(f'<br><a style="color:{color};font-size:11px" href="recuperar">¿Olvidaste tu contraseña?</a><br><a style="color:{color};font-size:11px" href="registro">Solicita tu acceso</a>')
        for field in (self.username,self.password,self.confirm):
            palette = field.palette()
            palette.setColor(QPalette.PlaceholderText,QColor('#E1EAF1' if dark else '#365F79'))
            field.setPalette(palette)
        pixmap = QPixmap(str(ASSETS / ('logo-oscuro.png' if dark else 'logo-vertical.png')))
        if dark:
            pixmap = pixmap.copy(QRegion(pixmap.mask()).boundingRect())
        self.logo.setPixmap(pixmap.scaledToWidth(160 if dark else 144,Qt.SmoothTransformation))
        self.logo.setContentsMargins(28 if dark else 36,36,28 if dark else 36,36)
        self.card.update()

    def check_setup(self):
        self.start_job(self.service.setup_required,self.setup_checked)

    def setup_checked(self, required):
        self.setup_mode = required
        self.confirm.setVisible(required)
        self.confirm_label.setVisible(required)
        self.heading.setVisible(required)
        self.subtitle.setVisible(required)
        if required:
            self.heading.setText('Configura tu administrador')
            self.subtitle.setText('Crea la cuenta principal del sistema. Usa una contraseña de al menos 12 caracteres.')
            self.submit_text = 'Crear administrador'
        self.submit.setText(self.submit_text)
        self.username.setFocus()

    def authenticate(self):
        if self.busy:
            return
        if self.setup_mode is None:
            self.check_setup()
            return
        username, password = self.username.text().strip(), self.password.text()
        if not username or not password:
            self.show_error('Completa el usuario y la contraseña.')
            (self.username if not username else self.password).setFocus()
            return
        if self.setup_mode and (len(username)<4 or len(password)<12 or password!=self.confirm.text()):
            self.show_error('Usa al menos 4 caracteres para el usuario y 12 para la contraseña. Ambas contraseñas deben coincidir.')
            return
        def authenticated(user):
            if not isinstance(user,dict) or not user.get('id') or user.get('rol') not in ('ADMINISTRADOR','EMPLEADO'):
                self.show_error('El servidor no confirmó un acceso administrativo válido.')
                return
            self.usuario = user
            self.accept()
        method = self.service.setup if self.setup_mode else self.service.login
        self.start_job(lambda: method(username,password),authenticated)

    def open_register(self):
        if not self.busy:
            from ui.register_window import RegisterWindow
            RegisterWindow(self,self.service).exec()

    def open_recovery(self):
        if not self.busy:
            from ui.recovery_dialog import RecoveryDialog
            RecoveryDialog(self,self.service).exec()
