"""Fachada pública compatible; persistencia implementada con ORM."""
from crece.infraestructura.base_datos import ErrorConexionBaseDatos
from .gestion import listar_clientes, registrar_cliente, obtener_cliente, actualizar_cliente, eliminar_cliente
