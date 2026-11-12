"""Carga un escenario de demostración completo (investigadores, solicitudes en todos los
estados, revisiones, sesiones, decisiones y un acta) usando la lógica del sistema.

Uso:  python datos_demo.py
Es idempotente: si los datos demo ya existen, no hace nada.
"""
from datetime import date, timedelta
import io

import models


class ArchivoDemo:
    """Imita un archivo subido (FileStorage) para guardar documentos de ejemplo."""

    def __init__(self, texto):
        self.texto = texto

    def save(self, ruta):
        with io.open(ruta, "w", encoding="utf-8") as f:
            f.write(self.texto)


def dias(n):
    return (date.today() + timedelta(days=n)).isoformat()


INVESTIGADORES = [
    ("Laura Martínez Ríos", "laura.martinez@comite.edu.co", "10203040", "Ingeniería de Sistemas", "Ingeniería", "3001112233"),
    ("Carlos Pérez Gómez", "carlos.perez@comite.edu.co", "10203041", "Biología", "Ciencias Básicas", "3002223344"),
    ("Ana Sofía Herrera", "ana.herrera@comite.edu.co", "10203042", "Psicología", "Ciencias Sociales", "3003334455"),
]
MIEMBROS = [
    ("Dra. Marta Lucía Vega", "marta.vega@comite.edu.co"),
    ("Dr. Jorge Andrés Ruiz", "jorge.ruiz@comite.edu.co"),
]
SOLICITUDES = [
    # (correo, tipo, título, resumen, prioridad, fecha_limite, flujo)
    ("laura.martinez@comite.edu.co", "Proyecto de Investigacion", "Modelo predictivo de deserción estudiantil con aprendizaje automático",
     "Proyecto para identificar tempranamente estudiantes en riesgo de deserción a partir de datos académicos.", "Alta", dias(20), "aprobada"),
    ("carlos.perez@comite.edu.co", "Ponencia", "Biodiversidad de anfibios en humedales urbanos",
     "Ponencia para el Congreso Nacional de Biología con resultados de muestreo 2025-2026.", "Media", dias(10), "ajustes_aprobada"),
    ("ana.herrera@comite.edu.co", "Publicacion", "Salud mental y uso de redes sociales en universitarios",
     "Artículo para revista indexada derivado de estudio transversal con 400 estudiantes.", "Media", dias(25), "rechazada"),
    ("investigador@comite.edu.co", "Monitoria de Investigacion", "Monitoría para el semillero de analítica de datos",
     "Solicitud de un monitor para apoyar la limpieza de datos y documentación del semillero.", "Baja", dias(30), "cerrada"),
    ("laura.martinez@comite.edu.co", "Ponencia", "Arquitecturas de microservicios para sistemas académicos",
     "Ponencia aceptada en el encuentro regional de ingeniería.", "Media", dias(12), "lista_agendada"),
    ("carlos.perez@comite.edu.co", "Proyecto de Investigacion", "Calidad del agua en la cuenca del río Sinú",
     "Monitoreo fisicoquímico y microbiológico en 12 puntos de la cuenca.", "Alta", dias(8), "lista_agendada"),
    ("ana.herrera@comite.edu.co", "Proyecto de Investigacion", "Estrategias de afrontamiento del estrés académico",
     "Intervención psicoeducativa con grupo control en estudiantes de primer semestre.", "Media", dias(18), "lista"),
    ("investigador@comite.edu.co", "Publicacion", "Revisión sistemática sobre gamificación en educación superior",
     "Manuscrito de revisión sistemática siguiendo la guía PRISMA.", "Media", dias(-3), "en_revision"),
    ("laura.martinez@comite.edu.co", "Informe final de proyecto", "Informe final: plataforma de tutorías virtuales",
     "Informe de cierre del proyecto financiado en la convocatoria interna 2025.", "Baja", dias(15), "en_revision"),
    ("carlos.perez@comite.edu.co", "Monitoria de Investigacion", "Monitoría para el laboratorio de microbiología",
     "Apoyo estudiantil para preparación de medios de cultivo y registro de muestras.", "Media", dias(-1), "pendiente_docs"),
    ("ana.herrera@comite.edu.co", "Ponencia", "Bienestar docente en tiempos de educación híbrida",
     "Ponencia propuesta para el simposio internacional de psicología educativa.", "Alta", dias(6), "requiere_ajustes"),
    ("investigador@comite.edu.co", "Proyecto de Investigacion", "Energía solar fotovoltaica para sedes rurales",
     "Estudio de factibilidad técnica y económica para dos sedes rurales de la universidad.", "Media", dias(40), "recibida"),
    ("laura.martinez@comite.edu.co", "Publicacion", "Detección de noticias falsas con modelos de lenguaje",
     "Artículo para conferencia internacional con evaluación de modelos en español.", "Alta", dias(9), "recibida"),
]


def _uid(correo):
    with models.db() as conn:
        return models._one(conn, "SELECT id_usuario FROM usuario WHERE correo = ?", (correo,))["id_usuario"]


def _rol(nombre):
    with models.db() as conn:
        return models._one(conn, "SELECT id_rol FROM rol WHERE nombre = ?", (nombre,))["id_rol"]


def _cargar_todos(id_sol, id_inv, saltar_uno=False):
    reqs = [r for r in models.estado_requisitos(id_sol) if r["obligatorio"]]
    if saltar_uno:
        reqs = reqs[:-1]
    for r in reqs:
        models.guardar_documento(id_sol, r["id_requisito"], ArchivoDemo(f"Documento de ejemplo: {r['nombre']}"),
                                 r["nombre"].lower().replace(" ", "_")[:40] + ".pdf", id_inv)


