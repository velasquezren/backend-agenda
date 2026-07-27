-- DDL para MySQL en el servidor de produccion.
-- En local (SQLite) no hace falta: `python seed.py` crea las tablas via SQLAlchemy.
--
--   CREATE DATABASE agenda CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
--   mysql -u root -p agenda < schema_mysql.sql

CREATE TABLE medico (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(120) NOT NULL,
  color CHAR(7) NOT NULL DEFAULT '#4f46e5',
  horario_ref VARCHAR(255) NULL,
  activo TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE licenciada (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(120) NOT NULL,
  usuario VARCHAR(60) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  activo TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE medico_licenciada (
  medico_id INT NOT NULL,
  licenciada_id INT NOT NULL,
  PRIMARY KEY (medico_id, licenciada_id),
  FOREIGN KEY (medico_id) REFERENCES medico(id),
  FOREIGN KEY (licenciada_id) REFERENCES licenciada(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE paciente (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(160) NOT NULL,
  telefono VARCHAR(40) NULL,
  notas VARCHAR(500) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_paciente_nombre (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE serie (
  id INT AUTO_INCREMENT PRIMARY KEY,
  medico_id INT NOT NULL,
  paciente_id INT NOT NULL,
  licenciada_id INT NOT NULL,
  dias_semana VARCHAR(20) NOT NULL,   -- CSV ISO: "1,3,5" (1=lunes..7=domingo)
  hora_inicio TIME NOT NULL,
  hora_fin TIME NOT NULL,
  fecha_desde DATE NOT NULL,
  fecha_hasta DATE NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (medico_id) REFERENCES medico(id),
  FOREIGN KEY (paciente_id) REFERENCES paciente(id),
  FOREIGN KEY (licenciada_id) REFERENCES licenciada(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE cita (
  id INT AUTO_INCREMENT PRIMARY KEY,
  medico_id INT NOT NULL,
  paciente_id INT NOT NULL,
  licenciada_id INT NOT NULL,
  serie_id INT NULL,
  inicio DATETIME NOT NULL,
  fin DATETIME NOT NULL,
  estado ENUM('programada','cumplida','cancelada','no_asistio')
         NOT NULL DEFAULT 'programada',
  notas VARCHAR(500) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                       ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (medico_id) REFERENCES medico(id),
  FOREIGN KEY (paciente_id) REFERENCES paciente(id),
  FOREIGN KEY (licenciada_id) REFERENCES licenciada(id),
  FOREIGN KEY (serie_id) REFERENCES serie(id),
  INDEX idx_medico_rango (medico_id, inicio, fin)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
