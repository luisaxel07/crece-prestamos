from PySide6.QtWidgets import QLabel
from ui.access_dialog import AccessDialog


class RegisterWindow(AccessDialog):
    """El alta se realiza con expediente y autorización, sin un registro público ficticio."""
    def __init__(self,parent=None,service=None):
        super().__init__(parent,service,'Solicita tu acceso.','Tu cuenta se crea desde administración')
        aviso=QLabel('Si eres cliente, el personal verificará tu expediente y habilitará tu cuenta vinculada.\n\nSi eres empleado, un administrador registrará tus datos y credenciales. Solo las cuentas activas pueden operar.\n\nContacta directamente al equipo de CRECE+ PRÉSTAMOS para solicitar tu acceso.')
        aviso.setWordWrap(True);aviso.setAccessibleName('Instrucciones para solicitar una cuenta')
        self.form.addWidget(aviso)
        self.submit.setText('Volver a iniciar sesión')
        self.submit.clicked.connect(self.reject)
