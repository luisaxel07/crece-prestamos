from PySide6.QtWidgets import QMessageBox
from ui.access_dialog import AccessDialog
from ui.widgets.premium import Field


class RecoveryDialog(AccessDialog):
    def __init__(self,parent=None,service=None):
        super().__init__(parent,service,'Recupera tu acceso.','Solicita al administrador un código tras verificar tu identidad. Válido 15 minutos y una sola vez.')
        self.submit_text='Guardar nueva contraseña'
        self.submit.setText(self.submit_text)
        self.username=self.add_field('Usuario de acceso',Field('Tu usuario registrado','Usuario de acceso'))
        self.username.setMaxLength(60)
        self.code=self.add_field('Código temporal',Field('Código temporal','Código temporal',icon='lock'))
        self.code.setMaxLength(43)
        self.password=self.add_field('Nueva contraseña',Field('10 a 128 caracteres','Nueva contraseña',True,'lock'))
        self.confirm=self.add_field('Confirmar contraseña',Field('Repite la contraseña','Confirmar contraseña',True,'lock'))
        self.password.setMaxLength(128);self.confirm.setMaxLength(128)
        self.add_link('Volver a iniciar sesión',self.reject)
        self.submit.clicked.connect(self.recover)

    def recover(self):
        import re
        username,code,password,confirm=self.username.text().strip(),self.code.text().strip(),self.password.text(),self.confirm.text()
        if not username or not re.fullmatch(r'[A-Za-z0-9_-]{43}',code):self.show_error('Ingresa tu usuario y el código completo entregado por el administrador.');return
        if not 10<=len(password)<=128:self.show_error('La contraseña debe tener entre 10 y 128 caracteres.');return
        if password!=confirm:self.show_error('Las contraseñas no coinciden.');return
        def completed(response):
            self.code.clear()
            if not isinstance(response,dict) or response.get('accepted') is not True:
                self.show_error('No se pudo confirmar el cambio de contraseña.');return
            QMessageBox.information(self,'Acceso recuperado',response['message'])
            self.accept()
        self.start_job(lambda:self.service.recover(username,code,password,confirm),completed)