def _validar(id_sol, id_secre):
    resultados = {r["id_requisito"]: (bool(r["documentos"]), "" if r["documentos"] else "No se adjuntó el documento")
                  for r in models.estado_requisitos(id_sol)}
    models.validar_requisitos(id_sol, resultados, id_secre)


def main():
    models.init_db()
    with models.db() as conn:
        if models._one(conn, "SELECT 1 AS si FROM usuario WHERE correo = ?", (INVESTIGADORES[0][1],)):
            print("Los datos demo ya estaban cargados. No se hizo ningún cambio.")
            return

    for nombre, correo, doc, prog, fac, tel in INVESTIGADORES:
        models.registrar_investigador(nombre, correo, "invest123", doc, prog, fac, tel)
    for nombre, correo in MIEMBROS:
        models.crear_usuario(nombre, correo, "comite123", _rol("Comite"))
    models.actualizar_perfil(_uid("investigador@comite.edu.co"), "Investigador Demo", "10203099",
                             "Ingeniería Ambiental", "Ingeniería", "3009998877")

    secre = _uid("secretaria@comite.edu.co")
    revisores = [_uid("comite@comite.edu.co"), _uid(MIEMBROS[0][1]), _uid(MIEMBROS[1][1])]

    # Sesión ya realizada (con acta) y sesión próxima (con agenda consolidada).
    _, _, ses_pasada = models.guardar_sesion(None, f"{date.today().year}-01", dias(-7), "14:00",
                                             "Sala de juntas, Bloque B", "Programada", secre)
    _, _, ses_proxima = models.guardar_sesion(None, f"{date.today().year}-02", dias(7), "10:00",
                                              "Sala virtual (Teams)", "Programada", secre)

    pasadas = []
    for i, (correo, tipo, titulo, resumen, prio, limite, flujo) in enumerate(SOLICITUDES):
        inv = _uid(correo)
        id_tipo = next(t["id_tipo"] for t in models.listar_tipos() if t["nombre"] == tipo)
        _, _, sid = models.crear_solicitud(inv, id_tipo, titulo, resumen, prio, limite)
        if flujo == "recibida":
            if i % 2 == 0:
                _cargar_todos(sid, inv)
            continue
        if flujo == "pendiente_docs":
            _cargar_todos(sid, inv, saltar_uno=True)
            _validar(sid, secre)
            continue

        _cargar_todos(sid, inv)
        _validar(sid, secre)
        rev = revisores[i % len(revisores)]
        models.asignar_revisor(sid, rev, limite, secre)
        if flujo == "en_revision":
            continue

        concepto = {"rechazada": "Desfavorable", "ajustes_aprobada": "Favorable con ajustes"}.get(flujo, "Favorable")
        models.registrar_revision(sid, rev, concepto, "Revisión metodológica y presupuestal realizada.")
        if flujo in ("requiere_ajustes", "ajustes_aprobada"):
            models.agregar_observacion(sid, rev, "Ajustar el cronograma y justificar mejor el presupuesto de viaje.",
                                       "Solicitud de ajuste", True)
            if flujo == "requiere_ajustes":
                continue
            models.guardar_documento(sid, models.estado_requisitos(sid)[0]["id_requisito"],
                                     ArchivoDemo("Versión ajustada"), "documento_ajustado.pdf", inv)
            models.responder_ajustes(sid, inv, "Se ajustó el cronograma y se adjuntó el presupuesto corregido.")
        models.cambiar_estado(sid, "Lista para comité", secre, "Revisión completa")
        if flujo == "lista":
            continue
        if flujo == "lista_agendada":
            models.agregar_a_agenda(ses_proxima, sid, secre)
            continue
        models.agregar_a_agenda(ses_pasada, sid, secre)
        pasadas.append((sid, flujo))

    decisiones = {
        "aprobada": ("Aprobada", "Se aprueba con el presupuesto solicitado."),
        "ajustes_aprobada": ("Aprobada con ajustes", "Aprobada condicionada a reducir el presupuesto de viaje en 15%."),
        "rechazada": ("Rechazada", "La metodología no garantiza la confidencialidad de los participantes."),
        "cerrada": ("Aprobada", "Se aprueba un monitor por 10 horas semanales."),
    }
    for sid, flujo in pasadas:
        decision, obs = decisiones[flujo]
        models.registrar_decision(ses_pasada, sid, decision, obs, secre)
    asistentes = "Secretaria Comite (Secretario)\nMiembro Comite (Comité)\n" + "\n".join(f"{n} (Comité)" for n, _ in MIEMBROS)
    models.generar_acta(ses_pasada, asistentes, "Se acordó revisar el reglamento de monitorías en la próxima sesión.", secre)
    for sid, flujo in pasadas:
        if flujo == "cerrada":
            models.cambiar_estado(sid, "Cerrada", secre, "Trámite finalizado; monitor vinculado.")

    print("Datos demo cargados.")
    print("  Investigadores extra: " + ", ".join(c for _, c, *_ in INVESTIGADORES) + " (contraseña invest123)")
    print("  Integrantes del comité extra: " + ", ".join(c for _, c in MIEMBROS) + " (contraseña comite123)")
    for estado, n in models.conteo_por_estado().items():
        print(f"  {estado}: {n}")


if __name__ == "__main__":
    main()
