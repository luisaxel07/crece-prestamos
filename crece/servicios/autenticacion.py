"""Fachada pública compatible; persistencia implementada con ORM."""
from .cuentas_orm import (hay_administrador_configurado, configurar_administrador, iniciar_sesion, iniciar_sesion_cliente_por_correo, crear_cuenta_cliente, actualizar_correo_cliente_portal, listar_usuarios, crear_usuario_personal, cambiar_estado_usuario, obtener_cliente_para_cuenta, actualizar_usuario, eliminar_usuario)
