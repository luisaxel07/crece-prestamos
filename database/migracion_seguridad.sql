-- Ejecutar una sola vez sobre la base existente crece_prestamos.
USE crece_prestamos;

ALTER TABLE usuarios
  ADD COLUMN requiere_cambio_contrasena BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN actualizado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

CREATE TABLE IF NOT EXISTS recuperaciones_contrasena (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  usuario_id BIGINT UNSIGNED NOT NULL,
  codigo_hash VARCHAR(255) NOT NULL,
  vence_en DATETIME NOT NULL,
  usado_en DATETIME NULL,
  creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_recuperaciones_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
  INDEX idx_recuperaciones_vigencia (usuario_id, vence_en)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS configuracion_empresa (
  id TINYINT UNSIGNED PRIMARY KEY DEFAULT 1,
  nombre_empresa VARCHAR(120) NOT NULL DEFAULT 'CRECE + PRÉSTAMOS',
  moneda VARCHAR(10) NOT NULL DEFAULT 'C$',
  actualizado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

INSERT IGNORE INTO configuracion_empresa (id) VALUES (1);
