from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QEvent
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QPushButton, QScrollArea, QProgressBar, QSizePolicy)
from ui.widgets.premium import (ROOT, BLUE, GREEN, GRAY, Scene, GlassCard, Task,
    brand_label, title_font, symbol, fade, load_fonts, reduced_motion, ASSETS)
from services.auth_service import AuthService
from ui.appearance import theme_picker, bind_theme


class AccessDialog(QDialog):
    def __init__(self, parent=None, service=None, title='Crecemos contigo.', subtitle='Accede a tu cuenta de forma segura', minimal_login=False):
        super().__init__(parent)
        self.minimal_login = minimal_login
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowSystemMenuHint |
                            Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
        self.service = service or AuthService()
        self.setFont(QFont('Open Sans',10))
        self.job = None
        self.busy = False
        load_fonts()
        self.setWindowTitle('Acceso seguro | CRECE+ PRÉSTAMOS')
        self.setMinimumSize(340, 440)
        self.resize(1380, 930)
        self.setStyleSheet((ROOT / 'styles/theme.qss').read_text(encoding='utf-8').replace('__ASSETS__',ASSETS.as_posix()))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        self.scene = Scene()
        layout.addWidget(self.scene)
        row = QHBoxLayout(self.scene)
        row.setContentsMargins(38,20,38,20)
        row.setSpacing(30)
        self.left = QWidget()
        left_layout = QVBoxLayout(self.left)
        left_layout.setContentsMargins(0,0,0,0)
        side_logo = brand_label(200,True)
        side_logo.setStyleSheet('background: #001F3F; border-radius: 12px;')
        left_layout.addWidget(side_logo,alignment=Qt.AlignLeft)
        left_layout.addStretch()
        for index, (name,heading,text) in enumerate([
            ('shield','Confianza','Tu respaldo en cada paso.'),
            ('document','Transparencia','Información clara y segura.'),
            ('growth','Impulso','Crecemos contigo.')]):
            item = QWidget()
            item_row = QHBoxLayout(item)
            item_row.setContentsMargins(0,8,0,8)
            image = QLabel()
            image.setFixedSize(54,54)
            image.setPixmap(symbol(name,'#FFFFFF',26).pixmap(26,26))
            image.setAlignment(Qt.AlignCenter)
            image.setStyleSheet('background: rgba(0,166,81,145); border-radius: 27px;')
            item_row.addWidget(image)
            text_box = QVBoxLayout()
            text_box.setSpacing(4)
            label = QLabel(heading)
            label.setFont(title_font(12))
            label.setObjectName('sceneText')
            caption = QLabel(text)
            caption.setObjectName('sceneText')
            caption.setStyleSheet('font-size: 11px;')
            text_box.addWidget(label)
            text_box.addWidget(caption)
            item_row.addLayout(text_box)
            item_row.addStretch()
            left_layout.addWidget(item)
            fade(item,200+index*100)
        left_layout.addStretch(2)
        row.addWidget(self.left,1)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setMaximumWidth(565)
        self.scroll.setMinimumWidth(0)
        self.scroll.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
        if minimal_login:
            self.scroll.viewport().installEventFilter(self)
        scroll_body = QWidget()
        self.stack = QVBoxLayout(scroll_body)
        self.stack.setContentsMargins(10,20,10,20)
        self.stack.addStretch()
        if minimal_login:
            from ui.widgets.login_glass import LoginGlassCard
            self.card = LoginGlassCard(self.scene)
        else:
            self.card = GlassCard(self.scene)
        self.card.setMaximumWidth(460 if minimal_login else 545)
        self.card.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Maximum)
        self.content = QVBoxLayout(self.card)
        self.content.setContentsMargins(48,4,48,27)
        self.content.setSpacing(0 if minimal_login else 10)
        self.theme_control = theme_picker(self.scene if minimal_login else self)
        if not minimal_login:
            self.content.addWidget(self.theme_control,alignment=Qt.AlignRight)
        self.logo = brand_label(144)
        self.logo.setObjectName('authLogo')
        self.content.addWidget(self.logo,alignment=Qt.AlignHCenter)
        self.heading = QLabel(title)
        self.heading.setObjectName('heading')
        self.heading.setFont(title_font(19))
        self.heading.setWordWrap(True)
        self.heading.setAlignment(Qt.AlignCenter)
        self.content.addWidget(self.heading)
        self.subtitle = QLabel(subtitle)
        self.subtitle.setObjectName('subtitle')
        self.subtitle.setWordWrap(True)
        self.subtitle.setAlignment(Qt.AlignCenter)
        self.content.addWidget(self.subtitle)
        self.heading.setVisible(not minimal_login)
        self.subtitle.setVisible(not minimal_login)
        self.content.addSpacing(24 if minimal_login else 15)
        self.form = QVBoxLayout()
        self.form.setSpacing(18 if minimal_login else 10)
        self.content.addLayout(self.form)
        if minimal_login:
            self.content.addSpacing(26)
        self.error = QLabel()
        self.error.setObjectName('error')
        self.error.setWordWrap(True)
        self.error.setAccessibleName('Estado de la solicitud')
        self.error.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.error.hide()
        self.content.addWidget(self.error)
        self.progress = QProgressBar()
        self.progress.setRange(0,0)
        self.progress.setTextVisible(False)
        self.progress.setAccessibleName('Solicitud en curso')
        self.progress.hide()
        self.content.addWidget(self.progress)
        self.submit = QPushButton('Iniciar sesión')
        self.submit.setObjectName('primary')
        self.submit.setIcon(symbol('arrow','#FFFFFF',20))
        self.submit.setLayoutDirection(Qt.RightToLeft)
        self.submit.setCursor(Qt.PointingHandCursor)
        self.submit.setDefault(True)
        self.content.addWidget(self.submit)
        self.links = QVBoxLayout()
        self.links.setSpacing(0)
        self.content.addLayout(self.links)
        self.note = QLabel('Tu información, clara y protegida.')
        self.note.setObjectName('note')
        self.note.setAlignment(Qt.AlignCenter)
        self.note.setStyleSheet('font-size: 10px;')
        self.content.addWidget(self.note)
        self.note.setVisible(not minimal_login)
        self.stack.addWidget(self.card,alignment=Qt.AlignHCenter if minimal_login else Qt.AlignmentFlag(0))
        self.stack.addStretch()
        self.scroll.setWidget(scroll_body)
        row.addWidget(self.scroll,2)
        self.right = QWidget()
        right_layout = QVBoxLayout(self.right)
        right_layout.setContentsMargins(0,90,0,30)
        eyebrow = QLabel('CONTIGO, HACIA ADELANTE')
        eyebrow.setObjectName('sceneText')
        eyebrow.setStyleSheet('font-size: 10px;')
        right_layout.addWidget(eyebrow)
        quote = QLabel('Grandes metas comienzan con un buen respaldo.')
        quote.setWordWrap(True)
        quote.setFont(title_font(21))
        quote.setObjectName('sceneText')
        right_layout.addWidget(quote)
        line = QLabel()
        line.setFixedSize(75,3)
        line.setStyleSheet('background: #00A651;')
        right_layout.addWidget(line)
        right_layout.addStretch()
        dots = QLabel('●   ●   ●   ●')
        dots.setAlignment(Qt.AlignRight)
        dots.setStyleSheet('color: #00A651; font-size: 10px;')
        right_layout.addWidget(dots)
        row.addWidget(self.right,1)
        bind_theme(self,self.scene,auth=True)
        self.adjust_responsive()
        QTimer.singleShot(0,self.scene.refresh_background)
        # Avoid nesting opacity effects around the card's shadow and blur.
        from PySide6.QtGui import QGuiApplication
        if not reduced_motion() and QGuiApplication.platformName() != 'offscreen':
            self.setWindowOpacity(0.)
            self._entry = QPropertyAnimation(self,b'windowOpacity',self)
            self._entry.setDuration(350)
            self._entry.setStartValue(0.)
            self._entry.setEndValue(1.)
            self._entry.setEasingCurve(QEasingCurve.OutCubic)
            QTimer.singleShot(0,self._entry.start)

    def add_field(self, label, field):
        if not self.minimal_login:
            caption = QLabel(label)
            caption.setBuddy(field)
            caption.setStyleSheet('font-size: 11px; font-weight: 600;')
            self.form.addWidget(caption)
        self.form.addWidget(field)
        return field

    def add_link(self, text, callback):
        button = QPushButton(text)
        button.setObjectName('link')
        button.setAutoDefault(False)
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(callback)
        self.links.addWidget(button)
        return button

    def show_error(self, message):
        self.error.setText(message)
        self.error.setAccessibleDescription(message)
        self.error.show()
        self.scroll.ensureWidgetVisible(self.error)

    def start_job(self, callback, success):
        if self.busy:
            return
        self.busy = True
        self.error.hide()
        self.submit.setEnabled(False)
        self.submit.setText('Verificando…')
        self.progress.show()
        self.job = Task(callback,self)
        task = self.job
        task.outcome = None
        task.failure = None
        task.result.connect(lambda value: setattr(task,'outcome',value))
        task.failed.connect(lambda message: setattr(task,'failure',message))
        def completed():
            self.busy = False
            self.progress.hide()
            self.submit.setEnabled(True)
            self.submit.setText(self.submit_text)
            self.job = None
            task.deleteLater()
            self.clear_passwords()
            if task.failure:
                self.show_error(task.failure)
            else:
                success(task.outcome)
        task.finished.connect(completed)
        task.start()

    def clear_passwords(self):
        from ui.widgets.premium import Field
        for field in self.findChildren(Field):
            if hasattr(field,'toggle_action'):
                field.clear()
                field.toggle_action.setChecked(False)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'left'):
            self.adjust_responsive()

    def adjust_responsive(self):
        wide = self.width() >= 1200
        self.left.setVisible(wide)
        self.right.setVisible(wide)
        compact = self.width() < 600
        self.scene.layout().setContentsMargins(3 if compact else 38,0 if compact else 20,3 if compact else 38,0 if compact else 20)
        if self.minimal_login:
            self.content.setContentsMargins(24 if compact else 40,24 if compact else 32,24 if compact else 40,30 if compact else 40)
            QTimer.singleShot(0,self.position_theme_control)
        else:
            self.content.setContentsMargins(20 if compact else 48,4,20 if compact else 48,27)

    def position_theme_control(self):
        self.card.setFixedWidth(min(460,max(260,self.scroll.viewport().width()-20)))
        self.theme_control.adjustSize()
        self.theme_control.move(max(12,self.scene.width()-self.theme_control.width()-20),14)
        self.theme_control.raise_()

    def eventFilter(self, watched, event):
        if self.minimal_login and hasattr(self,'scroll') and watched is self.scroll.viewport() and event.type()==QEvent.Resize:
            QTimer.singleShot(0,self.position_theme_control)
        return super().eventFilter(watched,event)

    def closeEvent(self,event):
        if self.busy:
            self.show_error('Espera a que termine la solicitud antes de cerrar esta ventana.')
            event.ignore()
        else:
            super().closeEvent(event)

    def reject(self):
        if not self.busy:
            super().reject()
