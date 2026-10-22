"""Acceso a datos y lógica de negocio del prototipo."""
import hashlib
import os
import re

import mysql.connector


MYSQL_HOST = os.environ.get("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "comite_db")

SCHEMA = (
    """CREATE TABLE IF NOT EXISTS rol (
        id_rol INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        nombre VARCHAR(100) NOT NULL UNIQUE,
        descripcion VARCHAR(500) NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS usuario (
        id_usuario INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        nombre VARCHAR(255) NOT NULL,
        correo VARCHAR(255) NOT NULL UNIQUE,
        password_hash CHAR(64) NOT NULL,
        id_rol INT NOT NULL,
        activo TINYINT NOT NULL DEFAULT 1,
        fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_usuario_rol FOREIGN KEY (id_rol) REFERENCES rol(id_rol)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS investigador (
        id_investigador INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        id_usuario INT NOT NULL UNIQUE,
        documento VARCHAR(100) NULL UNIQUE,
        programa VARCHAR(255) NULL,
        facultad VARCHAR(255) NULL,
        telefono VARCHAR(50) NULL,
        CONSTRAINT fk_investigador_usuario FOREIGN KEY (id_usuario)
            REFERENCES usuario(id_usuario)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS tipo_solicitud (
        id_tipo INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        nombre VARCHAR(255) NOT NULL UNIQUE,
        descripcion VARCHAR(500) NULL,
        activo TINYINT NOT NULL DEFAULT 1
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS requisito (
        id_requisito INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        id_tipo INT NOT NULL,
        nombre VARCHAR(255) NOT NULL,
        obligatorio TINYINT NOT NULL DEFAULT 1,
        CONSTRAINT fk_requisito_tipo FOREIGN KEY (id_tipo)
            REFERENCES tipo_solicitud(id_tipo)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS sesion_comite (
        id_sesion INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        numero VARCHAR(100) NOT NULL UNIQUE,
        fecha VARCHAR(40) NOT NULL,
        hora VARCHAR(40) NULL,
        lugar VARCHAR(255) NULL,
        estado VARCHAR(100) NOT NULL DEFAULT 'Programada'
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS solicitud (
        id_solicitud INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        codigo VARCHAR(100) NOT NULL UNIQUE,
        id_investigador INT NOT NULL,
        id_tipo INT NOT NULL,
        titulo VARCHAR(500) NOT NULL,
        resumen LONGTEXT NULL,
        fecha_radicacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        estado VARCHAR(100) NOT NULL DEFAULT 'Recibida',
        prioridad VARCHAR(100) NOT NULL DEFAULT 'Media',
        fecha_limite VARCHAR(40) NULL,
        CONSTRAINT fk_solicitud_investigador FOREIGN KEY (id_investigador)
            REFERENCES investigador(id_investigador),
        CONSTRAINT fk_solicitud_tipo FOREIGN KEY (id_tipo)
            REFERENCES tipo_solicitud(id_tipo)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS documento (
        id_documento INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        id_solicitud INT NOT NULL,
        nombre VARCHAR(255) NOT NULL,
        ruta VARCHAR(1000) NULL,
        tipo VARCHAR(100) NULL,
        version INT NOT NULL DEFAULT 1,
        fecha_carga DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_documento_solicitud FOREIGN KEY (id_solicitud)
            REFERENCES solicitud(id_solicitud)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS validacion_requisito (
        id_validacion INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        id_solicitud INT NOT NULL,
        id_requisito INT NOT NULL,
        cumple TINYINT NOT NULL DEFAULT 0,
        observacion LONGTEXT NULL,
        id_usuario_valida INT NULL,
        fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_validacion_solicitud FOREIGN KEY (id_solicitud)
            REFERENCES solicitud(id_solicitud),
        CONSTRAINT fk_validacion_requisito FOREIGN KEY (id_requisito)
            REFERENCES requisito(id_requisito)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS asignacion_revision (
        id_asignacion INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        id_solicitud INT NOT NULL,
        id_usuario INT NOT NULL,
        fecha_asignacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        fecha_limite VARCHAR(40) NULL,
        estado VARCHAR(100) NOT NULL DEFAULT 'Pendiente',
        CONSTRAINT fk_asignacion_solicitud FOREIGN KEY (id_solicitud)
            REFERENCES solicitud(id_solicitud),
        CONSTRAINT fk_asignacion_usuario FOREIGN KEY (id_usuario)
            REFERENCES usuario(id_usuario)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS revision (
        id_revision INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        id_solicitud INT NOT NULL,
        id_usuario INT NOT NULL,
        concepto LONGTEXT NULL,
        observacion LONGTEXT NULL,
        fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_revision_solicitud FOREIGN KEY (id_solicitud)
            REFERENCES solicitud(id_solicitud),
        CONSTRAINT fk_revision_usuario FOREIGN KEY (id_usuario)
            REFERENCES usuario(id_usuario)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS observacion (
        id_observacion INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        id_solicitud INT NOT NULL,
        id_usuario INT NOT NULL,
        descripcion LONGTEXT NOT NULL,
        tipo VARCHAR(100) NOT NULL DEFAULT 'General',
        atendida TINYINT NOT NULL DEFAULT 0,
        fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_observacion_solicitud FOREIGN KEY (id_solicitud)
            REFERENCES solicitud(id_solicitud),
        CONSTRAINT fk_observacion_usuario FOREIGN KEY (id_usuario)
            REFERENCES usuario(id_usuario)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS agenda_sesion (
        id_agenda INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        id_sesion INT NOT NULL,
        id_solicitud INT NOT NULL,
        orden INT NULL,
        CONSTRAINT fk_agenda_sesion FOREIGN KEY (id_sesion)
            REFERENCES sesion_comite(id_sesion),
        CONSTRAINT fk_agenda_solicitud FOREIGN KEY (id_solicitud)
            REFERENCES solicitud(id_solicitud)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS decision (
        id_decision INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        id_solicitud INT NOT NULL,
        id_sesion INT NULL,
        decision VARCHAR(255) NOT NULL,
        observacion LONGTEXT NULL,
        id_usuario INT NULL,
        fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_decision_solicitud FOREIGN KEY (id_solicitud)
            REFERENCES solicitud(id_solicitud),
        CONSTRAINT fk_decision_sesion FOREIGN KEY (id_sesion)
            REFERENCES sesion_comite(id_sesion),
        CONSTRAINT fk_decision_usuario FOREIGN KEY (id_usuario)
            REFERENCES usuario(id_usuario)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS acta (
        id_acta INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        id_sesion INT NOT NULL UNIQUE,
        numero VARCHAR(100) NULL,
        contenido LONGTEXT NULL,
        fecha_generacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        version INT NOT NULL DEFAULT 1,
        CONSTRAINT fk_acta_sesion FOREIGN KEY (id_sesion)
            REFERENCES sesion_comite(id_sesion)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS historial_estado (
        id_historial INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        id_solicitud INT NOT NULL,
        estado_anterior VARCHAR(100) NULL,
        estado_nuevo VARCHAR(100) NOT NULL,
        id_usuario INT NULL,
        comentario LONGTEXT NULL,
        fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_historial_solicitud FOREIGN KEY (id_solicitud)
            REFERENCES solicitud(id_solicitud)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
)


def hp(password):
    return hashlib.sha256(password.encode()).hexdigest()


def _connection_options(include_database=True):
    options = {
        "host": MYSQL_HOST,
        "port": MYSQL_PORT,
        "user": MYSQL_USER,
        "password": MYSQL_PASSWORD,
        "charset": "utf8mb4",
    }
    if include_database:
        options["database"] = MYSQL_DATABASE
    return options


def get_conn():
    return mysql.connector.connect(**_connection_options())


def _execute(conn, query, params=()):
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query.replace("?", "%s"), params)
    return cursor


def _executemany(conn, query, values):
    cursor = conn.cursor()
    cursor.executemany(query.replace("?", "%s"), values)
    return cursor


def _create_database():
    if not re.fullmatch(r"[A-Za-z0-9_]+", MYSQL_DATABASE):
        raise ValueError("MYSQL_DATABASE solo puede contener letras, números y guion bajo.")
    conn = mysql.connector.connect(**_connection_options(include_database=False))
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
    finally:
        conn.close()


def init_db():
    """Crea la base MySQL y agrega datos demo si hace falta."""
    _create_database()
    conn = get_conn()
    try:
        for statement in SCHEMA:
            _execute(conn, statement)

        for nombre in ("Administrador", "Secretario", "Comite", "Investigador"):
            _execute(conn, "INSERT IGNORE INTO rol(nombre) VALUES (?)", (nombre,))
        for nombre in (
            "Proyecto de Investigacion",
            "Ponencia",
            "Publicacion",
            "Monitoria de Investigacion",
        ):
            _execute(
                conn, "INSERT IGNORE INTO tipo_solicitud(nombre) VALUES (?)", (nombre,)
            )

        user_count = _execute(conn, "SELECT COUNT(*) AS total FROM usuario").fetchone()["total"]
        if user_count == 0:
            role_ids = {
                row["nombre"]: row["id_rol"]
                for row in _execute(conn, "SELECT id_rol, nombre FROM rol").fetchall()
            }
            demo_users = [
                ("Administrador", "admin@comite.edu.co", "admin123", "Administrador"),
                ("Secretaria Comite", "secretaria@comite.edu.co", "secre123", "Secretario"),
                ("Miembro Comite", "comite@comite.edu.co", "comite123", "Comite"),
                ("Investigador Demo", "investigador@comite.edu.co", "invest123", "Investigador"),
            ]
            for nombre, correo, password, rol in demo_users:
                cursor = _execute(
                    conn,
                    """INSERT INTO usuario(nombre, correo, password_hash, id_rol)
                       VALUES (?, ?, ?, ?)""",
                    (nombre, correo, hp(password), role_ids[rol]),
                )
                if rol == "Investigador":
                    _execute(
                        conn,
                        "INSERT INTO investigador(id_usuario) VALUES (?)",
                        (cursor.lastrowid,),
                    )

        _execute(
            conn,
            """INSERT INTO investigador(id_usuario)
               SELECT u.id_usuario FROM usuario u
               JOIN rol r ON r.id_rol = u.id_rol
               LEFT JOIN investigador i ON i.id_usuario = u.id_usuario
               WHERE r.nombre = 'Investigador' AND i.id_investigador IS NULL""",
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def login(correo, password):
    conn = get_conn()
    try:
        return _execute(
            conn,
            """SELECT u.id_usuario, u.nombre, u.correo, u.id_rol, r.nombre AS rol
               FROM usuario u JOIN rol r ON u.id_rol = r.id_rol
               WHERE u.correo = ? AND u.password_hash = ?
                 AND COALESCE(u.activo, 1) = 1""",
            (correo, hp(password)),
        ).fetchone()
    finally:
        conn.close()


def listar_usuarios():
    conn = get_conn()
    try:
        return _execute(
            conn,
            """SELECT u.id_usuario, u.nombre, u.correo, r.nombre AS rol
               FROM usuario u JOIN rol r ON u.id_rol = r.id_rol
               ORDER BY u.id_usuario""",
        ).fetchall()
    finally:
        conn.close()


def obtener_usuario(id_usuario):
    conn = get_conn()
    try:
        return _execute(
            conn,
            """SELECT u.id_usuario, u.nombre, u.correo, u.id_rol, r.nombre AS rol
               FROM usuario u JOIN rol r ON u.id_rol = r.id_rol
               WHERE u.id_usuario = ?""",
            (id_usuario,),
        ).fetchone()
    finally:
        conn.close()


def crear_usuario(nombre, correo, password, id_rol):
    if not nombre or not correo or not password:
        return False, "Todos los campos son obligatorios."
    if "@" not in correo:
        return False, "Correo inválido."
    if len(password) < 6:
        return False, "La contraseña debe tener al menos 6 caracteres."

    conn = get_conn()
    try:
        role = _execute(
            conn, "SELECT nombre FROM rol WHERE id_rol = ?", (id_rol,)
        ).fetchone()
        if role is None:
            return False, "Seleccione un rol válido."
        cursor = _execute(
            conn,
            """INSERT INTO usuario(nombre, correo, password_hash, id_rol)
               VALUES (?, ?, ?, ?)""",
            (nombre, correo, hp(password), id_rol),
        )
        if role["nombre"] == "Investigador":
            _execute(
                conn,
                "INSERT INTO investigador(id_usuario) VALUES (?)",
                (cursor.lastrowid,),
            )
        conn.commit()
        return True, "Usuario creado."
    except mysql.connector.IntegrityError:
        conn.rollback()
        return False, "El correo ya existe."
    finally:
        conn.close()


def actualizar_usuario(id_usuario, nombre, correo, id_rol):
    if not nombre or not correo:
        return False, "Nombre y correo obligatorios."
    conn = get_conn()
    try:
        role = _execute(
            conn, "SELECT nombre FROM rol WHERE id_rol = ?", (id_rol,)
        ).fetchone()
        if role is None:
            return False, "Seleccione un rol válido."
        _execute(
            conn,
            "UPDATE usuario SET nombre = ?, correo = ?, id_rol = ? WHERE id_usuario = ?",
            (nombre, correo, id_rol, id_usuario),
        )
        if role["nombre"] == "Investigador":
            _execute(
                conn,
                "INSERT IGNORE INTO investigador(id_usuario) VALUES (?)",
                (id_usuario,),
            )
        conn.commit()
        return True, "Usuario actualizado."
    except mysql.connector.IntegrityError:
        conn.rollback()
        return False, "El correo ya existe."
    finally:
        conn.close()


def eliminar_usuario(id_usuario):
    conn = get_conn()
    try:
        _execute(conn, "DELETE FROM usuario WHERE id_usuario = ?", (id_usuario,))
        conn.commit()
    finally:
        conn.close()


def listar_roles():
    conn = get_conn()
    try:
        return _execute(conn, "SELECT * FROM rol ORDER BY id_rol").fetchall()
    finally:
        conn.close()


def listar_tipos():
    conn = get_conn()
    try:
        return _execute(
            conn, "SELECT * FROM tipo_solicitud ORDER BY id_tipo"
        ).fetchall()
    finally:
        conn.close()


def listar_solicitudes(id_usuario=None):
    conn = get_conn()
    try:
        query = """SELECT s.id_solicitud, s.codigo, s.titulo, s.resumen AS descripcion,
                          s.estado, s.fecha_radicacion AS fecha, s.id_tipo,
                          i.id_usuario, u.nombre AS investigador, t.nombre AS tipo
                   FROM solicitud s
                   JOIN investigador i ON i.id_investigador = s.id_investigador
                   JOIN usuario u ON u.id_usuario = i.id_usuario
                   JOIN tipo_solicitud t ON t.id_tipo = s.id_tipo"""
        params = ()
        if id_usuario is not None:
            query += " WHERE i.id_usuario = ?"
            params = (id_usuario,)
        query += " ORDER BY s.fecha_radicacion DESC"
        return _execute(conn, query, params).fetchall()
    finally:
        conn.close()


def obtener_solicitud(id_solicitud, id_usuario=None):
    solicitudes = listar_solicitudes(id_usuario)
    return next(
        (
            solicitud
            for solicitud in solicitudes
            if solicitud["id_solicitud"] == id_solicitud
        ),
        None,
    )


def _nuevo_codigo(conn):
    n = _execute(conn, "SELECT COUNT(*) AS total FROM solicitud").fetchone()["total"] + 1
    return f"SOL-{n:04d}"


def crear_solicitud(id_usuario, id_tipo, titulo, descripcion):
    if not titulo:
        return False, "El título es obligatorio."
    conn = get_conn()
    try:
        investigador = _execute(
            conn,
            "SELECT id_investigador FROM investigador WHERE id_usuario = ?",
            (id_usuario,),
        ).fetchone()
        if investigador is None:
            return False, "El usuario no tiene un perfil de investigador."
        _execute(
            conn,
            """INSERT INTO solicitud
               (codigo, id_investigador, id_tipo, titulo, resumen)
               VALUES (?, ?, ?, ?, ?)""",
            (
                _nuevo_codigo(conn),
                investigador["id_investigador"],
                id_tipo,
                titulo,
                descripcion,
            ),
        )
        conn.commit()
        return True, "Solicitud creada."
    except mysql.connector.IntegrityError:
        conn.rollback()
        return False, "No fue posible crear la solicitud."
    finally:
        conn.close()


def actualizar_solicitud(id_solicitud, titulo, descripcion, id_tipo, estado):
    if not titulo:
        return False, "El título es obligatorio."
    conn = get_conn()
    try:
        _execute(
            conn,
            """UPDATE solicitud
               SET titulo = ?, resumen = ?, id_tipo = ?, estado = ?
               WHERE id_solicitud = ?""",
            (titulo, descripcion, id_tipo, estado, id_solicitud),
        )
        conn.commit()
        return True, "Solicitud actualizada."
    except mysql.connector.IntegrityError:
        conn.rollback()
        return False, "No fue posible actualizar la solicitud."
    finally:
        conn.close()


def eliminar_solicitud(id_solicitud):
    conn = get_conn()
    try:
        _execute(conn, "DELETE FROM solicitud WHERE id_solicitud = ?", (id_solicitud,))
        conn.commit()
    finally:
        conn.close()
