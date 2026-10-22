"""Emisión de códigos desde la sesión administrativa de escritorio."""
from PySide6.QtWidgets import QDialog,QVBoxLayout,QLabel,QLineEdit,QCheckBox,QPushButton,QFormLayout
from crece.servicios.recuperacion import emitir_codigo
from crece.infraestructura.base_datos import ErrorConexionBaseDatos

def recuperar_cuenta(parent,usuario_id,nombre):
    dialogo=QDialog(parent);dialogo.setWindowTitle('Recuperar acceso | CRECE+ PRÉSTAMOS');dialogo.setMinimumWidth(500)
    layout=QVBoxLayout(dialogo)
    texto=QLabel('Cuenta: '+nombre+'\n\nVerifica personalmente la identidad del titular contra su expediente antes de emitir el código. Conocer su correo o cédula no es suficiente.');texto.setWordWrap(True);layout.addWidget(texto)
    form=QFormLayout();motivo=QLineEdit();motivo.setMaxLength(250);motivo.setPlaceholderText('Ej.: Identidad contrastada presencialmente con el expediente')
    clave=QLineEdit();clave.setEchoMode(QLineEdit.Password);clave.setMaxLength(128)
    form.addRow('Constancia de verificación',motivo);form.addRow('Tu contraseña de administrador',clave);layout.addLayout(form)
    verificado=QCheckBox('Verifiqué la identidad del titular.');layout.addWidget(verificado)
    estado=QLabel();estado.setWordWrap(True);estado.setAccessibleName('Estado de recuperación');layout.addWidget(estado)
    emitir=QPushButton('Emitir código temporal');layout.addWidget(emitir)
    def generar():
        try:resultado=emitir_codigo(usuario_id,clave.text(),motivo.text(),verificado.isChecked())
        except (ValueError,ErrorConexionBaseDatos) as error:clave.clear();estado.setText(str(error));return
        clave.clear();dialogo.accept()
        entrega=QDialog(parent);entrega.setWindowTitle('Código temporal | CRECE+ PRÉSTAMOS');entrega.setMinimumWidth(520)
        contenido=QVBoxLayout(entrega)
        info=QLabel('Usuario: '+resultado['usuario']+'\nVence a las '+resultado['vence_en'].strftime('%H:%M:%S')+' (hora del servidor).\n\nSe muestra una sola vez. Entrégalo al titular por un canal privado. El usuario elegirá su contraseña en «Recuperar acceso», en web o escritorio.');info.setWordWrap(True);contenido.addWidget(info)
        codigo=QLineEdit(resultado['codigo']);codigo.setReadOnly(True);codigo.setAccessibleName('Código temporal de un solo uso');contenido.addWidget(codigo)
        cerrar=QPushButton('Cerrar');cerrar.clicked.connect(entrega.accept);contenido.addWidget(cerrar);entrega.exec()
    emitir.clicked.connect(generar);dialogo.exec()
