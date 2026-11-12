"""Acceso a datos y lógica de negocio del Sistema de Gestión del Comité de Investigación."""
from contextlib import contextmanager
from datetime import date, datetime
import hashlib
import os
import re
import uuid

import mysql.connector
import mysql.connector.pooling


MYSQL_HOST = os.environ.get("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "comite_db")

UPLOAD_DIR = os.environ.get(
    "COMITE_UPLOAD_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
)
EXTENSIONES_PERMITIDAS = {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "png", "jpg", "jpeg", "zip", "txt"}

# ---------------------------------------------------------------------------
# Catálogos del flujo
# ---------------------------------------------------------------------------
ESTADOS = [
    "Recibida",
    "En revisión",
    "Pendiente por documentos",
    "Requiere ajustes",
    "Lista para comité",
    "Aprobada",
    "Aprobada con ajustes",
    "Rechazada",
    "Cerrada",
]
# Estados en los que el investigador todavía puede modificar su solicitud.
ESTADOS_EDITABLES = {"Recibida", "Pendiente por documentos", "Requiere ajustes"}
# Estados que ya no requieren seguimiento de fechas.
ESTADOS_FINALES = {"Aprobada", "Aprobada con ajustes", "Rechazada", "Cerrada"}
PRIORIDADES = ["Alta", "Media", "Baja"]
CONCEPTOS = ["Favorable", "Favorable con ajustes", "Desfavorable"]
TIPOS_OBSERVACION = ["General", "Solicitud de ajuste"]
# Decisión del comité -> estado resultante de la solicitud.
DECISIONES = {
    "Aprobada": "Aprobada",
    "Aprobada con ajustes": "Aprobada con ajustes",
    "Rechazada": "Rechazada",
    "Aplazada": "Lista para comité",
}
ESTADOS_SESION = ["Programada", "Realizada", "Cancelada"]
ROLES_GESTION = {"Administrador", "Secretario"}
ROLES_COMITE = ROLES_GESTION | {"Comite"}

TIPOS_Y_REQUISITOS = {
    "Proyecto de Investigacion": [
        ("Formato de propuesta del proyecto", 1),
        ("Presupuesto detallado", 1),
        ("Cronograma de actividades", 1),
        ("Aval del grupo de investigación", 1),
        ("Consentimiento informado (si aplica)", 0),
    ],
    "Ponencia": [
        ("Resumen o abstract de la ponencia", 1),
        ("Carta de aceptación del evento", 1),
        ("Presupuesto de viaje", 0),
    ],
    "Publicacion": [
        ("Manuscrito del artículo", 1),
        ("Carta de originalidad", 1),
        ("Aval del grupo de investigación", 0),
    ],
    "Monitoria de Investigacion": [
        ("Plan de trabajo del monitor", 1),
        ("Carta del docente responsable", 1),
        ("Certificado de notas del estudiante", 1),
    ],
    "Informe final de proyecto": [
        ("Informe final", 1),
        ("Productos o evidencias de resultados", 1),
        ("Paz y salvo de ejecución presupuestal", 0),
    ],
}

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
    # Bitácora de todas las actuaciones sobre una solicitud (trazabilidad).
    """CREATE TABLE IF NOT EXISTS actuacion (
        id_actuacion INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        id_solicitud INT NOT NULL,
        id_usuario INT NULL,
        accion VARCHAR(255) NOT NULL,
        detalle LONGTEXT NULL,
        fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_actuacion_solicitud FOREIGN KEY (id_solicitud)
            REFERENCES solicitud(id_solicitud)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS notificacion (
        id_notificacion INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        id_usuario INT NOT NULL,
        mensaje VARCHAR(1000) NOT NULL,
        enlace VARCHAR(500) NULL,
        leida TINYINT NOT NULL DEFAULT 0,
        fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_notificacion_usuario FOREIGN KEY (id_usuario)
            REFERENCES usuario(id_usuario)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
)

# Columnas agregadas a tablas existentes (para bases creadas con la versión anterior).
MIGRACIONES = (
    ("documento", "id_requisito", "INT NULL"),
    ("documento", "id_usuario", "INT NULL"),
    ("documento", "nombre_original", "VARCHAR(255) NULL"),
    ("acta", "asistentes", "LONGTEXT NULL"),
    ("acta", "id_usuario", "INT NULL"),
)


# ---------------------------------------------------------------------------
# Utilidades de conexión
# ---------------------------------------------------------------------------
def hp(password):
    return hashlib.sha256(password.encode()).hexdigest()


def hoy():
    return date.today().isoformat()


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


_pool = None


def get_conn():
    """Entrega una conexión del pool (reutilizar conexiones hace mucho más rápida cada página)."""
    global _pool
    if _pool is None:
        _pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name="comite", pool_size=10, pool_reset_session=True, **_connection_options()
        )
    try:
        return _pool.get_connection()
    except mysql.connector.errors.PoolError:
        # Pool agotado (muchas peticiones simultáneas): usar una conexión directa.
        return mysql.connector.connect(**_connection_options())


def _execute(conn, query, params=()):
    cursor = conn.cursor(dictionary=True, buffered=True)
    cursor.execute(query.replace("?", "%s"), params)
    return cursor


def _one(conn, query, params=()):
    return _execute(conn, query, params).fetchone()


def _all(conn, query, params=()):
    return _execute(conn, query, params).fetchall()


@contextmanager
def db():
    """Abre una conexión, confirma al final y revierte si ocurre un error."""
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


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


def _migrar(conn):
    for tabla, columna, definicion in MIGRACIONES:
        existe = _one(
            conn,
            """SELECT COUNT(*) AS total FROM information_schema.COLUMNS
               WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? AND COLUMN_NAME = ?""",
            (MYSQL_DATABASE, tabla, columna),
        )["total"]
        if not existe:
            _execute(conn, f"ALTER TABLE `{tabla}` ADD COLUMN `{columna}` {definicion}")


def init_db():
    """Crea la base MySQL, aplica migraciones y agrega datos base si hace falta."""
    _create_database()
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with db() as conn:
        for statement in SCHEMA:
            _execute(conn, statement)
        _migrar(conn)

        for nombre in ("Administrador", "Secretario", "Comite", "Investigador"):
            _execute(conn, "INSERT IGNORE INTO rol(nombre) VALUES (?)", (nombre,))

        for tipo, requisitos in TIPOS_Y_REQUISITOS.items():
            _execute(conn, "INSERT IGNORE INTO tipo_solicitud(nombre) VALUES (?)", (tipo,))
            id_tipo = _one(
                conn, "SELECT id_tipo FROM tipo_solicitud WHERE nombre = ?", (tipo,)
            )["id_tipo"]
            tiene = _one(
                conn, "SELECT COUNT(*) AS total FROM requisito WHERE id_tipo = ?", (id_tipo,)
            )["total"]
            if not tiene:
                for nombre, obligatorio in requisitos:
                    _execute(
                        conn,
                        "INSERT INTO requisito(id_tipo, nombre, obligatorio) VALUES (?, ?, ?)",
                        (id_tipo, nombre, obligatorio),
                    )

        user_count = _one(conn, "SELECT COUNT(*) AS total FROM usuario")["total"]
        if user_count == 0:
            role_ids = {
                row["nombre"]: row["id_rol"]
                for row in _all(conn, "SELECT id_rol, nombre FROM rol")
            }
            demo_users = [
                ("Administrador", "admin@comite.edu.co", "admin123", "Administrador"),
                ("Secretaria Comite", "secretaria@comite.edu.co", "secre123", "Secretario"),
                ("Miembro Comite", "comite@comite.edu.co", "comite123", "Comite"),
                ("Investigador Demo", "investigador@comite.edu.co", "invest123", "Investigador"),
            ]
            for nombre, correo, password, rol in demo_users:
                _execute(
                    conn,
                    """INSERT INTO usuario(nombre, correo, password_hash, id_rol)
                       VALUES (?, ?, ?, ?)""",
                    (nombre, correo, hp(password), role_ids[rol]),
                )

        _execute(
            conn,
            """INSERT INTO investigador(id_usuario)
               SELECT u.id_usuario FROM usuario u
               JOIN rol r ON r.id_rol = u.id_rol
               LEFT JOIN investigador i ON i.id_usuario = u.id_usuario
               WHERE r.nombre = 'Investigador' AND i.id_investigador IS NULL""",
        )


# ---------------------------------------------------------------------------
# Notificaciones y trazabilidad (se llaman dentro de otras transacciones)
# ---------------------------------------------------------------------------
def notificar(conn, id_usuario, mensaje, enlace=None):
    if id_usuario:
        _execute(
            conn,
            "INSERT INTO notificacion(id_usuario, mensaje, enlace) VALUES (?, ?, ?)",
            (id_usuario, mensaje[:1000], enlace),
        )


def notificar_roles(conn, roles, mensaje, enlace=None, excepto=None):
    marcadores = ", ".join("?" for _ in roles)
    usuarios = _all(
        conn,
        f"""SELECT u.id_usuario FROM usuario u JOIN rol r ON r.id_rol = u.id_rol
            WHERE r.nombre IN ({marcadores}) AND u.activo = 1""",
        tuple(roles),
    )
    for fila in usuarios:
        if fila["id_usuario"] != excepto:
            notificar(conn, fila["id_usuario"], mensaje, enlace)


def registrar_actuacion(conn, id_solicitud, id_usuario, accion, detalle=None):
    _execute(
        conn,
        "INSERT INTO actuacion(id_solicitud, id_usuario, accion, detalle) VALUES (?, ?, ?, ?)",
        (id_solicitud, id_usuario, accion, detalle),
    )


def _id_usuario_investigador(conn, id_solicitud):
    fila = _one(
        conn,
        """SELECT i.id_usuario, s.codigo FROM solicitud s
           JOIN investigador i ON i.id_investigador = s.id_investigador
           WHERE s.id_solicitud = ?""",
        (id_solicitud,),
    )
    return fila


def _cambiar_estado(conn, id_solicitud, nuevo, id_usuario, comentario=None, notificar_investigador=True):
    actual = _one(conn, "SELECT estado, codigo FROM solicitud WHERE id_solicitud = ?", (id_solicitud,))
    if actual is None or actual["estado"] == nuevo:
        return
    _execute(conn, "UPDATE solicitud SET estado = ? WHERE id_solicitud = ?", (nuevo, id_solicitud))
    _execute(
        conn,
        """INSERT INTO historial_estado
           (id_solicitud, estado_anterior, estado_nuevo, id_usuario, comentario)
           VALUES (?, ?, ?, ?, ?)""",
        (id_solicitud, actual["estado"], nuevo, id_usuario, comentario),
    )
    detalle = f"{actual['estado']} → {nuevo}"
    if comentario:
        detalle += f". {comentario}"
    registrar_actuacion(conn, id_solicitud, id_usuario, "Cambio de estado", detalle)
    if notificar_investigador:
        inv = _id_usuario_investigador(conn, id_solicitud)
        if inv and inv["id_usuario"] != id_usuario:
            notificar(
                conn,
                inv["id_usuario"],
                f"Su solicitud {actual['codigo']} cambió a «{nuevo}».",
                f"/solicitudes/{id_solicitud}",
            )


# ---------------------------------------------------------------------------
# Usuarios, roles e investigadores
# ---------------------------------------------------------------------------
def login(correo, password):
    with db() as conn:
        return _one(
            conn,
            """SELECT u.id_usuario, u.nombre, u.correo, u.id_rol, r.nombre AS rol
               FROM usuario u JOIN rol r ON u.id_rol = r.id_rol
               WHERE u.correo = ? AND u.password_hash = ? AND u.activo = 1""",
            (correo, hp(password)),
        )


def listar_usuarios():
    with db() as conn:
        return _all(
            conn,
            """SELECT u.id_usuario, u.nombre, u.correo, u.activo, r.nombre AS rol
               FROM usuario u JOIN rol r ON u.id_rol = r.id_rol
               ORDER BY u.id_usuario""",
        )


def usuarios_por_rol(*roles):
    marcadores = ", ".join("?" for _ in roles)
    with db() as conn:
        return _all(
            conn,
            f"""SELECT u.id_usuario, u.nombre, r.nombre AS rol FROM usuario u
                JOIN rol r ON r.id_rol = u.id_rol
                WHERE r.nombre IN ({marcadores}) AND u.activo = 1 ORDER BY u.nombre""",
            tuple(roles),
        )


def obtener_usuario(id_usuario):
    with db() as conn:
        return _one(
            conn,
            """SELECT u.id_usuario, u.nombre, u.correo, u.id_rol, u.activo, r.nombre AS rol
               FROM usuario u JOIN rol r ON u.id_rol = r.id_rol
               WHERE u.id_usuario = ?""",
            (id_usuario,),
        )


def _validar_datos_usuario(nombre, correo, password, requerir_password):
    if not nombre or not correo:
        return "Nombre y correo son obligatorios."
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", correo):
        return "Correo inválido."
    if requerir_password and not password:
        return "La contraseña es obligatoria."
    if password and len(password) < 6:
        return "La contraseña debe tener al menos 6 caracteres."
    return None


def crear_usuario(nombre, correo, password, id_rol):
    error = _validar_datos_usuario(nombre, correo, password, True)
    if error:
        return False, error
    try:
        with db() as conn:
            role = _one(conn, "SELECT nombre FROM rol WHERE id_rol = ?", (id_rol,))
            if role is None:
                return False, "Seleccione un rol válido."
            cursor = _execute(
                conn,
                """INSERT INTO usuario(nombre, correo, password_hash, id_rol)
                   VALUES (?, ?, ?, ?)""",
                (nombre, correo, hp(password), id_rol),
            )
            if role["nombre"] == "Investigador":
                _execute(conn, "INSERT INTO investigador(id_usuario) VALUES (?)", (cursor.lastrowid,))
        return True, "Usuario creado."
    except mysql.connector.IntegrityError:
        return False, "El correo ya existe."


def registrar_investigador(nombre, correo, password, documento, programa, facultad, telefono):
    """Registro público de investigadores."""
    error = _validar_datos_usuario(nombre, correo, password, True)
    if error:
        return False, error
    if not documento:
        return False, "El documento de identidad es obligatorio."
    try:
        with db() as conn:
            id_rol = _one(conn, "SELECT id_rol FROM rol WHERE nombre = 'Investigador'")["id_rol"]
            cursor = _execute(
                conn,
                """INSERT INTO usuario(nombre, correo, password_hash, id_rol)
                   VALUES (?, ?, ?, ?)""",
                (nombre, correo, hp(password), id_rol),
            )
            id_usuario = cursor.lastrowid
            _execute(
                conn,
                """INSERT INTO investigador(id_usuario, documento, programa, facultad, telefono)
                   VALUES (?, ?, ?, ?, ?)""",
                (id_usuario, documento, programa or None, facultad or None, telefono or None),
            )
            notificar_roles(
                conn,
                ROLES_GESTION,
                f"Nuevo investigador registrado: {nombre}.",
                "/investigadores",
            )
        return True, "Registro exitoso. Ya puede iniciar sesión."
    except mysql.connector.IntegrityError:
        return False, "El correo o el documento ya están registrados."


def actualizar_usuario(id_usuario, nombre, correo, id_rol, password=None, activo=1):
    error = _validar_datos_usuario(nombre, correo, password, False)
    if error:
        return False, error
    try:
        with db() as conn:
            role = _one(conn, "SELECT nombre FROM rol WHERE id_rol = ?", (id_rol,))
            if role is None:
                return False, "Seleccione un rol válido."
            _execute(
                conn,
                """UPDATE usuario SET nombre = ?, correo = ?, id_rol = ?, activo = ?
                   WHERE id_usuario = ?""",
                (nombre, correo, id_rol, 1 if activo else 0, id_usuario),
            )
            if password:
                _execute(
                    conn,
                    "UPDATE usuario SET password_hash = ? WHERE id_usuario = ?",
                    (hp(password), id_usuario),
                )
            if role["nombre"] == "Investigador":
                _execute(conn, "INSERT IGNORE INTO investigador(id_usuario) VALUES (?)", (id_usuario,))
        return True, "Usuario actualizado."
    except mysql.connector.IntegrityError:
        return False, "El correo ya existe."


def eliminar_usuario(id_usuario):
    """Elimina el usuario; si tiene registros asociados, lo desactiva para conservar la trazabilidad."""
    try:
        with db() as conn:
            _execute(conn, "DELETE FROM notificacion WHERE id_usuario = ?", (id_usuario,))
            _execute(conn, "DELETE FROM investigador WHERE id_usuario = ?", (id_usuario,))
            _execute(conn, "DELETE FROM usuario WHERE id_usuario = ?", (id_usuario,))
        return "Usuario eliminado."
    except mysql.connector.IntegrityError:
        with db() as conn:
            _execute(conn, "UPDATE usuario SET activo = 0 WHERE id_usuario = ?", (id_usuario,))
        return "El usuario tiene registros asociados; se desactivó para conservar el historial."


def listar_roles():
    with db() as conn:
        return _all(conn, "SELECT * FROM rol ORDER BY id_rol")


def obtener_perfil(id_usuario):
    with db() as conn:
        return _one(
            conn,
            """SELECT u.id_usuario, u.nombre, u.correo, r.nombre AS rol,
                      i.documento, i.programa, i.facultad, i.telefono
               FROM usuario u JOIN rol r ON r.id_rol = u.id_rol
               LEFT JOIN investigador i ON i.id_usuario = u.id_usuario
               WHERE u.id_usuario = ?""",
            (id_usuario,),
        )


def actualizar_perfil(id_usuario, nombre, documento, programa, facultad, telefono, password=None):
    if not nombre:
        return False, "El nombre es obligatorio."
    if password and len(password) < 6:
        return False, "La contraseña debe tener al menos 6 caracteres."
    try:
        with db() as conn:
            _execute(conn, "UPDATE usuario SET nombre = ? WHERE id_usuario = ?", (nombre, id_usuario))
            if password:
                _execute(
                    conn,
                    "UPDATE usuario SET password_hash = ? WHERE id_usuario = ?",
                    (hp(password), id_usuario),
                )
            _execute(
                conn,
                """UPDATE investigador SET documento = ?, programa = ?, facultad = ?, telefono = ?
                   WHERE id_usuario = ?""",
                (documento or None, programa or None, facultad or None, telefono or None, id_usuario),
            )
        return True, "Perfil actualizado."
    except mysql.connector.IntegrityError:
        return False, "El documento ya está registrado por otro investigador."


def listar_investigadores(q=None):
    query = """SELECT u.id_usuario, u.nombre, u.correo, u.activo, i.documento, i.programa,
                      i.facultad, i.telefono, COUNT(s.id_solicitud) AS solicitudes,
                      SUM(s.estado IN ('Aprobada', 'Aprobada con ajustes')) AS aprobadas
               FROM investigador i
               JOIN usuario u ON u.id_usuario = i.id_usuario
               LEFT JOIN solicitud s ON s.id_investigador = i.id_investigador"""
    params = ()
    if q:
        query += " WHERE u.nombre LIKE ? OR u.correo LIKE ? OR i.documento LIKE ? OR i.programa LIKE ?"
        patron = f"%{q}%"
        params = (patron, patron, patron, patron)
    query += " GROUP BY u.id_usuario, u.nombre, u.correo, u.activo, i.documento, i.programa, i.facultad, i.telefono ORDER BY u.nombre"
    with db() as conn:
        return _all(conn, query, params)


# ---------------------------------------------------------------------------
# Tipos de solicitud y requisitos
# ---------------------------------------------------------------------------
def listar_tipos():
    with db() as conn:
        tipos = _all(conn, "SELECT * FROM tipo_solicitud WHERE activo = 1 ORDER BY nombre")
        for tipo in tipos:
            tipo["requisitos"] = _all(
                conn,
                "SELECT * FROM requisito WHERE id_tipo = ? ORDER BY obligatorio DESC, id_requisito",
                (tipo["id_tipo"],),
            )
        return tipos


# ---------------------------------------------------------------------------
# Solicitudes
# ---------------------------------------------------------------------------
_SELECT_SOLICITUD = """SELECT s.id_solicitud, s.codigo, s.titulo, s.resumen AS descripcion,
                              s.estado, s.prioridad, s.fecha_limite,
                              s.fecha_radicacion AS fecha, s.id_tipo,
                              i.id_usuario, i.documento, i.programa, i.facultad, i.telefono,
                              u.nombre AS investigador, u.correo AS correo_investigador,
                              t.nombre AS tipo,
                              (SELECT GROUP_CONCAT(ur.nombre SEPARATOR ', ')
                                 FROM asignacion_revision a
                                 JOIN usuario ur ON ur.id_usuario = a.id_usuario
                                WHERE a.id_solicitud = s.id_solicitud) AS responsables
                       FROM solicitud s
                       JOIN investigador i ON i.id_investigador = s.id_investigador
                       JOIN usuario u ON u.id_usuario = i.id_usuario
                       JOIN tipo_solicitud t ON t.id_tipo = s.id_tipo"""


def _marcar_vencida(solicitud):
    solicitud["vencida"] = bool(
        solicitud.get("fecha_limite")
        and solicitud["fecha_limite"] < hoy()
        and solicitud["estado"] not in ESTADOS_FINALES
    )
    return solicitud


def listar_solicitudes(id_usuario=None, estado=None, id_tipo=None, q=None, solo_vencidas=False,
                       id_revisor=None, desde=None, hasta=None):
    condiciones, params = [], []
    if id_usuario is not None:
        condiciones.append("i.id_usuario = ?")
        params.append(id_usuario)
    if estado:
        condiciones.append("s.estado = ?")
        params.append(estado)
    if id_tipo:
        condiciones.append("s.id_tipo = ?")
        params.append(id_tipo)
    if q:
        condiciones.append("(s.codigo LIKE ? OR s.titulo LIKE ? OR u.nombre LIKE ?)")
        params += [f"%{q}%"] * 3
    if solo_vencidas:
        condiciones.append(
            "s.fecha_limite IS NOT NULL AND s.fecha_limite <> '' AND s.fecha_limite < ? "
            "AND s.estado NOT IN ('Aprobada', 'Aprobada con ajustes', 'Rechazada', 'Cerrada')"
        )
        params.append(hoy())
    if id_revisor:
        condiciones.append(
            "EXISTS (SELECT 1 FROM asignacion_revision a WHERE a.id_solicitud = s.id_solicitud AND a.id_usuario = ?)"
        )
        params.append(id_revisor)
    if desde:
        condiciones.append("s.fecha_radicacion >= ?")
        params.append(desde)
    if hasta:
        condiciones.append("s.fecha_radicacion < DATE_ADD(?, INTERVAL 1 DAY)")
        params.append(hasta)
    query = _SELECT_SOLICITUD
    if condiciones:
        query += " WHERE " + " AND ".join(condiciones)
    query += " ORDER BY s.fecha_radicacion DESC, s.id_solicitud DESC"
    with db() as conn:
        return [_marcar_vencida(s) for s in _all(conn, query, tuple(params))]


def obtener_solicitud(id_solicitud, id_usuario=None):
    query = _SELECT_SOLICITUD + " WHERE s.id_solicitud = ?"
    params = [id_solicitud]
    if id_usuario is not None:
        query += " AND i.id_usuario = ?"
        params.append(id_usuario)
    with db() as conn:
        solicitud = _one(conn, query, tuple(params))
    return _marcar_vencida(solicitud) if solicitud else None


def _nuevo_codigo(conn):
    anio = date.today().year
    fila = _one(
        conn,
        "SELECT codigo FROM solicitud WHERE codigo LIKE ? ORDER BY id_solicitud DESC LIMIT 1",
        (f"SOL-{anio}-%",),
    )
    consecutivo = 1
    if fila:
        try:
            consecutivo = int(fila["codigo"].rsplit("-", 1)[1]) + 1
        except (ValueError, IndexError):
            consecutivo = _one(conn, "SELECT COUNT(*) AS total FROM solicitud")["total"] + 1
    codigo = f"SOL-{anio}-{consecutivo:04d}"
    while _one(conn, "SELECT 1 AS existe FROM solicitud WHERE codigo = ?", (codigo,)):
        consecutivo += 1
        codigo = f"SOL-{anio}-{consecutivo:04d}"
    return codigo


def crear_solicitud(id_usuario, id_tipo, titulo, descripcion, prioridad="Media", fecha_limite=None):
    """Radica una solicitud. Retorna (ok, mensaje, id_solicitud)."""
    if not titulo:
        return False, "El título es obligatorio.", None
    if prioridad not in PRIORIDADES:
        prioridad = "Media"
    try:
        with db() as conn:
            investigador = _one(
                conn, "SELECT id_investigador FROM investigador WHERE id_usuario = ?", (id_usuario,)
            )
            if investigador is None:
                return False, "Solo los usuarios con perfil de investigador pueden radicar solicitudes.", None
            codigo = _nuevo_codigo(conn)
            cursor = _execute(
                conn,
                """INSERT INTO solicitud
                   (codigo, id_investigador, id_tipo, titulo, resumen, prioridad, fecha_limite)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (codigo, investigador["id_investigador"], id_tipo, titulo, descripcion,
                 prioridad, fecha_limite or None),
            )
            id_solicitud = cursor.lastrowid
            _execute(
                conn,
                """INSERT INTO historial_estado (id_solicitud, estado_anterior, estado_nuevo, id_usuario, comentario)
                   VALUES (?, NULL, 'Recibida', ?, 'Radicación de la solicitud')""",
                (id_solicitud, id_usuario),
            )
            registrar_actuacion(conn, id_solicitud, id_usuario, "Radicación", f"Solicitud {codigo} radicada.")
            notificar_roles(
                conn,
                ROLES_GESTION,
                f"Nueva solicitud radicada: {codigo} – {titulo}.",
                f"/solicitudes/{id_solicitud}",
            )
        return True, f"Solicitud {codigo} radicada. Ahora cargue los documentos requeridos.", id_solicitud
    except mysql.connector.IntegrityError:
        return False, "No fue posible radicar la solicitud.", None


