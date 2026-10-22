"""Ejemplo publicable. Copiar como conexion.py en una instalación nueva.

Configurar MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD y MYSQL_DATABASE en el equipo.
No incluir contraseñas reales en este archivo ni en Git.
"""
import os
import mysql.connector
from mysql.connector.constants import ClientFlag

def conectar_bd():
    try:
        return mysql.connector.connect(
            host=os.environ.get('MYSQL_HOST','127.0.0.1'),
            port=int(os.environ.get('MYSQL_PORT','3306')),
            user=os.environ['MYSQL_USER'],
            password=os.environ['MYSQL_PASSWORD'],
            database=os.environ.get('MYSQL_DATABASE','crece_prestamos'),
            client_flags=[ClientFlag.FOUND_ROWS],
        )
    except (mysql.connector.Error,KeyError,ValueError):
        return None
