"""Aplica una migración segura sin eliminar información existente."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from conexion import conectar_bd


conexion = conectar_bd()
if not conexion:
    raise SystemExit("No se pudo aplicar la migración: revisa conexion.py.")

cursor = conexion.cursor()
cursor.execute("SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name = 'usuarios' AND column_name = 'requiere_cambio_contrasena'")
if cursor.fetchone()[0] == 0:
    cursor.execute("ALTER TABLE usuarios ADD COLUMN requiere_cambio_contrasena BOOLEAN NOT NULL DEFAULT FALSE, ADD COLUMN actualizado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
cursor.execute("CREATE TABLE IF NOT EXISTS recuperaciones_contrasena (id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY, usuario_id BIGINT UNSIGNED NOT NULL, codigo_hash VARCHAR(255) NOT NULL, vence_en DATETIME NOT NULL, usado_en DATETIME NULL, creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, CONSTRAINT fk_recuperaciones_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id), INDEX idx_recuperaciones_vigencia (usuario_id, vence_en)) ENGINE=InnoDB")
cursor.execute("CREATE TABLE IF NOT EXISTS configuracion_empresa (id TINYINT UNSIGNED PRIMARY KEY DEFAULT 1, nombre_empresa VARCHAR(120) NOT NULL DEFAULT 'CRECE + PRÉSTAMOS', moneda VARCHAR(10) NOT NULL DEFAULT 'C$', actualizado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP) ENGINE=InnoDB")
cursor.execute("INSERT IGNORE INTO configuracion_empresa (id) VALUES (1)")
conexion.commit()
conexion.close()
print("Migración de seguridad aplicada correctamente.")
