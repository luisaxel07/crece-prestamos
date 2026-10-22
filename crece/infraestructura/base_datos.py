"""Motor reutilizable, una sesión por operación y rollback automático."""
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

class ErrorConexionBaseDatos(Exception): pass
_engine=None
_factory=None

def abrir_conexion_mysql():
    """FOUND_ROWS permite a SQLAlchemy contar filas encontradas, incluso sin cambios."""
    from conexion import conectar_bd
    from mysql.connector.constants import ClientFlag
    from mysql.connector import Error
    connection=conectar_bd()
    if connection is None:raise ErrorConexionBaseDatos('No se pudo conectar a MySQL. Revisa la configuración de conexión.')
    try:
        if not connection.client_flags & ClientFlag.FOUND_ROWS:
            connection.client_flags=connection.client_flags | ClientFlag.FOUND_ROWS
            connection.reconnect(attempts=1,delay=0)
        return connection
    except Error as error:
        connection.close()
        raise ErrorConexionBaseDatos('No se pudo preparar la conexión MySQL.') from error

def configurar_motor(engine):
    """Inyección del motor para pruebas aisladas; no crea tablas de producción."""
    global _engine,_factory
    if engine.dialect.name!='mysql':raise ValueError('CRECE+ PRÉSTAMOS utiliza exclusivamente MySQL.')
    _engine=engine
    _factory=sessionmaker(bind=engine,expire_on_commit=False)

def obtener_motor():
    if _engine is None:
        configurar_motor(create_engine('mysql+mysqlconnector://',creator=abrir_conexion_mysql,pool_pre_ping=True,pool_recycle=1800))
    return _engine

@contextmanager
def transaccion():
    obtener_motor()
    try:
        with _factory() as session,session.begin():
            yield session
    except IntegrityError as error:
        raise ValueError('Hay datos duplicados o relacionados con otros registros. Revisa la cédula, usuario y correo.') from error
    except SQLAlchemyError as error:
        raise ErrorConexionBaseDatos('No se pudo completar la operación de base de datos. Verifica conexión y migraciones.') from error
