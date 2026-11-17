"""Inicializa la base de datos en la nube usando credenciales_nube.txt.

Uso:
    python iniciar_nube.py            crea tablas, roles, tipos y usuarios demo
    python iniciar_nube.py --demo     además carga el escenario de demostración (datos_demo.py)

Lee las credenciales de credenciales_nube.txt (archivo ignorado por git), así la
contraseña nunca queda en el código ni en GitHub.
"""
import os
import sys

ARCHIVO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credenciales_nube.txt")
OBLIGATORIAS = ("MYSQL_HOST", "MYSQL_PORT", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE")


def cargar_credenciales():
    if not os.path.exists(ARCHIVO):
        sys.exit(f"No se encontró {ARCHIVO}. Créelo con los datos de su base en la nube.")
    datos = {}
    with open(ARCHIVO, encoding="utf-8") as archivo:
        for linea in archivo:
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                clave, valor = linea.split("=", 1)
                datos[clave.strip()] = valor.strip().strip('"').strip("'")
    faltan = [c for c in OBLIGATORIAS if not datos.get(c)]
    if faltan:
        sys.exit("Faltan datos en credenciales_nube.txt: " + ", ".join(faltan))
    # Se definen ANTES de importar models para que tengan prioridad sobre el .env local.
    os.environ.update(datos)
    return datos


def main():
    datos = cargar_credenciales()
    print(f"Conectando a {datos['MYSQL_HOST']}:{datos['MYSQL_PORT']} (base {datos['MYSQL_DATABASE']})...")
    import models

    models.init_db()
    print("Tablas, roles, tipos de solicitud y usuarios demo listos.")
    if "--demo" in sys.argv:
        import datos_demo

        datos_demo.main()
        print("Datos de demostración cargados.")
    print("Listo. Ahora configure las mismas variables en Vercel y despliegue.")


if __name__ == "__main__":
    main()
