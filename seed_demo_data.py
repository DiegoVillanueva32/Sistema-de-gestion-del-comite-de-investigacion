"""Carga solicitudes de demostración en MySQL sin duplicarlas ni borrar datos."""
import models


SOLICITUDES_DEMO = (
    (
        "DEMO-PRUEBA-001",
        "Proyecto de Investigacion",
        "Evaluación de estrategias de lectura crítica en estudiantes universitarios",
        "Proyecto piloto para medir cambios en comprensión lectora durante un semestre.",
        "Recibida",
        "Alta",
        "2026-11-15",
    ),
    (
        "DEMO-PRUEBA-002",
        "Ponencia",
        "Resultados preliminares sobre calidad del agua en la cuenca local",
        "Propuesta de ponencia para presentar resultados de muestreo y análisis ambiental.",
        "En revisión",
        "Media",
        "2026-11-20",
    ),
    (
        "DEMO-PRUEBA-003",
        "Publicacion",
        "Artículo sobre prácticas de innovación pedagógica",
        "Manuscrito derivado de un estudio institucional sobre metodologías activas.",
        "Aprobada",
        "Media",
        "2026-12-01",
    ),
    (
        "DEMO-PRUEBA-004",
        "Monitoria de Investigacion",
        "Monitoría para el laboratorio de análisis de datos",
        "Solicitud de apoyo estudiantil para organizar datos y documentar resultados.",
        "Rechazada",
        "Baja",
        "2026-12-10",
    ),
)


def seed_demo_data():
    models.init_db()
    conn = models.get_conn()
    try:
        investigador = models._execute(
            conn,
            """SELECT u.id_usuario, i.id_investigador
               FROM usuario u
               JOIN rol r ON r.id_rol = u.id_rol
               JOIN investigador i ON i.id_usuario = u.id_usuario
               WHERE r.nombre = 'Investigador'
               ORDER BY u.id_usuario
               LIMIT 1""",
        ).fetchone()
        if investigador is None:
            raise RuntimeError(
                "No se encontró ningún usuario con perfil de investigador."
            )

        inserted = 0
        for codigo, tipo, titulo, resumen, estado, prioridad, fecha_limite in SOLICITUDES_DEMO:
            tipo_row = models._execute(
                conn, "SELECT id_tipo FROM tipo_solicitud WHERE nombre = ?", (tipo,)
            ).fetchone()
            if tipo_row is None:
                raise RuntimeError(f"No se encontró el tipo de solicitud: {tipo}")

            cursor = models._execute(
                conn,
                """INSERT IGNORE INTO solicitud
                   (codigo, id_investigador, id_tipo, titulo, resumen, estado,
                    prioridad, fecha_limite)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    codigo,
                    investigador["id_investigador"],
                    tipo_row["id_tipo"],
                    titulo,
                    resumen,
                    estado,
                    prioridad,
                    fecha_limite,
                ),
            )
            inserted += cursor.rowcount

        conn.commit()
        print(f"Solicitudes de demostración nuevas: {inserted}")
        print(f"Solicitudes de demostración existentes: {len(SOLICITUDES_DEMO) - inserted}")
        print(f"Investigador asignado: usuario #{investigador['id_usuario']}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    seed_demo_data()