def actualizar_solicitud(id_solicitud, titulo, descripcion, id_tipo, prioridad, fecha_limite, id_usuario):
    if not titulo:
        return False, "El título es obligatorio."
    if prioridad not in PRIORIDADES:
        prioridad = "Media"
    with db() as conn:
        _execute(
            conn,
            """UPDATE solicitud SET titulo = ?, resumen = ?, id_tipo = ?, prioridad = ?, fecha_limite = ?
               WHERE id_solicitud = ?""",
            (titulo, descripcion, id_tipo, prioridad, fecha_limite or None, id_solicitud),
        )
        registrar_actuacion(conn, id_solicitud, id_usuario, "Edición", "Se actualizaron los datos de la solicitud.")
    return True, "Solicitud actualizada."


def cambiar_estado(id_solicitud, nuevo, id_usuario, comentario=None):
    if nuevo not in ESTADOS:
        return False, "Estado no válido."
    with db() as conn:
        _cambiar_estado(conn, id_solicitud, nuevo, id_usuario, comentario)
    return True, f"Estado actualizado a «{nuevo}»."


def eliminar_solicitud(id_solicitud):
    with db() as conn:
        rutas = [d["ruta"] for d in _all(conn, "SELECT ruta FROM documento WHERE id_solicitud = ?", (id_solicitud,))]
        for tabla in ("agenda_sesion", "decision", "validacion_requisito", "asignacion_revision",
                      "revision", "observacion", "documento", "historial_estado", "actuacion"):
            _execute(conn, f"DELETE FROM {tabla} WHERE id_solicitud = ?", (id_solicitud,))
        _execute(conn, "DELETE FROM solicitud WHERE id_solicitud = ?", (id_solicitud,))
    for ruta in rutas:
        if ruta:
            try:
                os.remove(os.path.join(UPLOAD_DIR, ruta))
            except OSError:
                pass


