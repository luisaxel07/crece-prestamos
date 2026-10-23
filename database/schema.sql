-- CRECE + PRESTAMOS | Esquema inicial para MySQL 8+
CREATE DATABASE IF NOT EXISTS crece_prestamos
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE crece_prestamos;

CREATE TABLE usuarios (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  nombre_usuario VARCHAR(60) NOT NULL UNIQUE,
  hash_contrasena VARCHAR(255) NOT NULL,
  version_sesion INT NOT NULL DEFAULT 1,
  rol ENUM('ADMINISTRADOR','EMPLEADO','CLIENTE') NOT NULL,
  activo BOOLEAN NOT NULL DEFAULT TRUE,
  ultimo_acceso_en DATETIME NULL,
  creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE clientes (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  usuario_id BIGINT UNSIGNED NULL UNIQUE,
  cedula VARCHAR(30) NOT NULL UNIQUE,
  nombres VARCHAR(80) NOT NULL,
  apellidos VARCHAR(80) NOT NULL,
  telefono VARCHAR(25) NOT NULL,
  correo VARCHAR(160) NULL UNIQUE,
  direccion VARCHAR(255) NULL,
  estado ENUM('ACTIVO','INACTIVO','BLOQUEADO') NOT NULL DEFAULT 'ACTIVO',
  creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_clientes_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
) ENGINE=InnoDB;

CREATE TABLE prestamos (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  cliente_id BIGINT UNSIGNED NOT NULL,
  creado_por BIGINT UNSIGNED NOT NULL,
  monto_principal DECIMAL(14,2) NOT NULL,
  tasa_interes_anual DECIMAL(7,4) NOT NULL,
  plazo_meses SMALLINT UNSIGNED NOT NULL,
  cuota_mensual DECIMAL(14,2) NOT NULL,
  frecuencia VARCHAR(12) NOT NULL DEFAULT 'MENSUAL',
  recargo_porcentaje DECIMAL(5,2) NOT NULL DEFAULT 0,
  gracia_horas INT NOT NULL DEFAULT 72,
  fecha_desembolso DATE NOT NULL,
  fecha_primera_cuota DATE NOT NULL,
  estado ENUM('BORRADOR','ACTIVO','MORA','FINALIZADO','CANCELADO') NOT NULL DEFAULT 'ACTIVO',
  notas VARCHAR(500) NULL,
  creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT chk_prestamos_monto CHECK (monto_principal > 0),
  CONSTRAINT chk_prestamos_tasa CHECK (tasa_interes_anual >= 0),
  CONSTRAINT chk_prestamos_plazo CHECK (plazo_meses > 0),
  CONSTRAINT fk_prestamos_cliente FOREIGN KEY (cliente_id) REFERENCES clientes(id),
  CONSTRAINT fk_prestamos_creador FOREIGN KEY (creado_por) REFERENCES usuarios(id),
  INDEX idx_prestamos_cliente_estado (cliente_id, estado)
) ENGINE=InnoDB;

CREATE TABLE cuotas (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  prestamo_id BIGINT UNSIGNED NOT NULL,
  numero_cuota SMALLINT UNSIGNED NOT NULL,
  fecha_vencimiento DATE NOT NULL,
  saldo_inicial DECIMAL(14,2) NOT NULL,
  cuota_programada DECIMAL(14,2) NOT NULL,
  abono_capital DECIMAL(14,2) NOT NULL,
  interes DECIMAL(14,2) NOT NULL,
  monto_pagado DECIMAL(14,2) NOT NULL DEFAULT 0,
  recargo_pagado DECIMAL(14,2) NOT NULL DEFAULT 0,
  pagado_en DATETIME NULL,
  estado ENUM('PENDIENTE','PAGADA','VENCIDA','PARCIAL') NOT NULL DEFAULT 'PENDIENTE',
  UNIQUE KEY uq_cuotas_numero (prestamo_id, numero_cuota),
  CONSTRAINT fk_cuotas_prestamo FOREIGN KEY (prestamo_id) REFERENCES prestamos(id),
  INDEX idx_cuotas_vencimiento_estado (fecha_vencimiento, estado)
) ENGINE=InnoDB;

CREATE TABLE pagos (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  cuota_id BIGINT UNSIGNED NOT NULL,
  registrado_por BIGINT UNSIGNED NULL,
  monto DECIMAL(14,2) NOT NULL,
  monto_recargo DECIMAL(14,2) NOT NULL DEFAULT 0,
  fecha_pago DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  metodo ENUM('EFECTIVO','TRANSFERENCIA','TARJETA','PAGO_CLIENTE') NOT NULL,
  referencia VARCHAR(100) NULL,
  estado ENUM('PENDIENTE_VERIFICACION','CONFIRMADO','RECHAZADO','ANULADO') NOT NULL DEFAULT 'CONFIRMADO',
  notas VARCHAR(500) NULL,
  creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT chk_pagos_monto CHECK (monto > 0),
  CONSTRAINT fk_pagos_cuota FOREIGN KEY (cuota_id) REFERENCES cuotas(id),
  CONSTRAINT fk_pagos_registrador FOREIGN KEY (registrado_por) REFERENCES usuarios(id),
  INDEX idx_pagos_estado_fecha (estado, fecha_pago)
) ENGINE=InnoDB;

CREATE TABLE comprobantes_pago (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  pago_id BIGINT UNSIGNED NOT NULL UNIQUE,
  tipo_mime VARCHAR(40) NOT NULL,
  contenido MEDIUMBLOB NOT NULL,
  sha256 CHAR(64) NOT NULL,
  creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_comprobante_pago FOREIGN KEY (pago_id) REFERENCES pagos(id)
) ENGINE=InnoDB;

CREATE TABLE bitacora_auditoria (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  usuario_actor_id BIGINT UNSIGNED NULL,
  tipo_entidad VARCHAR(40) NOT NULL,
  entidad_id BIGINT UNSIGNED NOT NULL,
  accion VARCHAR(60) NOT NULL,
  detalle JSON NULL,
  creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_bitacora_usuario FOREIGN KEY (usuario_actor_id) REFERENCES usuarios(id),
  INDEX idx_bitacora_entidad (tipo_entidad, entidad_id)
) ENGINE=InnoDB;
