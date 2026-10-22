"""Aplicación independiente para clientes de CRECE + PRÉSTAMOS."""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase, QPixmap
from PySide6.QtWidgets import QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout

from crece.interfaz import ESTILO_APLICACION, PanelCliente, aplicar_sombra
from crece.servicios.autenticacion import iniciar_sesion
from crece.servicios.clientes import ErrorConexionBaseDatos


class AccesoPortalCliente(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.usuario = None
        self.setWindowTitle("Portal del cliente | CRECE + PRÉSTAMOS")
        self.resize(820, 500)
        self.setMinimumSize(760, 480)
        exterior = QHBoxLayout(self); exterior.setContentsMargins(18, 18, 18, 18); exterior.setSpacing(0)
        tarjeta = QFrame(); tarjeta.setObjectName("tarjetaAccesoCliente")
        tarjeta.setStyleSheet("QFrame#tarjetaAccesoCliente { background: #FDFEFE; border-radius: 28px; }")
        aplicar_sombra(tarjeta, 32, 9)
        exterior.addWidget(tarjeta)
        estructura = QHBoxLayout(tarjeta); estructura.setContentsMargins(0, 0, 0, 0); estructura.setSpacing(0)
        bienvenida = QFrame(); bienvenida.setObjectName("bienvenidaCliente")
        bienvenida.setStyleSheet("QFrame#bienvenidaCliente { background: #DDF5E9; border-top-left-radius: 28px; border-bottom-left-radius: 28px; }")
        mensaje = QVBoxLayout(bienvenida); mensaje.setContentsMargins(34, 34, 34, 30); mensaje.setSpacing(12)
        marca = QLabel("PORTAL DEL CLIENTE")
        marca.setStyleSheet("background: #C2EBD6; color: #006633; border-radius: 11px; padding: 7px; font-size: 11px; font-weight: 800;")
        mensaje.addWidget(marca, alignment=Qt.AlignLeft)
        mensaje.addStretch()
        ruta_logo = Path(__file__).resolve().parent / "assets" / "logo_crece.png"
        if ruta_logo.exists():
            logo = QLabel(); logo.setPixmap(QPixmap(str(ruta_logo)).scaled(142, 142, Qt.KeepAspectRatio, Qt.SmoothTransformation)); logo.setAlignment(Qt.AlignCenter)
            logo.setFixedSize(148, 148); logo.setStyleSheet("background: transparent;")
            mensaje.addWidget(logo, alignment=Qt.AlignLeft)
        titulo_lateral = QLabel("Tu crédito,\nsiempre contigo.")
        titulo_lateral.setStyleSheet("font-size: 24px; font-weight: 800; color: #003366;"); mensaje.addWidget(titulo_lateral)
        texto_lateral = QLabel("Revisa tus cuotas, conoce tu saldo y envía solicitudes de pago desde un solo lugar.")
        texto_lateral.setWordWrap(True); texto_lateral.setStyleSheet("color: #356170; font-size: 13px;"); mensaje.addWidget(texto_lateral)
        mensaje.addStretch(2)
        estructura.addWidget(bienvenida, 4)
        acceso = QFrame(); acceso.setObjectName("panelAccesoCliente")
        acceso.setStyleSheet("QFrame#panelAccesoCliente { background: #FDFEFE; border-top-right-radius: 28px; border-bottom-right-radius: 28px; }")
        distribucion = QVBoxLayout(acceso); distribucion.setContentsMargins(42, 46, 42, 38); distribucion.setSpacing(12)
        estructura.addWidget(acceso, 5)
        titulo = QLabel("Bienvenido a tu portal")
        titulo.setStyleSheet("font-size: 26px; font-weight: 800; color: #003366;"); distribucion.addWidget(titulo)
        subtitulo = QLabel("Ingresa para consultar únicamente tu información financiera.")
        subtitulo.setWordWrap(True); subtitulo.setStyleSheet("color: #667788; font-size: 13px;"); distribucion.addWidget(subtitulo)
        distribucion.addSpacing(12)
        nombre_usuario, contrasena = QLineEdit(), QLineEdit()
        nombre_usuario.setPlaceholderText("Tu usuario")
        contrasena.setPlaceholderText("Tu contraseña")
        contrasena.setEchoMode(QLineEdit.Password)
        estilo_campo = "QLineEdit { background: #F3F7F8; color: #003366; border: 2px solid #D8E4E8; border-radius: 13px; padding: 11px 14px; min-height: 24px; font-size: 13px; } QLineEdit:focus { background: #FFFFFF; border: 2px solid #00A651; }"
        nombre_usuario.setStyleSheet(estilo_campo); contrasena.setStyleSheet(estilo_campo)
        etiqueta_usuario = QLabel("USUARIO"); etiqueta_usuario.setStyleSheet("font-size: 11px; font-weight: 800; color: #385D78;")
        etiqueta_contrasena = QLabel("CONTRASEÑA"); etiqueta_contrasena.setStyleSheet("font-size: 11px; font-weight: 800; color: #385D78;")
        distribucion.addWidget(etiqueta_usuario); distribucion.addWidget(nombre_usuario)
        distribucion.addWidget(etiqueta_contrasena); distribucion.addWidget(contrasena)
        distribucion.addStretch()
        ingresar = QPushButton("Ingresar a mi portal")
        ingresar.setMinimumHeight(54)
        ingresar.setStyleSheet("QPushButton { background: #00A651; color: white; border: 0; border-radius: 15px; font-size: 14px; font-weight: 800; } QPushButton:hover { background: #008B44; }")
        distribucion.addWidget(ingresar)
        seguridad = QLabel("Acceso protegido · CRECE + PRÉSTAMOS")
        seguridad.setAlignment(Qt.AlignCenter); seguridad.setStyleSheet("color: #728B9C; font-size: 10px;"); distribucion.addWidget(seguridad)

        def acceder() -> None:
            try:
                usuario = iniciar_sesion(nombre_usuario.text(), contrasena.text())
            except ErrorConexionBaseDatos as error:
                QMessageBox.warning(self, "Portal no disponible", str(error))
                return
            if not usuario or usuario["rol"] != "CLIENTE":
                QMessageBox.warning(self, "Acceso no permitido", "Estas credenciales no pertenecen a una cuenta de cliente.")
                return
            self.usuario = usuario
            self.accept()

        ingresar.clicked.connect(acceder)


def ejecutar_portal_cliente() -> int:
    aplicacion = QApplication([])
    QFontDatabase.addApplicationFont("C:/Windows/Fonts/arial.ttf")
    aplicacion.setStyleSheet(ESTILO_APLICACION)
    aplicacion.setFont(QFont("Arial", 10))
    acceso = AccesoPortalCliente()
    if acceso.exec() != QDialog.Accepted:
        return 0
    ventana = PanelCliente(acceso.usuario)
    ventana.show()
    return aplicacion.exec()


if __name__ == "__main__":
    raise SystemExit(ejecutar_portal_cliente())
