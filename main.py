"""Aplicación web del Sistema de Gestión del Comité de Investigación."""
import csv
from datetime import date, datetime
from functools import wraps
import io
import os

from flask import (
    Flask, Response, abort, flash, redirect, render_template, request,
    send_from_directory, session, url_for,
)
from werkzeug.utils import secure_filename

import models
from models import ESTADOS, ROLES_COMITE, ROLES_GESTION


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "clave-de-desarrollo-comite")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB por archivo


# ---------------------------------------------------------------------------
# Autorización
# ---------------------------------------------------------------------------
def rol_actual():
    return session["usuario"]["rol"] if "usuario" in session else None


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "usuario" not in session:
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped_view


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped_view(*args, **kwargs):
            if rol_actual() not in roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapped_view

    return decorator


admin_required = roles_required("Administrador")
gestion_required = roles_required(*ROLES_GESTION)
comite_required = roles_required(*ROLES_COMITE)


def _id_si_investigador():
    """Si el usuario es investigador, retorna su id para filtrar solo sus datos."""
    usuario = session["usuario"]
    return usuario["id_usuario"] if usuario["rol"] == "Investigador" else None


def _cargar_solicitud(id_solicitud):
    solicitud = models.obtener_solicitud(id_solicitud, _id_si_investigador())
    if solicitud is None:
        abort(404)
    return solicitud


def _fecha_valida(valor):
    if not valor:
        return None
    try:
        return date.fromisoformat(valor).isoformat()
    except ValueError:
        return None


@app.context_processor
def contexto_global():
    datos = {"ROLES_GESTION": ROLES_GESTION, "ROLES_COMITE": ROLES_COMITE, "hoy": models.hoy()}
    if "usuario" in session:
        try:
            datos["notificaciones_pendientes"] = models.contar_no_leidas(session["usuario"]["id_usuario"])
        except Exception:
            datos["notificaciones_pendientes"] = 0
    return datos


@app.template_filter("clase_estado")
def clase_estado(estado):
    return {
        "Recibida": "st-info",
        "En revisión": "st-warn",
        "Pendiente por documentos": "st-alert",
        "Requiere ajustes": "st-alert",
        "Lista para comité": "st-purple",
        "Aprobada": "st-ok",
        "Aprobada con ajustes": "st-ok",
        "Rechazada": "st-bad",
        "Cerrada": "st-muted",
        "Aplazada": "st-warn",
        "Favorable": "st-ok",
        "Favorable con ajustes": "st-warn",
        "Desfavorable": "st-bad",
        "Programada": "st-info",
        "Realizada": "st-ok",
        "Cancelada": "st-muted",
        "Pendiente": "st-warn",
        "Completada": "st-ok",
    }.get(estado, "st-info")


@app.template_filter("fecha")
def formato_fecha(valor, con_hora=False):
    if not valor:
        return "—"
    if isinstance(valor, datetime):
        return valor.strftime("%Y-%m-%d %H:%M" if con_hora else "%Y-%m-%d")
    return str(valor)


