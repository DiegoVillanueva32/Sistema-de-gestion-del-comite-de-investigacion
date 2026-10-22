# Comité de Investigación

Aplicación web de prototipo con Flask, Jinja2 y MySQL para XAMPP.

## Iniciar con XAMPP

1. En el panel de XAMPP, inicia **MySQL**. Inicia también **Apache** si vas a abrir phpMyAdmin desde `http://localhost/phpmyadmin`.
2. Instala las dependencias desde la carpeta del proyecto:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Inicia la aplicación:

   ```powershell
   python main.py
   ```

La aplicación crea automáticamente la base `comite_db` y sus tablas al iniciar. En phpMyAdmin, selecciona o actualiza la lista de bases de datos para verla. No es necesario importar un archivo SQL.

La configuración predeterminada de XAMPP es `127.0.0.1:3306`, usuario `root` y contraseña vacía. Si tu instalación utiliza otros valores, configúralos antes de iniciar Flask:

```powershell
$env:MYSQL_HOST = "127.0.0.1"
$env:MYSQL_PORT = "3306"
$env:MYSQL_USER = "root"
$env:MYSQL_PASSWORD = "tu contraseña"
$env:MYSQL_DATABASE = "comite_db"
python main.py
```

Si la tabla de usuarios de `comite_db` está vacía, se cargan los usuarios demo:

| Rol | Correo | Contraseña |
| --- | --- | --- |
| Administrador | `admin@comite.edu.co` | `admin123` |
| Secretario | `secretaria@comite.edu.co` | `secre123` |
| Comité | `comite@comite.edu.co` | `comite123` |
| Investigador | `investigador@comite.edu.co` | `invest123` |

## Cargar solicitudes de prueba

Con MySQL de XAMPP iniciado, ejecuta una vez (o de nuevo cuando quieras comprobar los datos):

```powershell
python seed_demo_data.py
```

El script agrega cuatro solicitudes de demostración con distintos tipos, estados y prioridades. Es idempotente: volver a ejecutarlo no duplica esas solicitudes ni borra datos existentes. Si la base de datos está vacía, también inicializa el esquema y las cuentas demo.

La aplicación permite probar el inicio de sesión, la lista, creación, edición y eliminación de solicitudes, además de la administración de usuarios con el rol Administrador. Las tablas para documentos, validaciones, revisiones y sesiones están en el esquema, pero sus pantallas y operaciones todavía no están implementadas.
