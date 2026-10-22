"""Adaptador del backend existente; reemplazable por un repositorio SQLAlchemy."""
from crece.servicios.autenticacion import (
    configurar_administrador, hay_administrador_configurado, iniciar_sesion,
)


class AuthService:
    def setup_required(self):
        return not hay_administrador_configurado()

    def login(self, username, password):
        user = iniciar_sesion(username, password)
        if not user or user['rol'] not in ('ADMINISTRADOR', 'EMPLEADO'):
            raise ValueError('Usuario o contraseña incorrectos, o cuenta no autorizada para administración.')
        return {key: user[key] for key in ('id', 'nombre_usuario', 'rol', 'version_sesion','requiere_cambio_contrasena') if key in user}

    def setup(self, username, password):
        if hay_administrador_configurado():
            raise ValueError('El administrador ya fue configurado. Vuelve a iniciar sesión.')
        configurar_administrador(username, password)
        return self.login(username, password)

    def register(self, name, email, password):
        raise ValueError('Las cuentas de personal y clientes se crean únicamente desde administración tras verificar el expediente.')

    def recover(self, username, code, password, confirm):
        from crece.servicios.recuperacion import restablecer_contrasena
        return restablecer_contrasena(username,code,password,confirm)
