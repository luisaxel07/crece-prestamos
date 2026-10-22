"""Contrato real de rowcount que necesita SQLAlchemy para UPDATE sobre MySQL."""
import unittest
from sqlalchemy import text
from mysql_support import preparar_mysql
from crece.infraestructura.base_datos import transaccion
from crece.infraestructura.modelos import Usuario

class MySQLBackendTests(unittest.TestCase):
    def test_unchanged_update_still_counts_the_matched_row(self):
        engine=preparar_mysql()
        try:
            self.assertEqual(engine.dialect.name,'mysql')
            with transaccion() as s:
                user=Usuario(nombre_usuario='fila_prueba',hash_contrasena='sin_acceso',rol='EMPLEADO');s.add(user);s.flush();id=user.id
            with engine.begin() as c:
                result=c.execute(text('UPDATE usuarios SET nombre_usuario=nombre_usuario WHERE id=:id'),dict(id=id))
                self.assertEqual(result.rowcount,1)
        finally:engine.dispose()
