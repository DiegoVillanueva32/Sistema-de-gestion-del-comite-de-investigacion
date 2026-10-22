"""Aplicación web del Comité de Investigación."""
from functools import wraps
import os

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for

import models


ESTADOS = ["Recibida", "En revisión", "Aprobada", "Rechazada"]
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "FLASK_SECRET_KEY", "clave-de-desarrollo-comite"
)


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "usuario" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped_view(*args, **kwargs):
        if session["usuario"]["rol"] != "Administrador":
            abort(403)
        return view(*args, **kwargs)

    return wrapped_view


@app.get("/")
def index():
    if "usuario" in session:
        return redirect(url_for("solicitudes"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if "usuario" in session:
        return redirect(url_for("solicitudes"))

    if request.method == "POST":
        correo = request.form.get("correo", "").strip()
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
                return redirect(url_for("solicitudes"))
            flash("Correo o contraseña incorrectos.", "error")

    return render_template("login.html")


@app.post("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/solicitudes")
@login_required
def solicitudes():
    usuario = session["usuario"]
    id_usuario = usuario["id_usuario"] if usuario["rol"] == "Investigador" else None
    return render_template(
        "solicitudes.html",
        solicitudes=models.listar_solicitudes(id_usuario),
        usuario=usuario,
    )


@app.route("/solicitudes/nueva", methods=["GET", "POST"])
@login_required
def nueva_solicitud():
    return formulario_solicitud(None)


@app.route("/solicitudes/<int:id_solicitud>/editar", methods=["GET", "POST"])
@login_required
def editar_solicitud(id_solicitud):
    usuario = session["usuario"]
    solicitud = models.obtener_solicitud(
        id_solicitud,
        usuario["id_usuario"] if usuario["rol"] == "Investigador" else None,
    )
    if solicitud is None:
        abort(404)
    return formulario_solicitud(solicitud)


def formulario_solicitud(solicitud):
    tipos = models.listar_tipos()
    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        id_tipo = request.form.get("id_tipo", type=int)
        estado = request.form.get("estado", "Recibida")
        tipos_validos = {tipo["id_tipo"] for tipo in tipos}

        if not titulo or id_tipo not in tipos_validos:
            flash("Título y tipo son obligatorios.", "error")
        elif estado not in ESTADOS:
            flash("Seleccione un estado válido.", "error")
        else:
            if solicitud:
                ok, mensaje = models.actualizar_solicitud(
                    solicitud["id_solicitud"], titulo, descripcion, id_tipo, estado
                )
            else:
                ok, mensaje = models.crear_solicitud(
                    session["usuario"]["id_usuario"], id_tipo, titulo, descripcion
                )
            flash(mensaje, "success" if ok else "error")
            if ok:
                return redirect(url_for("solicitudes"))

    return render_template(
        "solicitud_form.html",
        solicitud=solicitud,
        tipos=tipos,
        estados=ESTADOS,
    )


@app.post("/solicitudes/<int:id_solicitud>/eliminar")
@login_required
def eliminar_solicitud(id_solicitud):
    if session["usuario"]["rol"] == "Investigador":
        abort(403)
    if models.obtener_solicitud(id_solicitud) is None:
        abort(404)
    models.eliminar_solicitud(id_solicitud)
    flash("Solicitud eliminada.", "success")
    return redirect(url_for("solicitudes"))


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
        correo = request.form.get("correo", "").strip()
        password = request.form.get("password", "").strip()
        id_rol = request.form.get("id_rol", type=int)
        roles_validos = {rol["id_rol"] for rol in roles}

        if not nombre or not correo or id_rol not in roles_validos:
            flash("Complete los campos obligatorios.", "error")
        elif not usuario and not password:
            flash("La contraseña es obligatoria para crear un usuario.", "error")
        else:
            if usuario:
                ok, mensaje = models.actualizar_usuario(
                    usuario["id_usuario"], nombre, correo, id_rol
                )
            else:
                ok, mensaje = models.crear_usuario(nombre, correo, password, id_rol)
            flash(mensaje, "success" if ok else "error")
            if ok:
                return redirect(url_for("usuarios"))

    return render_template("usuario_form.html", usuario=usuario, roles=roles)


@app.post("/usuarios/<int:id_usuario>/eliminar")
@admin_required
def eliminar_usuario(id_usuario):
    administrador = session["usuario"]
    if id_usuario == administrador["id_usuario"]:
        flash("No puede eliminarse a sí mismo.", "error")
    elif models.obtener_usuario(id_usuario) is None:
        abort(404)
    else:
        models.eliminar_usuario(id_usuario)
        flash("Usuario eliminado.", "success")
    return redirect(url_for("usuarios"))


@app.errorhandler(403)
def forbidden(_error):
    return render_template("error.html", code=403, message="No tiene permiso para realizar esta acción."), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="No se encontró el recurso solicitado."), 404


if __name__ == "__main__":
    models.init_db()
    app.run(debug=True)