def historial(id_solicitud):
    with db() as conn:
        return _all(
            conn,
            """SELECT a.fecha, a.accion, a.detalle, u.nombre AS usuario
               FROM actuacion a LEFT JOIN usuario u ON u.id_usuario = a.id_usuario
               WHERE a.id_solicitud = ? ORDER BY a.fecha DESC, a.id_actuacion DESC""",
            (id_solicitud,),
        )


def historial_estados(id_solicitud):
    with db() as conn:
        return _all(
            conn,
            """SELECT h.*, u.nombre AS usuario FROM historial_estado h
               LEFT JOIN usuario u ON u.id_usuario = h.id_usuario
               WHERE h.id_solicitud = ? ORDER BY h.fecha, h.id_historial""",
            (id_solicitud,),
        )


# ---------------------------------------------------------------------------
# Documentos
# ---------------------------------------------------------------------------
def extension_permitida(nombre):
    return "." in nombre and nombre.rsplit(".", 1)[1].lower() in EXTENSIONES_PERMITIDAS


def guardar_documento(id_solicitud, id_requisito, archivo, nombre_seguro, id_usuario):
    """Guarda el archivo en disco y registra una nueva versión del documento."""
    if not nombre_seguro or not extension_permitida(nombre_seguro):
        return False, "Tipo de archivo no permitido. Use: " + ", ".join(sorted(EXTENSIONES_PERMITIDAS)) + "."
    carpeta = os.path.join(UPLOAD_DIR, str(id_solicitud))
    os.makedirs(carpeta, exist_ok=True)
    nombre_disco = f"{uuid.uuid4().hex[:10]}_{nombre_seguro}"
    archivo.save(os.path.join(carpeta, nombre_disco))
    with db() as conn:
        requisito = None
        if id_requisito:
            requisito = _one(conn, "SELECT nombre FROM requisito WHERE id_requisito = ?", (id_requisito,))
        tipo_doc = requisito["nombre"] if requisito else "Documento adicional"
        version = _one(
            conn,
            """SELECT COALESCE(MAX(version), 0) + 1 AS v FROM documento
               WHERE id_solicitud = ? AND COALESCE(id_requisito, 0) = ?""",
            (id_solicitud, id_requisito or 0),
        )["v"]
        _execute(
            conn,
            """INSERT INTO documento
               (id_solicitud, nombre, ruta, tipo, version, id_requisito, id_usuario, nombre_original)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (id_solicitud, nombre_seguro, f"{id_solicitud}/{nombre_disco}", tipo_doc, version,
             id_requisito or None, id_usuario, nombre_seguro),
        )
        registrar_actuacion(
            conn, id_solicitud, id_usuario, "Carga de documento", f"{tipo_doc}: {nombre_seguro} (versión {version})"
        )
        inv = _id_usuario_investigador(conn, id_solicitud)
        if inv and inv["id_usuario"] == id_usuario:
            notificar_roles(
                conn, ROLES_GESTION,
                f"Se cargó un documento en la solicitud {inv['codigo']}.",
                f"/solicitudes/{id_solicitud}",
            )
    return True, f"Documento cargado (versión {version})."


def listar_documentos(id_solicitud):
    with db() as conn:
        return _all(
            conn,
            """SELECT d.*, u.nombre AS usuario FROM documento d
               LEFT JOIN usuario u ON u.id_usuario = d.id_usuario
               WHERE d.id_solicitud = ? ORDER BY d.tipo, d.version DESC""",
            (id_solicitud,),
        )


def obtener_documento(id_documento):
    with db() as conn:
        return _one(conn, "SELECT * FROM documento WHERE id_documento = ?", (id_documento,))


# ---------------------------------------------------------------------------
# Validación de requisitos
# ---------------------------------------------------------------------------
def estado_requisitos(id_solicitud):
    """Requisitos del tipo de la solicitud con su última validación y documentos cargados."""
    with db() as conn:
        return _all(
            conn,
            """SELECT r.id_requisito, r.nombre, r.obligatorio,
                      (SELECT COUNT(*) FROM documento d
                        WHERE d.id_solicitud = s.id_solicitud AND d.id_requisito = r.id_requisito) AS documentos,
                      v.cumple, v.observacion, v.fecha AS fecha_validacion, uv.nombre AS validado_por
               FROM solicitud s
               JOIN requisito r ON r.id_tipo = s.id_tipo
               LEFT JOIN validacion_requisito v ON v.id_validacion = (
                    SELECT MAX(v2.id_validacion) FROM validacion_requisito v2
                     WHERE v2.id_solicitud = s.id_solicitud AND v2.id_requisito = r.id_requisito)
               LEFT JOIN usuario uv ON uv.id_usuario = v.id_usuario_valida
               WHERE s.id_solicitud = ?
               ORDER BY r.obligatorio DESC, r.id_requisito""",
            (id_solicitud,),
        )


def validar_requisitos(id_solicitud, resultados, id_usuario):
    """resultados: {id_requisito: (cumple: bool, observacion: str)}."""
    requisitos = estado_requisitos(id_solicitud)
    if not requisitos:
        return False, "Este tipo de solicitud no tiene requisitos configurados."
    faltantes = []
    with db() as conn:
        for req in requisitos:
            cumple, observacion = resultados.get(req["id_requisito"], (False, ""))
            _execute(
                conn,
                """INSERT INTO validacion_requisito
                   (id_solicitud, id_requisito, cumple, observacion, id_usuario_valida)
                   VALUES (?, ?, ?, ?, ?)""",
                (id_solicitud, req["id_requisito"], 1 if cumple else 0, observacion or None, id_usuario),
            )
            if req["obligatorio"] and not cumple:
                faltantes.append(req["nombre"] + (f" ({observacion})" if observacion else ""))
        if faltantes:
            detalle = "Requisitos pendientes: " + "; ".join(faltantes)
            registrar_actuacion(conn, id_solicitud, id_usuario, "Validación de requisitos", "Incompleta. " + detalle)
            _cambiar_estado(conn, id_solicitud, "Pendiente por documentos", id_usuario, detalle)
            mensaje = "Validación registrada: faltan requisitos obligatorios. Se notificó al investigador."
        else:
            registrar_actuacion(conn, id_solicitud, id_usuario, "Validación de requisitos",
                                "Completa. Todos los requisitos obligatorios cumplen.")
            _cambiar_estado(conn, id_solicitud, "En revisión", id_usuario, "Requisitos completos")
            mensaje = "Validación registrada: requisitos completos. La solicitud pasó a «En revisión»."
    return True, mensaje


# ---------------------------------------------------------------------------
# Asignación de responsables y revisiones del comité
# ---------------------------------------------------------------------------
def listar_asignaciones(id_solicitud):
    with db() as conn:
        filas = _all(
            conn,
            """SELECT a.*, u.nombre AS revisor FROM asignacion_revision a
               JOIN usuario u ON u.id_usuario = a.id_usuario
               WHERE a.id_solicitud = ? ORDER BY a.fecha_asignacion""",
            (id_solicitud,),
        )
    for fila in filas:
        fila["vencida"] = bool(fila["fecha_limite"] and fila["estado"] == "Pendiente" and fila["fecha_limite"] < hoy())
    return filas


def asignar_revisor(id_solicitud, id_revisor, fecha_limite, id_usuario):
    with db() as conn:
        revisor = _one(
            conn,
            """SELECT u.nombre FROM usuario u JOIN rol r ON r.id_rol = u.id_rol
               WHERE u.id_usuario = ? AND r.nombre IN ('Comite', 'Secretario', 'Administrador')""",
            (id_revisor,),
        )
        if revisor is None:
            return False, "Seleccione un integrante del comité válido."
        existe = _one(
            conn,
            "SELECT id_asignacion FROM asignacion_revision WHERE id_solicitud = ? AND id_usuario = ? AND estado = 'Pendiente'",
            (id_solicitud, id_revisor),
        )
        if existe:
            return False, "Ese integrante ya tiene una revisión pendiente de esta solicitud."
        _execute(
            conn,
            "INSERT INTO asignacion_revision(id_solicitud, id_usuario, fecha_limite) VALUES (?, ?, ?)",
            (id_solicitud, id_revisor, fecha_limite or None),
        )
        codigo = _one(conn, "SELECT codigo, estado FROM solicitud WHERE id_solicitud = ?", (id_solicitud,))
        detalle = f"Responsable: {revisor['nombre']}" + (f", fecha límite {fecha_limite}" if fecha_limite else "")
        registrar_actuacion(conn, id_solicitud, id_usuario, "Asignación de responsable", detalle)
        notificar(
            conn, id_revisor,
            f"Se le asignó la revisión de la solicitud {codigo['codigo']}"
            + (f" (fecha límite {fecha_limite})." if fecha_limite else "."),
            f"/solicitudes/{id_solicitud}",
        )
        if codigo["estado"] == "Recibida":
            _cambiar_estado(conn, id_solicitud, "En revisión", id_usuario, "Asignación de responsable")
    return True, f"Revisión asignada a {revisor['nombre']}."


def es_revisor(id_solicitud, id_usuario):
    with db() as conn:
        return bool(_one(
            conn,
            "SELECT 1 AS si FROM asignacion_revision WHERE id_solicitud = ? AND id_usuario = ?",
            (id_solicitud, id_usuario),
        ))


def listar_revisiones(id_solicitud):
    with db() as conn:
        return _all(
            conn,
            """SELECT r.*, u.nombre AS revisor FROM revision r
               JOIN usuario u ON u.id_usuario = r.id_usuario
               WHERE r.id_solicitud = ? ORDER BY r.fecha DESC, r.id_revision DESC""",
            (id_solicitud,),
        )


def registrar_revision(id_solicitud, id_usuario, concepto, observacion):
    if concepto not in CONCEPTOS:
        return False, "Seleccione un concepto válido."
    with db() as conn:
        _execute(
            conn,
            "INSERT INTO revision(id_solicitud, id_usuario, concepto, observacion) VALUES (?, ?, ?, ?)",
            (id_solicitud, id_usuario, concepto, observacion or None),
        )
        _execute(
            conn,
            """UPDATE asignacion_revision SET estado = 'Completada'
               WHERE id_solicitud = ? AND id_usuario = ? AND estado = 'Pendiente'""",
            (id_solicitud, id_usuario),
        )
        registrar_actuacion(conn, id_solicitud, id_usuario, "Revisión del comité",
                            f"Concepto: {concepto}" + (f". {observacion}" if observacion else ""))
        codigo = _one(conn, "SELECT codigo FROM solicitud WHERE id_solicitud = ?", (id_solicitud,))["codigo"]
        notificar_roles(conn, ROLES_GESTION, f"Nuevo concepto ({concepto}) en la solicitud {codigo}.",
                        f"/solicitudes/{id_solicitud}", excepto=id_usuario)
    return True, "Revisión registrada."


def mis_asignaciones(id_usuario):
    with db() as conn:
        filas = _all(
            conn,
            """SELECT a.*, s.codigo, s.titulo, s.estado AS estado_solicitud FROM asignacion_revision a
               JOIN solicitud s ON s.id_solicitud = a.id_solicitud
               WHERE a.id_usuario = ? AND a.estado = 'Pendiente'
               ORDER BY (a.fecha_limite IS NULL), a.fecha_limite""",
            (id_usuario,),
        )
    for fila in filas:
        fila["vencida"] = bool(fila["fecha_limite"] and fila["fecha_limite"] < hoy())
    return filas


# ---------------------------------------------------------------------------
# Observaciones y solicitudes de ajuste
# ---------------------------------------------------------------------------
def listar_observaciones(id_solicitud):
    with db() as conn:
        return _all(
            conn,
            """SELECT o.*, u.nombre AS usuario, r.nombre AS rol FROM observacion o
               JOIN usuario u ON u.id_usuario = o.id_usuario
               JOIN rol r ON r.id_rol = u.id_rol
               WHERE o.id_solicitud = ? ORDER BY o.fecha DESC, o.id_observacion DESC""",
            (id_solicitud,),
        )


def agregar_observacion(id_solicitud, id_usuario, descripcion, tipo, puede_pedir_ajustes):
    if not descripcion:
        return False, "Escriba la observación."
    if tipo not in TIPOS_OBSERVACION or (tipo == "Solicitud de ajuste" and not puede_pedir_ajustes):
        tipo = "General"
    with db() as conn:
        _execute(
            conn,
            "INSERT INTO observacion(id_solicitud, id_usuario, descripcion, tipo) VALUES (?, ?, ?, ?)",
            (id_solicitud, id_usuario, descripcion, tipo),
        )
        registrar_actuacion(conn, id_solicitud, id_usuario,
                            "Solicitud de ajustes" if tipo == "Solicitud de ajuste" else "Observación", descripcion)
        inv = _id_usuario_investigador(conn, id_solicitud)
        if tipo == "Solicitud de ajuste":
            _cambiar_estado(conn, id_solicitud, "Requiere ajustes", id_usuario, "Se solicitaron ajustes")
            return True, "Se solicitaron ajustes al investigador."
        if inv and inv["id_usuario"] != id_usuario:
            notificar(conn, inv["id_usuario"], f"Nueva observación en su solicitud {inv['codigo']}.",
                      f"/solicitudes/{id_solicitud}")
        elif inv:
            notificar_roles(conn, ROLES_GESTION, f"El investigador comentó la solicitud {inv['codigo']}.",
                            f"/solicitudes/{id_solicitud}")
    return True, "Observación registrada."


def responder_ajustes(id_solicitud, id_usuario, comentario):
    """El investigador indica que atendió los ajustes o completó los documentos."""
    with db() as conn:
        solicitud = _one(conn, "SELECT estado, codigo FROM solicitud WHERE id_solicitud = ?", (id_solicitud,))
        if solicitud["estado"] not in ("Requiere ajustes", "Pendiente por documentos"):
            return False, "La solicitud no tiene ajustes ni documentos pendientes."
        _execute(
            conn,
            "UPDATE observacion SET atendida = 1 WHERE id_solicitud = ? AND tipo = 'Solicitud de ajuste'",
            (id_solicitud,),
        )
        if comentario:
            _execute(
                conn,
                "INSERT INTO observacion(id_solicitud, id_usuario, descripcion, tipo, atendida) VALUES (?, ?, ?, 'Respuesta del investigador', 1)",
                (id_solicitud, id_usuario, comentario),
            )
        nuevo = "En revisión" if solicitud["estado"] == "Requiere ajustes" else "Recibida"
        registrar_actuacion(conn, id_solicitud, id_usuario, "Respuesta del investigador",
                            comentario or "El investigador reenvió la solicitud.")
        _cambiar_estado(conn, id_solicitud, nuevo, id_usuario, "Reenvío del investigador", notificar_investigador=False)
        notificar_roles(conn, ROLES_GESTION, f"El investigador reenvió la solicitud {solicitud['codigo']}.",
                        f"/solicitudes/{id_solicitud}")
        for fila in _all(conn, "SELECT DISTINCT id_usuario FROM asignacion_revision WHERE id_solicitud = ?",
                         (id_solicitud,)):
            notificar(conn, fila["id_usuario"], f"La solicitud {solicitud['codigo']} fue ajustada por el investigador.",
                      f"/solicitudes/{id_solicitud}")
    return True, "Solicitud reenviada al comité."


# ---------------------------------------------------------------------------
# Sesiones del comité, agenda y decisiones
# ---------------------------------------------------------------------------
def listar_sesiones():
    with db() as conn:
        return _all(
            conn,
            """SELECT se.*, (SELECT COUNT(*) FROM agenda_sesion a WHERE a.id_sesion = se.id_sesion) AS items,
                      (SELECT COUNT(*) FROM decision d WHERE d.id_sesion = se.id_sesion) AS decisiones,
                      ac.id_acta, ac.numero AS numero_acta
               FROM sesion_comite se LEFT JOIN acta ac ON ac.id_sesion = se.id_sesion
               ORDER BY se.fecha DESC, se.hora DESC""",
        )


def proximas_sesiones(limite=5):
    with db() as conn:
        return _all(
            conn,
            """SELECT se.*, (SELECT COUNT(*) FROM agenda_sesion a WHERE a.id_sesion = se.id_sesion) AS items
               FROM sesion_comite se WHERE se.estado = 'Programada' AND se.fecha >= ?
               ORDER BY se.fecha, se.hora LIMIT ?""",
            (hoy(), limite),
        )


def obtener_sesion(id_sesion):
    with db() as conn:
        return _one(conn, "SELECT * FROM sesion_comite WHERE id_sesion = ?", (id_sesion,))


def guardar_sesion(id_sesion, numero, fecha, hora, lugar, estado, id_usuario):
    if not numero or not fecha:
        return False, "Número y fecha de la sesión son obligatorios.", None
    if estado not in ESTADOS_SESION:
        estado = "Programada"
    try:
        with db() as conn:
            if id_sesion:
                _execute(
                    conn,
                    "UPDATE sesion_comite SET numero = ?, fecha = ?, hora = ?, lugar = ?, estado = ? WHERE id_sesion = ?",
                    (numero, fecha, hora or None, lugar or None, estado, id_sesion),
                )
            else:
                cursor = _execute(
                    conn,
                    "INSERT INTO sesion_comite(numero, fecha, hora, lugar, estado) VALUES (?, ?, ?, ?, ?)",
                    (numero, fecha, hora or None, lugar or None, estado),
                )
                id_sesion = cursor.lastrowid
                notificar_roles(
                    conn, ROLES_COMITE,
                    f"Se programó la sesión {numero} para el {fecha}" + (f" a las {hora}" if hora else "") + ".",
                    f"/sesiones/{id_sesion}", excepto=id_usuario,
                )
        return True, "Sesión guardada.", id_sesion
    except mysql.connector.IntegrityError:
        return False, "Ya existe una sesión con ese número.", None


def sugerir_numero_sesion():
    with db() as conn:
        total = _one(conn, "SELECT COUNT(*) AS total FROM sesion_comite WHERE numero LIKE ?",
                     (f"{date.today().year}-%",))["total"]
    return f"{date.today().year}-{total + 1:02d}"


def eliminar_sesion(id_sesion):
    with db() as conn:
        bloqueo = _one(
            conn,
            """SELECT (SELECT COUNT(*) FROM decision WHERE id_sesion = ?) +
                      (SELECT COUNT(*) FROM acta WHERE id_sesion = ?) AS total""",
            (id_sesion, id_sesion),
        )["total"]
        if bloqueo:
            return False, "No se puede eliminar una sesión con decisiones o acta. Puede marcarla como cancelada."
        _execute(conn, "DELETE FROM agenda_sesion WHERE id_sesion = ?", (id_sesion,))
        _execute(conn, "DELETE FROM sesion_comite WHERE id_sesion = ?", (id_sesion,))
    return True, "Sesión eliminada."


def agenda_sesion(id_sesion):
    with db() as conn:
        return _all(
            conn,
            """SELECT a.id_agenda, a.orden, s.id_solicitud, s.codigo, s.titulo, s.estado, s.prioridad,
                      t.nombre AS tipo, u.nombre AS investigador,
                      d.decision, d.observacion AS observacion_decision,
                      (SELECT GROUP_CONCAT(CONCAT(ur.nombre, ': ', r.concepto) SEPARATOR ' | ')
                         FROM revision r JOIN usuario ur ON ur.id_usuario = r.id_usuario
                        WHERE r.id_solicitud = s.id_solicitud) AS conceptos
               FROM agenda_sesion a
               JOIN solicitud s ON s.id_solicitud = a.id_solicitud
               JOIN tipo_solicitud t ON t.id_tipo = s.id_tipo
               JOIN investigador i ON i.id_investigador = s.id_investigador
               JOIN usuario u ON u.id_usuario = i.id_usuario
               LEFT JOIN decision d ON d.id_decision = (
                    SELECT MAX(d2.id_decision) FROM decision d2
                     WHERE d2.id_sesion = a.id_sesion AND d2.id_solicitud = a.id_solicitud)
               WHERE a.id_sesion = ? ORDER BY a.orden, a.id_agenda""",
            (id_sesion,),
        )


def solicitudes_disponibles_para_agenda(id_sesion):
    """Solicitudes listas para comité que no están en la agenda de otra sesión programada."""
    with db() as conn:
        return _all(
            conn,
            """SELECT s.id_solicitud, s.codigo, s.titulo, s.prioridad FROM solicitud s
               WHERE s.estado = 'Lista para comité'
                 AND NOT EXISTS (
                     SELECT 1 FROM agenda_sesion a JOIN sesion_comite se ON se.id_sesion = a.id_sesion
                      WHERE a.id_solicitud = s.id_solicitud
                        AND (a.id_sesion = ? OR se.estado = 'Programada')
                        AND NOT EXISTS (SELECT 1 FROM decision d
                                         WHERE d.id_sesion = a.id_sesion AND d.id_solicitud = s.id_solicitud))
               ORDER BY FIELD(s.prioridad, 'Alta', 'Media', 'Baja'), s.fecha_radicacion""",
            (id_sesion,),
        )


def _agregar_item(conn, id_sesion, id_solicitud, id_usuario, sesion_numero):
    existe = _one(conn, "SELECT 1 AS si FROM agenda_sesion WHERE id_sesion = ? AND id_solicitud = ?",
                  (id_sesion, id_solicitud))
    if existe:
        return False
    orden = _one(conn, "SELECT COALESCE(MAX(orden), 0) + 1 AS o FROM agenda_sesion WHERE id_sesion = ?",
                 (id_sesion,))["o"]
    _execute(conn, "INSERT INTO agenda_sesion(id_sesion, id_solicitud, orden) VALUES (?, ?, ?)",
             (id_sesion, id_solicitud, orden))
    registrar_actuacion(conn, id_solicitud, id_usuario, "Inclusión en agenda", f"Sesión {sesion_numero}")
    inv = _id_usuario_investigador(conn, id_solicitud)
    if inv:
        notificar(conn, inv["id_usuario"],
                  f"Su solicitud {inv['codigo']} será estudiada en la sesión {sesion_numero}.",
                  f"/solicitudes/{id_solicitud}")
    return True


def agregar_a_agenda(id_sesion, id_solicitud, id_usuario):
    sesion = obtener_sesion(id_sesion)
    with db() as conn:
        if not _agregar_item(conn, id_sesion, id_solicitud, id_usuario, sesion["numero"]):
            return False, "La solicitud ya está en la agenda."
    return True, "Solicitud agregada a la agenda."


def consolidar_agenda(id_sesion, id_usuario):
    """Agrega a la agenda todas las solicitudes listas para comité."""
    sesion = obtener_sesion(id_sesion)
    disponibles = solicitudes_disponibles_para_agenda(id_sesion)
    agregadas = 0
    with db() as conn:
        for sol in disponibles:
            if _agregar_item(conn, id_sesion, sol["id_solicitud"], id_usuario, sesion["numero"]):
                agregadas += 1
    if not agregadas:
        return False, "No hay solicitudes «Lista para comité» pendientes de agendar."
    return True, f"Se consolidaron {agregadas} solicitud(es) en la agenda."


def quitar_de_agenda(id_sesion, id_solicitud, id_usuario):
    with db() as conn:
        if _one(conn, "SELECT 1 AS si FROM decision WHERE id_sesion = ? AND id_solicitud = ?", (id_sesion, id_solicitud)):
            return False, "La solicitud ya tiene decisión en esta sesión."
        _execute(conn, "DELETE FROM agenda_sesion WHERE id_sesion = ? AND id_solicitud = ?", (id_sesion, id_solicitud))
        registrar_actuacion(conn, id_solicitud, id_usuario, "Retiro de agenda", f"Sesión {id_sesion}")
    return True, "Solicitud retirada de la agenda."


def registrar_decision(id_sesion, id_solicitud, decision, observacion, id_usuario):
    if decision not in DECISIONES:
        return False, "Seleccione una decisión válida."
    with db() as conn:
        sesion = _one(conn, "SELECT numero FROM sesion_comite WHERE id_sesion = ?", (id_sesion,))
        en_agenda = _one(conn, "SELECT 1 AS si FROM agenda_sesion WHERE id_sesion = ? AND id_solicitud = ?",
                         (id_sesion, id_solicitud))
        if not sesion or not en_agenda:
            return False, "La solicitud no está en la agenda de esta sesión."
        _execute(conn, "DELETE FROM decision WHERE id_sesion = ? AND id_solicitud = ?", (id_sesion, id_solicitud))
        _execute(
            conn,
            "INSERT INTO decision(id_solicitud, id_sesion, decision, observacion, id_usuario) VALUES (?, ?, ?, ?, ?)",
            (id_solicitud, id_sesion, decision, observacion or None, id_usuario),
        )
        registrar_actuacion(conn, id_solicitud, id_usuario, "Decisión del comité",
                            f"Sesión {sesion['numero']}: {decision}" + (f". {observacion}" if observacion else ""))
        _cambiar_estado(conn, id_solicitud, DECISIONES[decision], id_usuario,
                        f"Decisión de la sesión {sesion['numero']}", notificar_investigador=False)
        inv = _id_usuario_investigador(conn, id_solicitud)
        if inv:
            notificar(conn, inv["id_usuario"],
                      f"El comité decidió «{decision}» sobre su solicitud {inv['codigo']} (sesión {sesion['numero']}).",
                      f"/solicitudes/{id_solicitud}")
    return True, "Decisión registrada."


def listar_decisiones(id_usuario=None, decision=None, q=None, id_sesion=None):
    condiciones, params = [], []
    if id_usuario is not None:
        condiciones.append("i.id_usuario = ?")
        params.append(id_usuario)
    if decision:
        condiciones.append("d.decision = ?")
        params.append(decision)
    if id_sesion:
        condiciones.append("d.id_sesion = ?")
        params.append(id_sesion)
    if q:
        condiciones.append("(s.codigo LIKE ? OR s.titulo LIKE ? OR u.nombre LIKE ?)")
        params += [f"%{q}%"] * 3
    query = """SELECT d.*, s.codigo, s.titulo, u.nombre AS investigador, t.nombre AS tipo,
                      se.numero AS sesion, se.fecha AS fecha_sesion, ud.nombre AS registrado_por
               FROM decision d
               JOIN solicitud s ON s.id_solicitud = d.id_solicitud
               JOIN tipo_solicitud t ON t.id_tipo = s.id_tipo
               JOIN investigador i ON i.id_investigador = s.id_investigador
               JOIN usuario u ON u.id_usuario = i.id_usuario
               LEFT JOIN sesion_comite se ON se.id_sesion = d.id_sesion
               LEFT JOIN usuario ud ON ud.id_usuario = d.id_usuario"""
    if condiciones:
        query += " WHERE " + " AND ".join(condiciones)
    query += " ORDER BY d.fecha DESC, d.id_decision DESC"
    with db() as conn:
        return _all(conn, query, tuple(params))


def decisiones_de_solicitud(id_solicitud):
    with db() as conn:
        return _all(
            conn,
            """SELECT d.*, se.numero AS sesion, se.fecha AS fecha_sesion, se.id_sesion
               FROM decision d LEFT JOIN sesion_comite se ON se.id_sesion = d.id_sesion
               WHERE d.id_solicitud = ? ORDER BY d.fecha DESC, d.id_decision DESC""",
            (id_solicitud,),
        )


# ---------------------------------------------------------------------------
# Actas
# ---------------------------------------------------------------------------
def obtener_acta(id_sesion):
    with db() as conn:
        return _one(
            conn,
            """SELECT a.*, u.nombre AS generada_por FROM acta a
               LEFT JOIN usuario u ON u.id_usuario = a.id_usuario WHERE a.id_sesion = ?""",
            (id_sesion,),
        )


def generar_acta(id_sesion, asistentes, notas, id_usuario):
    """Consolida las decisiones de la sesión en el texto del acta y marca la sesión como realizada."""
    sesion = obtener_sesion(id_sesion)
    agenda = agenda_sesion(id_sesion)
    if not agenda:
        return False, "La sesión no tiene solicitudes en agenda."
    sin_decision = [item["codigo"] for item in agenda if not item["decision"]]
    if sin_decision:
        return False, "Registre la decisión de todas las solicitudes antes del acta: " + ", ".join(sin_decision)

    numero = f"ACTA-{sesion['numero']}"
    lineas = [
        f"{numero}",
        "COMITÉ DE INVESTIGACIÓN",
        "",
        f"Sesión: {sesion['numero']}",
        f"Fecha: {sesion['fecha']}" + (f"    Hora: {sesion['hora']}" if sesion["hora"] else ""),
        f"Lugar: {sesion['lugar'] or 'No registrado'}",
        "",
        "1. ASISTENTES",
    ]
    lineas += [f"   - {a.strip()}" for a in asistentes.splitlines() if a.strip()] or ["   - No registrados"]
    lineas += ["", "2. ORDEN DEL DÍA"]
    for n, item in enumerate(agenda, 1):
        lineas.append(f"   {n}. {item['codigo']} – {item['titulo']} ({item['tipo']})")
    lineas += ["", "3. DESARROLLO Y DECISIONES"]
    for n, item in enumerate(agenda, 1):
        lineas += [
            f"   3.{n}. Solicitud {item['codigo']}: {item['titulo']}",
            f"        Investigador: {item['investigador']}",
            f"        Tipo: {item['tipo']}",
            f"        Conceptos de revisión: {item['conceptos'] or 'Sin conceptos registrados'}",
            f"        DECISIÓN: {item['decision'].upper()}",
        ]
        if item["observacion_decision"]:
            lineas.append(f"        Observaciones: {item['observacion_decision']}")
        lineas.append("")
    resumen = {}
    for item in agenda:
        resumen[item["decision"]] = resumen.get(item["decision"], 0) + 1
    lineas.append("4. RESUMEN DE DECISIONES")
    lineas += [f"   - {k}: {v}" for k, v in resumen.items()]
    lineas += [f"   - Total de solicitudes estudiadas: {len(agenda)}", "", "5. PROPOSICIONES Y VARIOS"]
    lineas.append(f"   {notas.strip()}" if notas and notas.strip() else "   Sin proposiciones.")
    lineas += [
        "",
        f"Acta generada el {datetime.now():%Y-%m-%d %H:%M}.",
        "",
        "",
        "______________________________          ______________________________",
        "Presidente(a) del Comité                 Secretario(a) del Comité",
    ]
    contenido = "\n".join(lineas)

    with db() as conn:
        existente = _one(conn, "SELECT version FROM acta WHERE id_sesion = ?", (id_sesion,))
        if existente:
            _execute(
                conn,
                """UPDATE acta SET contenido = ?, asistentes = ?, version = version + 1,
                          fecha_generacion = NOW(), id_usuario = ? WHERE id_sesion = ?""",
                (contenido, asistentes, id_usuario, id_sesion),
            )
            version = existente["version"] + 1
        else:
            _execute(
                conn,
                "INSERT INTO acta(id_sesion, numero, contenido, asistentes, id_usuario) VALUES (?, ?, ?, ?, ?)",
                (id_sesion, numero, contenido, asistentes, id_usuario),
            )
            version = 1
        _execute(conn, "UPDATE sesion_comite SET estado = 'Realizada' WHERE id_sesion = ?", (id_sesion,))
        for item in agenda:
            registrar_actuacion(conn, item["id_solicitud"], id_usuario, "Registro en acta", f"{numero} (versión {version})")
        notificar_roles(conn, ROLES_COMITE, f"Se generó el {numero} (versión {version}).",
                        f"/sesiones/{id_sesion}/acta", excepto=id_usuario)
    return True, f"{numero} generada (versión {version})."


def listar_actas():
    with db() as conn:
        return _all(
            conn,
            """SELECT a.id_acta, a.numero, a.version, a.fecha_generacion, se.id_sesion, se.numero AS sesion, se.fecha
               FROM acta a JOIN sesion_comite se ON se.id_sesion = a.id_sesion
               ORDER BY se.fecha DESC""",
        )


# ---------------------------------------------------------------------------
# Notificaciones
# ---------------------------------------------------------------------------
def listar_notificaciones(id_usuario, limite=100):
    with db() as conn:
        return _all(
            conn,
            "SELECT * FROM notificacion WHERE id_usuario = ? ORDER BY fecha DESC, id_notificacion DESC LIMIT ?",
            (id_usuario, limite),
        )


def contar_no_leidas(id_usuario):
    with db() as conn:
        return _one(conn, "SELECT COUNT(*) AS total FROM notificacion WHERE id_usuario = ? AND leida = 0",
                    (id_usuario,))["total"]


def marcar_leida(id_usuario, id_notificacion=None):
    with db() as conn:
        if id_notificacion:
            fila = _one(conn, "SELECT enlace FROM notificacion WHERE id_notificacion = ? AND id_usuario = ?",
                        (id_notificacion, id_usuario))
            _execute(conn, "UPDATE notificacion SET leida = 1 WHERE id_notificacion = ? AND id_usuario = ?",
                     (id_notificacion, id_usuario))
            return fila["enlace"] if fila else None
        _execute(conn, "UPDATE notificacion SET leida = 1 WHERE id_usuario = ?", (id_usuario,))
    return None


# ---------------------------------------------------------------------------
# Dashboard y reportes
# ---------------------------------------------------------------------------
def conteo_por_estado(id_usuario=None, desde=None, hasta=None):
    condiciones, params = [], []
    if id_usuario is not None:
        condiciones.append("i.id_usuario = ?")
        params.append(id_usuario)
    if desde:
        condiciones.append("s.fecha_radicacion >= ?")
        params.append(desde)
    if hasta:
        condiciones.append("s.fecha_radicacion < DATE_ADD(?, INTERVAL 1 DAY)")
        params.append(hasta)
    query = """SELECT s.estado, COUNT(*) AS total FROM solicitud s
               JOIN investigador i ON i.id_investigador = s.id_investigador"""
    if condiciones:
        query += " WHERE " + " AND ".join(condiciones)
    query += " GROUP BY s.estado"
    with db() as conn:
        filas = {f["estado"]: f["total"] for f in _all(conn, query, tuple(params))}
    return {estado: filas.get(estado, 0) for estado in ESTADOS}


def _rango(desde, hasta, alias="s"):
    condiciones, params = [], []
    if desde:
        condiciones.append(f"{alias}.fecha_radicacion >= ?")
        params.append(desde)
    if hasta:
        condiciones.append(f"{alias}.fecha_radicacion < DATE_ADD(?, INTERVAL 1 DAY)")
        params.append(hasta)
    return (" WHERE " + " AND ".join(condiciones)) if condiciones else "", tuple(params)


def reportes(desde=None, hasta=None):
    where, params = _rango(desde, hasta)
    with db() as conn:
        por_tipo = _all(
            conn,
            f"""SELECT t.nombre AS etiqueta, COUNT(*) AS total,
                       SUM(s.estado IN ('Aprobada', 'Aprobada con ajustes')) AS aprobadas,
                       SUM(s.estado = 'Rechazada') AS rechazadas
                FROM solicitud s JOIN tipo_solicitud t ON t.id_tipo = s.id_tipo{where}
                GROUP BY t.nombre ORDER BY total DESC""",
            params,
        )
        por_mes = _all(
            conn,
            f"""SELECT SUBSTRING(CAST(s.fecha_radicacion AS CHAR), 1, 7) AS etiqueta, COUNT(*) AS total
                FROM solicitud s{where} GROUP BY etiqueta ORDER BY etiqueta DESC LIMIT 12""",
            params,
        )
        por_programa = _all(
            conn,
            f"""SELECT COALESCE(NULLIF(i.programa, ''), 'Sin programa') AS etiqueta, COUNT(*) AS total
                FROM solicitud s JOIN investigador i ON i.id_investigador = s.id_investigador{where}
                GROUP BY etiqueta ORDER BY total DESC""",
            params,
        )
        por_decision = _all(
            conn,
            f"""SELECT d.decision AS etiqueta, COUNT(*) AS total FROM decision d
                JOIN solicitud s ON s.id_solicitud = d.id_solicitud{where}
                GROUP BY d.decision ORDER BY total DESC""",
            params,
        )
        tiempo = _one(
            conn,
            f"""SELECT AVG(DATEDIFF(primera, s.fecha_radicacion)) AS dias, COUNT(*) AS decididas
                FROM solicitud s
                JOIN (SELECT id_solicitud, MIN(fecha) AS primera FROM decision
                       WHERE decision <> 'Aplazada' GROUP BY id_solicitud) d
                  ON d.id_solicitud = s.id_solicitud{where}""",
            params,
        )
        carga = _all(
            conn,
            """SELECT u.nombre AS etiqueta,
                      SUM(a.estado = 'Pendiente') AS pendientes,
                      SUM(a.estado = 'Completada') AS completadas,
                      SUM(a.estado = 'Pendiente' AND a.fecha_limite IS NOT NULL AND a.fecha_limite < ?) AS vencidas
               FROM asignacion_revision a JOIN usuario u ON u.id_usuario = a.id_usuario
               GROUP BY u.nombre ORDER BY pendientes DESC""",
            (hoy(),),
        )
        sesiones = _one(
            conn,
            """SELECT COUNT(*) AS total, SUM(estado = 'Realizada') AS realizadas,
                      SUM(estado = 'Programada') AS programadas,
                      (SELECT COUNT(*) FROM acta) AS actas FROM sesion_comite""",
        )
    por_mes.reverse()
    return {
        "por_tipo": por_tipo,
        "por_mes": por_mes,
        "por_programa": por_programa,
        "por_decision": por_decision,
        "tiempo_promedio": round(float(tiempo["dias"]), 1) if tiempo and tiempo["dias"] is not None else None,
        "decididas": tiempo["decididas"] if tiempo else 0,
        "carga": carga,
        "sesiones": sesiones,
    }


def actividad_reciente(id_usuario=None, limite=8):
    query = """SELECT a.fecha, a.accion, a.detalle, s.id_solicitud, s.codigo, u.nombre AS usuario
               FROM actuacion a JOIN solicitud s ON s.id_solicitud = a.id_solicitud
               JOIN investigador i ON i.id_investigador = s.id_investigador
               LEFT JOIN usuario u ON u.id_usuario = a.id_usuario"""
    params = ()
    if id_usuario is not None:
        query += " WHERE i.id_usuario = ?"
        params = (id_usuario,)
    query += " ORDER BY a.fecha DESC, a.id_actuacion DESC LIMIT ?"
    with db() as conn:
        return _all(conn, query, params + (limite,))
