"""Pruebas exclusivamente en MySQL, en un esquema temporal creado por esta ejecución."""
import atexit
import re
from uuid import uuid4
from sqlalchemy import create_engine,event,text
from crece.infraestructura.modelos import Base
from crece.infraestructura.base_datos import configurar_motor

_motor=None
_esquema=None
_creado=False
_produccion=None

def _conexion():
    from crece.infraestructura.base_datos import abrir_conexion_mysql
    connection=abrir_conexion_mysql()
    if connection is None:raise RuntimeError('Las pruebas requieren MySQL activo y una conexión autorizada.')
    return connection

def _verificar_nombre():
    if not _creado or not re.fullmatch(r'crece_pruebas_[0-9a-f]{32}',_esquema or '') or _esquema==_produccion:
        raise RuntimeError('Se rechazó una operación fuera del esquema MySQL de pruebas.')

def cerrar():
    global _creado
    if not _creado:return
    _verificar_nombre()
    if _motor:_motor.dispose()
    connection=_conexion()
    try:
        cursor=connection.cursor();cursor.execute('DROP DATABASE `'+_esquema+'`');cursor.close();_creado=False
    finally:connection.close()

def preparar_mysql():
    global _motor,_esquema,_creado,_produccion
    if _motor is None:
        connection=_conexion()
        try:
            cursor=connection.cursor();cursor.execute('SELECT DATABASE()');_produccion=cursor.fetchone()[0]
            _esquema='crece_pruebas_'+uuid4().hex
            cursor.execute('CREATE DATABASE `'+_esquema+'` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci');cursor.close();_creado=True
            atexit.register(cerrar)
        except Exception as error:
            raise RuntimeError('No se pudo crear el esquema exclusivo de pruebas en MySQL. Revisa CREATE/DROP DATABASE; los datos del proyecto no se usan para probar.') from error
        finally:connection.close()
        def conectar_pruebas():
            _verificar_nombre();connection=_conexion()
            try:
                cursor=connection.cursor();cursor.execute('USE `'+_esquema+'`');cursor.execute('SELECT DATABASE()')
                if cursor.fetchone()[0]!=_esquema:raise RuntimeError('Esquema inesperado.')
                cursor.close();return connection
            except Exception:connection.close();raise
        _motor=create_engine('mysql+mysqlconnector://',creator=conectar_pruebas,pool_pre_ping=True)
        @event.listens_for(_motor,'checkout')
        def comprobar(connection,*_):
            cursor=connection.cursor();cursor.execute('SELECT DATABASE()');actual=cursor.fetchone()[0];cursor.close()
            if actual!=_esquema:raise RuntimeError('Conexión de pruebas fuera de su esquema.')
        Base.metadata.create_all(_motor)
    _verificar_nombre()
    # Solo limpia tablas del esquema aleatorio que creó esta ejecución.
    with _motor.connect() as connection:
        actual=connection.scalar(text('SELECT DATABASE()'))
        if actual!=_esquema:raise RuntimeError('No se permite limpiar esta base de datos.')
        connection.execute(text('SET FOREIGN_KEY_CHECKS=0'))
        try:
            for tabla in reversed(Base.metadata.sorted_tables):connection.execute(text('TRUNCATE TABLE `'+tabla.name+'`'))
        finally:connection.execute(text('SET FOREIGN_KEY_CHECKS=1'))
        connection.commit()
    configurar_motor(_motor)
    return _motor