# ---------------------------------------------------------------------------
# Autenticación y registro de investigadores
# ---------------------------------------------------------------------------
@app.get("/")
def index():
    return redirect(url_for("dashboard") if "usuario" in session else url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if "usuario" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        correo = request.form.get("correo", "").strip().lower()
        password = request.form.get("password", "").strip()
        if not correo or not password:
            flash("Ingrese correo y contraseña.", "error")
        else:
            usuario = models.login(correo, password)
            if usuario:
                session.clear()
                session["usuario"] = {
                    "id_usuario": usuario["id_usuario"],
                    "nombre": usuario["nombre"],
                    "rol": usuario["rol"],
                }
                destino = request.args.get("next", "")
                if destino.startswith("/") and not destino.startswith("//"):
                    return redirect(destino)
                return redirect(url_for("dashboard"))
            flash("Correo o contraseña incorrectos.", "error")
    return render_template("login.html")


@app.route("/registro", methods=["GET", "POST"])
def registro():
    if "usuario" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        f = request.form
        if f.get("password", "") != f.get("password2", ""):
            flash("Las contraseñas no coinciden.", "error")
        else:
            ok, mensaje = models.registrar_investigador(
                f.get("nombre", "").strip(), f.get("correo", "").strip().lower(), f.get("password", "").strip(),
                f.get("documento", "").strip(), f.get("programa", "").strip(),
                f.get("facultad", "").strip(), f.get("telefono", "").strip(),
            )
            flash(mensaje, "success" if ok else "error")
            if ok:
                return redirect(url_for("login"))
    return render_template("registro.html")


@app.post("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    id_usuario = session["usuario"]["id_usuario"]
    if request.method == "POST":
        f = request.form
        ok, mensaje = models.actualizar_perfil(
            id_usuario, f.get("nombre", "").strip(), f.get("documento", "").strip(),
            f.get("programa", "").strip(), f.get("facultad", "").strip(),
            f.get("telefono", "").strip(), f.get("password", "").strip() or None,
        )
        flash(mensaje, "success" if ok else "error")
        if ok:
            session["usuario"] = {**session["usuario"], "nombre": f.get("nombre", "").strip()}
            return redirect(url_for("perfil"))
    return render_template("perfil.html", perfil=models.obtener_perfil(id_usuario))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@app.get("/dashboard")
@login_required
def dashboard():
    usuario = session["usuario"]
    id_inv = _id_si_investigador()
    conteo = models.conteo_por_estado(id_inv)
    return render_template(
        "dashboard.html",
        conteo=conteo,
        total=sum(conteo.values()),
        vencidas=models.listar_solicitudes(id_usuario=id_inv, solo_vencidas=True)[:8],
        asignaciones=models.mis_asignaciones(usuario["id_usuario"]) if usuario["rol"] in ROLES_COMITE else [],
        sesiones=models.proximas_sesiones(),
        actividad=models.actividad_reciente(id_inv),
        mis_solicitudes=models.listar_solicitudes(id_usuario=id_inv)[:6] if id_inv else [],
    )


# ---------------------------------------------------------------------------
# Solicitudes
# ---------------------------------------------------------------------------
@app.get("/solicitudes")
@login_required
def solicitudes():
    filtros = {
        "estado": request.args.get("estado") or None,
        "id_tipo": request.args.get("id_tipo", type=int),
        "q": request.args.get("q", "").strip() or None,
        "solo_vencidas": request.args.get("vencidas") == "1",
        "id_revisor": session["usuario"]["id_usuario"] if request.args.get("mias") == "1" else None,
    }
    return render_template(
        "solicitudes.html",
        solicitudes=models.listar_solicitudes(_id_si_investigador(), **filtros),
        tipos=models.listar_tipos(),
        estados=ESTADOS,
        usuario=session["usuario"],
    )


@app.route("/solicitudes/nueva", methods=["GET", "POST"])
@login_required
def nueva_solicitud():
    if rol_actual() != "Investigador":
        flash("La radicación de solicitudes la realizan los investigadores registrados.", "error")
        return redirect(url_for("solicitudes"))
    return formulario_solicitud(None)


@app.route("/solicitudes/<int:id_solicitud>/editar", methods=["GET", "POST"])
@login_required
def editar_solicitud(id_solicitud):
    solicitud = _cargar_solicitud(id_solicitud)
    if rol_actual() == "Investigador" and solicitud["estado"] not in models.ESTADOS_EDITABLES:
        flash("La solicitud ya está en trámite y no puede modificarse.", "error")
        return redirect(url_for("detalle_solicitud", id_solicitud=id_solicitud))
    if rol_actual() == "Comite":
        abort(403)
    return formulario_solicitud(solicitud)


def formulario_solicitud(solicitud):
    tipos = models.listar_tipos()
    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        id_tipo = request.form.get("id_tipo", type=int)
        prioridad = request.form.get("prioridad", "Media")
        fecha_limite = _fecha_valida(request.form.get("fecha_limite"))
        if rol_actual() == "Investigador" and solicitud:
            # El investigador no cambia prioridad ni fecha límite fijadas por la secretaría.
            prioridad, fecha_limite = solicitud["prioridad"], solicitud["fecha_limite"]

        if not titulo or id_tipo not in {t["id_tipo"] for t in tipos}:
            flash("Título y tipo de solicitud son obligatorios.", "error")
        elif solicitud:
            ok, mensaje = models.actualizar_solicitud(
                solicitud["id_solicitud"], titulo, descripcion, id_tipo, prioridad, fecha_limite,
                session["usuario"]["id_usuario"],
            )
            flash(mensaje, "success" if ok else "error")
            if ok:
                return redirect(url_for("detalle_solicitud", id_solicitud=solicitud["id_solicitud"]))
        else:
            ok, mensaje, id_nueva = models.crear_solicitud(
                session["usuario"]["id_usuario"], id_tipo, titulo, descripcion, prioridad, fecha_limite
            )
            flash(mensaje, "success" if ok else "error")
            if ok:
                return redirect(url_for("detalle_solicitud", id_solicitud=id_nueva))

    return render_template(
        "solicitud_form.html", solicitud=solicitud, tipos=tipos, prioridades=models.PRIORIDADES
    )


@app.get("/solicitudes/<int:id_solicitud>")
@login_required
def detalle_solicitud(id_solicitud):
    solicitud = _cargar_solicitud(id_solicitud)
    usuario = session["usuario"]
    rol = usuario["rol"]
    es_dueno = solicitud["id_usuario"] == usuario["id_usuario"]
    asignaciones = models.listar_asignaciones(id_solicitud)
    revision_pendiente = any(
        a["id_usuario"] == usuario["id_usuario"] and a["estado"] == "Pendiente" for a in asignaciones
    )
    return render_template(
        "solicitud_detalle.html",
        s=solicitud,
        documentos=models.listar_documentos(id_solicitud),
        requisitos=models.estado_requisitos(id_solicitud),
        asignaciones=asignaciones,
        revisiones=models.listar_revisiones(id_solicitud),
        observaciones=models.listar_observaciones(id_solicitud),
        historial=models.historial(id_solicitud),
        estados_hist=models.historial_estados(id_solicitud),
        decisiones=models.decisiones_de_solicitud(id_solicitud),
        miembros=models.usuarios_por_rol("Comite", "Secretario") if rol in ROLES_GESTION else [],
        es_dueno=es_dueno,
        puede_gestionar=rol in ROLES_GESTION,
        puede_revisar=rol in ROLES_COMITE and (revision_pendiente or rol in ROLES_GESTION),
        puede_cargar=rol in ROLES_GESTION or (es_dueno and solicitud["estado"] in models.ESTADOS_EDITABLES),
        puede_editar=rol in ROLES_GESTION or (es_dueno and solicitud["estado"] in models.ESTADOS_EDITABLES),
        estados=ESTADOS,
        conceptos=models.CONCEPTOS,
        tipos_obs=models.TIPOS_OBSERVACION,
        extensiones=", ".join(sorted(models.EXTENSIONES_PERMITIDAS)),
    )


@app.post("/solicitudes/<int:id_solicitud>/eliminar")
@gestion_required
def eliminar_solicitud(id_solicitud):
    _cargar_solicitud(id_solicitud)
    models.eliminar_solicitud(id_solicitud)
    flash("Solicitud eliminada.", "success")
    return redirect(url_for("solicitudes"))


@app.post("/solicitudes/<int:id_solicitud>/documentos")
@login_required
def cargar_documento(id_solicitud):
    solicitud = _cargar_solicitud(id_solicitud)
    es_dueno = solicitud["id_usuario"] == session["usuario"]["id_usuario"]
    if not (rol_actual() in ROLES_GESTION or (es_dueno and solicitud["estado"] in models.ESTADOS_EDITABLES)):
        abort(403)
    archivo = request.files.get("archivo")
    if not archivo or not archivo.filename:
        flash("Seleccione un archivo.", "error")
    else:
        ok, mensaje = models.guardar_documento(
            id_solicitud, request.form.get("id_requisito", type=int), archivo,
            secure_filename(archivo.filename), session["usuario"]["id_usuario"],
        )
        flash(mensaje, "success" if ok else "error")
    return redirect(url_for("detalle_solicitud", id_solicitud=id_solicitud) + "#documentos")


@app.get("/documentos/<int:id_documento>")
@login_required
def descargar_documento(id_documento):
    documento = models.obtener_documento(id_documento)
    if documento is None:
        abort(404)
    _cargar_solicitud(documento["id_solicitud"])  # verifica permisos
    carpeta, nombre = os.path.split(documento["ruta"])
    return send_from_directory(
        os.path.join(models.UPLOAD_DIR, carpeta), nombre,
        as_attachment=True, download_name=documento["nombre_original"] or documento["nombre"],
    )


@app.post("/solicitudes/<int:id_solicitud>/validar")
@gestion_required
def validar_requisitos(id_solicitud):
    _cargar_solicitud(id_solicitud)
    resultados = {}
    for req in models.estado_requisitos(id_solicitud):
        rid = req["id_requisito"]
        resultados[rid] = (
            request.form.get(f"cumple_{rid}") == "1",
            request.form.get(f"obs_{rid}", "").strip(),
        )
    ok, mensaje = models.validar_requisitos(id_solicitud, resultados, session["usuario"]["id_usuario"])
    flash(mensaje, "success" if ok else "error")
    return redirect(url_for("detalle_solicitud", id_solicitud=id_solicitud) + "#requisitos")


@app.post("/solicitudes/<int:id_solicitud>/asignar")
@gestion_required
def asignar_revisor(id_solicitud):
    _cargar_solicitud(id_solicitud)
    ok, mensaje = models.asignar_revisor(
        id_solicitud, request.form.get("id_revisor", type=int),
        _fecha_valida(request.form.get("fecha_limite")), session["usuario"]["id_usuario"],
    )
    flash(mensaje, "success" if ok else "error")
    return redirect(url_for("detalle_solicitud", id_solicitud=id_solicitud) + "#revision")


@app.post("/solicitudes/<int:id_solicitud>/revision")
@comite_required
def registrar_revision(id_solicitud):
    _cargar_solicitud(id_solicitud)
    id_usuario = session["usuario"]["id_usuario"]
    if rol_actual() not in ROLES_GESTION and not models.es_revisor(id_solicitud, id_usuario):
        abort(403)
    ok, mensaje = models.registrar_revision(
        id_solicitud, id_usuario, request.form.get("concepto", ""), request.form.get("observacion", "").strip()
    )
    flash(mensaje, "success" if ok else "error")
    return redirect(url_for("detalle_solicitud", id_solicitud=id_solicitud) + "#revision")


@app.post("/solicitudes/<int:id_solicitud>/observaciones")
@login_required
def agregar_observacion(id_solicitud):
    _cargar_solicitud(id_solicitud)
    ok, mensaje = models.agregar_observacion(
        id_solicitud, session["usuario"]["id_usuario"], request.form.get("descripcion", "").strip(),
        request.form.get("tipo", "General"), rol_actual() in ROLES_COMITE,
    )
    flash(mensaje, "success" if ok else "error")
    return redirect(url_for("detalle_solicitud", id_solicitud=id_solicitud) + "#observaciones")


@app.post("/solicitudes/<int:id_solicitud>/responder")
@roles_required("Investigador")
def responder_ajustes(id_solicitud):
    _cargar_solicitud(id_solicitud)
    ok, mensaje = models.responder_ajustes(
        id_solicitud, session["usuario"]["id_usuario"], request.form.get("comentario", "").strip()
    )
    flash(mensaje, "success" if ok else "error")
    return redirect(url_for("detalle_solicitud", id_solicitud=id_solicitud))


@app.post("/solicitudes/<int:id_solicitud>/estado")
@gestion_required
def cambiar_estado(id_solicitud):
    _cargar_solicitud(id_solicitud)
    ok, mensaje = models.cambiar_estado(
        id_solicitud, request.form.get("estado", ""), session["usuario"]["id_usuario"],
        request.form.get("comentario", "").strip() or None,
    )
    flash(mensaje, "success" if ok else "error")
    return redirect(url_for("detalle_solicitud", id_solicitud=id_solicitud))


# ---------------------------------------------------------------------------
# Investigadores
# ---------------------------------------------------------------------------
@app.get("/investigadores")
@comite_required
def investigadores():
    q = request.args.get("q", "").strip() or None
    return render_template("investigadores.html", investigadores=models.listar_investigadores(q))


# ---------------------------------------------------------------------------
# Sesiones del comité, agenda, decisiones y actas
# ---------------------------------------------------------------------------
@app.get("/sesiones")
@comite_required
def sesiones():
    return render_template("sesiones.html", sesiones=models.listar_sesiones())


@app.route("/sesiones/nueva", methods=["GET", "POST"])
@gestion_required
def nueva_sesion():
    return formulario_sesion(None)


@app.route("/sesiones/<int:id_sesion>/editar", methods=["GET", "POST"])
@gestion_required
def editar_sesion(id_sesion):
    sesion_c = models.obtener_sesion(id_sesion)
    if sesion_c is None:
        abort(404)
    return formulario_sesion(sesion_c)


def formulario_sesion(sesion_c):
    if request.method == "POST":
        f = request.form
        ok, mensaje, id_sesion = models.guardar_sesion(
            sesion_c["id_sesion"] if sesion_c else None, f.get("numero", "").strip(),
            _fecha_valida(f.get("fecha")), f.get("hora", "").strip(), f.get("lugar", "").strip(),
            f.get("estado", "Programada"), session["usuario"]["id_usuario"],
        )
        flash(mensaje, "success" if ok else "error")
        if ok:
            return redirect(url_for("detalle_sesion", id_sesion=id_sesion))
    return render_template(
        "sesion_form.html", sesion_c=sesion_c, estados=models.ESTADOS_SESION,
        numero_sugerido=models.sugerir_numero_sesion(),
    )


@app.get("/sesiones/<int:id_sesion>")
@comite_required
def detalle_sesion(id_sesion):
    sesion_c = models.obtener_sesion(id_sesion)
    if sesion_c is None:
        abort(404)
    agenda = models.agenda_sesion(id_sesion)
    return render_template(
        "sesion_detalle.html",
        sesion_c=sesion_c,
        agenda=agenda,
        disponibles=models.solicitudes_disponibles_para_agenda(id_sesion),
        acta=models.obtener_acta(id_sesion),
        decisiones=list(models.DECISIONES),
        puede_gestionar=rol_actual() in ROLES_GESTION,
        asistentes_sugeridos="\n".join(
            f"{u['nombre']} ({u['rol']})" for u in models.usuarios_por_rol("Comite", "Secretario")
        ),
        pendientes=sum(1 for item in agenda if not item["decision"]),
    )


@app.post("/sesiones/<int:id_sesion>/eliminar")
@gestion_required
def eliminar_sesion(id_sesion):
    ok, mensaje = models.eliminar_sesion(id_sesion)
    flash(mensaje, "success" if ok else "error")
    return redirect(url_for("sesiones") if ok else url_for("detalle_sesion", id_sesion=id_sesion))


@app.post("/sesiones/<int:id_sesion>/agenda")
@gestion_required
def agregar_agenda(id_sesion):
    if models.obtener_sesion(id_sesion) is None:
        abort(404)
    id_solicitud = request.form.get("id_solicitud", type=int)
    if not id_solicitud:
        flash("Seleccione una solicitud.", "error")
    else:
        ok, mensaje = models.agregar_a_agenda(id_sesion, id_solicitud, session["usuario"]["id_usuario"])
        flash(mensaje, "success" if ok else "error")
    return redirect(url_for("detalle_sesion", id_sesion=id_sesion))


@app.post("/sesiones/<int:id_sesion>/consolidar")
@gestion_required
def consolidar_agenda(id_sesion):
    if models.obtener_sesion(id_sesion) is None:
        abort(404)
    ok, mensaje = models.consolidar_agenda(id_sesion, session["usuario"]["id_usuario"])
    flash(mensaje, "success" if ok else "error")
    return redirect(url_for("detalle_sesion", id_sesion=id_sesion))


@app.post("/sesiones/<int:id_sesion>/agenda/<int:id_solicitud>/quitar")
@gestion_required
def quitar_agenda(id_sesion, id_solicitud):
    ok, mensaje = models.quitar_de_agenda(id_sesion, id_solicitud, session["usuario"]["id_usuario"])
    flash(mensaje, "success" if ok else "error")
    return redirect(url_for("detalle_sesion", id_sesion=id_sesion))


@app.post("/sesiones/<int:id_sesion>/decision")
@gestion_required
def registrar_decision(id_sesion):
    ok, mensaje = models.registrar_decision(
        id_sesion, request.form.get("id_solicitud", type=int), request.form.get("decision", ""),
        request.form.get("observacion", "").strip(), session["usuario"]["id_usuario"],
    )
    flash(mensaje, "success" if ok else "error")
    return redirect(url_for("detalle_sesion", id_sesion=id_sesion) + "#agenda")


@app.post("/sesiones/<int:id_sesion>/acta")
@gestion_required
def generar_acta(id_sesion):
    if models.obtener_sesion(id_sesion) is None:
        abort(404)
    ok, mensaje = models.generar_acta(
        id_sesion, request.form.get("asistentes", ""), request.form.get("notas", ""),
        session["usuario"]["id_usuario"],
    )
    flash(mensaje, "success" if ok else "error")
    if ok:
        return redirect(url_for("ver_acta", id_sesion=id_sesion))
    return redirect(url_for("detalle_sesion", id_sesion=id_sesion))


@app.get("/sesiones/<int:id_sesion>/acta")
@comite_required
def ver_acta(id_sesion):
    acta = models.obtener_acta(id_sesion)
    if acta is None:
        abort(404)
    return render_template("acta.html", acta=acta, sesion_c=models.obtener_sesion(id_sesion))


@app.get("/sesiones/<int:id_sesion>/acta.txt")
@comite_required
def descargar_acta(id_sesion):
    acta = models.obtener_acta(id_sesion)
    if acta is None:
        abort(404)
    return Response(
        acta["contenido"], mimetype="text/plain; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={acta['numero']}.txt"},
    )


@app.get("/decisiones")
@login_required
def decisiones():
    decision = request.args.get("decision") or None
    q = request.args.get("q", "").strip() or None
    return render_template(
        "decisiones.html",
        decisiones=models.listar_decisiones(_id_si_investigador(), decision, q),
        opciones=list(models.DECISIONES),
        actas=models.listar_actas() if rol_actual() in ROLES_COMITE else [],
    )


# ---------------------------------------------------------------------------
# Notificaciones
# ---------------------------------------------------------------------------
@app.get("/notificaciones")
@login_required
def notificaciones():
    return render_template(
        "notificaciones.html",
        notificaciones=models.listar_notificaciones(session["usuario"]["id_usuario"]),
    )


@app.post("/notificaciones/leer")
@login_required
def leer_notificaciones():
    models.marcar_leida(session["usuario"]["id_usuario"])
    return redirect(url_for("notificaciones"))


@app.get("/notificaciones/<int:id_notificacion>")
@login_required
def abrir_notificacion(id_notificacion):
    enlace = models.marcar_leida(session["usuario"]["id_usuario"], id_notificacion)
    if enlace and enlace.startswith("/") and not enlace.startswith("//"):
        return redirect(enlace)
    return redirect(url_for("notificaciones"))


# ---------------------------------------------------------------------------
# Reportes
# ---------------------------------------------------------------------------
@app.get("/reportes")
@comite_required
def reportes():
    desde = _fecha_valida(request.args.get("desde"))
    hasta = _fecha_valida(request.args.get("hasta"))
    conteo = models.conteo_por_estado(desde=desde, hasta=hasta)
    return render_template(
        "reportes.html",
        conteo=conteo,
        total=sum(conteo.values()),
        r=models.reportes(desde, hasta),
        vencidas=models.listar_solicitudes(solo_vencidas=True),
        desde=desde,
        hasta=hasta,
    )


@app.get("/reportes/solicitudes.csv")
@comite_required
def exportar_solicitudes():
    filas = models.listar_solicitudes(
        estado=request.args.get("estado") or None,
        desde=_fecha_valida(request.args.get("desde")),
        hasta=_fecha_valida(request.args.get("hasta")),
    )
    salida = io.StringIO()
    writer = csv.writer(salida, delimiter=";")
    writer.writerow(["Código", "Título", "Tipo", "Investigador", "Programa", "Estado", "Prioridad",
                     "Fecha radicación", "Fecha límite", "Vencida", "Responsables"])
    for s in filas:
        writer.writerow([s["codigo"], s["titulo"], s["tipo"], s["investigador"], s["programa"] or "",
                         s["estado"], s["prioridad"], formato_fecha(s["fecha"]), s["fecha_limite"] or "",
                         "Sí" if s["vencida"] else "No", s["responsables"] or ""])
    return Response(
        "﻿" + salida.getvalue(), mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=solicitudes_{models.hoy()}.csv"},
    )


@app.get("/reportes/decisiones.csv")
@comite_required
def exportar_decisiones():
    salida = io.StringIO()
    writer = csv.writer(salida, delimiter=";")
    writer.writerow(["Fecha", "Sesión", "Código", "Título", "Tipo", "Investigador", "Decisión", "Observación"])
    for d in models.listar_decisiones():
        writer.writerow([formato_fecha(d["fecha"]), d["sesion"] or "", d["codigo"], d["titulo"], d["tipo"],
                         d["investigador"], d["decision"], d["observacion"] or ""])
    return Response(
        "﻿" + salida.getvalue(), mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=decisiones_{models.hoy()}.csv"},
    )


# ---------------------------------------------------------------------------
# Usuarios (administrador)
# ---------------------------------------------------------------------------
@app.get("/usuarios")
@admin_required
def usuarios():
    return render_template("usuarios.html", usuarios=models.listar_usuarios())


@app.route("/usuarios/nuevo", methods=["GET", "POST"])
@admin_required
def nuevo_usuario():
    return formulario_usuario(None)


@app.route("/usuarios/<int:id_usuario>/editar", methods=["GET", "POST"])
@admin_required
def editar_usuario(id_usuario):
    usuario = models.obtener_usuario(id_usuario)
    if usuario is None:
        abort(404)
    return formulario_usuario(usuario)


def formulario_usuario(usuario):
    roles = models.listar_roles()
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        correo = request.form.get("correo", "").strip().lower()
        password = request.form.get("password", "").strip()
        id_rol = request.form.get("id_rol", type=int)
        activo = request.form.get("activo") == "1"
        if not nombre or not correo or id_rol not in {rol["id_rol"] for rol in roles}:
            flash("Complete los campos obligatorios.", "error")
        elif usuario:
            if usuario["id_usuario"] == session["usuario"]["id_usuario"]:
                activo = True
            ok, mensaje = models.actualizar_usuario(
                usuario["id_usuario"], nombre, correo, id_rol, password or None, activo
            )
            flash(mensaje, "success" if ok else "error")
            if ok:
                return redirect(url_for("usuarios"))
        else:
            ok, mensaje = models.crear_usuario(nombre, correo, password, id_rol)
            flash(mensaje, "success" if ok else "error")
            if ok:
                return redirect(url_for("usuarios"))
    return render_template("usuario_form.html", usuario=usuario, roles=roles)


@app.post("/usuarios/<int:id_usuario>/eliminar")
@admin_required
def eliminar_usuario(id_usuario):
    if id_usuario == session["usuario"]["id_usuario"]:
        flash("No puede eliminarse a sí mismo.", "error")
    elif models.obtener_usuario(id_usuario) is None:
        abort(404)
    else:
        flash(models.eliminar_usuario(id_usuario), "success")
    return redirect(url_for("usuarios"))


# ---------------------------------------------------------------------------
# Errores
# ---------------------------------------------------------------------------
@app.errorhandler(403)
def forbidden(_error):
    return render_template("error.html", code=403, message="No tiene permiso para realizar esta acción."), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="No se encontró el recurso solicitado."), 404


@app.errorhandler(413)
def demasiado_grande(_error):
    return render_template("error.html", code=413, message="El archivo supera el tamaño máximo de 16 MB."), 413


if __name__ == "__main__":
    models.init_db()
    app.run(debug=True)
