# Sistema de Gestión del Comité de Investigación

Aplicación web con Flask, Jinja2 y MySQL (MySQL Server + MySQL Workbench) que centraliza las solicitudes de los investigadores ante el Comité de Investigación: radicación, verificación de documentos, revisión, ajustes, sesiones, decisiones, actas, notificaciones y reportes, con trazabilidad completa de cada trámite.

**Usuarios:** investigadores, integrantes del comité, secretario(a) del comité y administrador.

## Iniciar con MySQL Server y Workbench

1. Verifica que el servicio **MySQL Server** esté corriendo (en Windows: `services.msc` → servicio `MySQL80`, o desde Workbench en *Server → Startup/Shutdown*). Workbench sirve para ver las tablas y los datos de `comite_db`.
2. Instala las dependencias desde la carpeta del proyecto:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. (Opcional) Carga los datos de demostración:

   ```powershell
   python datos_demo.py
   ```

4. Inicia la aplicación y abre `http://127.0.0.1:5000`:

   ```powershell
   python main.py
   ```

La aplicación crea automáticamente la base `comite_db`, sus tablas y los tipos de solicitud con sus requisitos. Si ya tenías la base de la versión anterior, agrega las tablas y columnas nuevas sin borrar datos. No hace falta importar ningún archivo SQL. Los documentos cargados se guardan en la carpeta `uploads/`.

La aplicación se conecta por defecto a `127.0.0.1:3306` con el usuario `root` y la contraseña vacía. Si al instalar MySQL Server le pusiste una contraseña a `root` (lo normal), o usas otros valores, configúralos antes de iniciar (son los mismos datos de la conexión que usas en Workbench):

```powershell
$env:MYSQL_HOST = "127.0.0.1"
$env:MYSQL_PORT = "3306"
$env:MYSQL_USER = "root"
$env:MYSQL_PASSWORD = "tu contraseña"
$env:MYSQL_DATABASE = "comite_db"
python main.py
```

## Usuarios demo

| Rol | Correo | Contraseña |
| --- | --- | --- |
| Administrador | `admin@comite.edu.co` | `admin123` |
| Secretario | `secretaria@comite.edu.co` | `secre123` |
| Comité | `comite@comite.edu.co` | `comite123` |
| Investigador | `investigador@comite.edu.co` | `invest123` |

`datos_demo.py` agrega además tres investigadores (`laura.martinez@…`, `carlos.perez@…`, `ana.herrera@…`, contraseña `invest123`), dos integrantes del comité (`marta.vega@…`, `jorge.ruiz@…`, contraseña `comite123`), 13 solicitudes en todos los estados, una sesión realizada con su acta y una sesión próxima con agenda. Puedes ejecutarlo varias veces: si los datos ya existen, no hace nada.

## Flujo de una solicitud

```
Radicación ─► Recibida ─► Validación de requisitos ─┬─► Pendiente por documentos ─► (investigador carga y reenvía) ─► Recibida
                                                    └─► En revisión ─► Asignación de responsables ─► Conceptos del comité
                                                                        │
                                       Requiere ajustes ◄── Solicitud de ajuste ─┤ (investigador ajusta y reenvía ─► En revisión)
                                                                        ▼
                                                              Lista para comité ─► Agenda de sesión ─► Decisión
                                                                                                         │
                                       Aprobada / Aprobada con ajustes / Rechazada (Aplazada vuelve a Lista para comité)
                                                                        ▼
                                                                  Acta ─► Cerrada
```

Cada paso queda en el **historial de actuaciones** de la solicitud y genera **notificaciones** a las personas involucradas.

## Funcionalidades requeridas y dónde están

| Requisito del proyecto | Implementación |
| --- | --- |
| Registro de investigadores | `/registro` (público) y `/perfil`; listado en **Investigadores** |
| Radicación de solicitudes | **Solicitudes → Radicar solicitud**; código consecutivo `SOL-AAAA-NNNN` |
| Selección del tipo de solicitud | 5 tipos (proyecto, ponencia, publicación, monitoría, informe final); el formulario muestra los documentos que exige cada tipo |
| Carga de documentos | Sección **Documentos** del detalle; asociados a un requisito, con versiones y descarga protegida |
| Validación de requisitos | Lista de requisitos del tipo con «cumple» y observación; si falta un requisito obligatorio la solicitud pasa a *Pendiente por documentos* |
| Revisión por parte del comité | Conceptos *Favorable*, *Favorable con ajustes* o *Desfavorable* con observaciones |
| Asignación de responsables | El secretario asigna integrantes del comité con fecha límite; se ven en la lista y en el dashboard de cada revisor |
| Estados de solicitud | 9 estados con colores, línea de progreso y cambio manual con motivo |
| Observaciones | Observaciones generales de cualquier participante |
| Solicitud de ajustes | Observación tipo *Solicitud de ajuste* → estado *Requiere ajustes*; el investigador responde y reenvía |
| Seguimiento de fechas | Fecha límite de la solicitud y de cada revisión; alertas de vencidas en lista, dashboard y reportes |
| Historial de actuaciones | Línea de tiempo con cada acción, usuario y fecha (tablas `actuacion` e `historial_estado`) |
| Gestión de sesiones del comité | **Sesiones**: programar, editar, cancelar o eliminar |
| Agenda | Orden del día de cada sesión, con conceptos de revisión de cada solicitud |
| Consolidación de solicitudes por sesión | Botón **Consolidar** que agenda todas las solicitudes *Lista para comité* |
| Generación de actas | El acta se arma automáticamente con asistentes, orden del día, decisiones y resumen; tiene versiones, se puede imprimir o guardar como PDF y descargar en .txt |
| Consulta de decisiones | **Decisiones**: filtro por tipo de decisión y búsqueda; el investigador ve las suyas |
| Notificaciones | Campana con contador; avisos de radicación, cambios de estado, asignaciones, ajustes, sesiones, decisiones y actas |
| Reportes | **Reportes**: indicadores por estado, tipo, mes, programa, decisiones, tasa de aprobación, tiempo promedio, carga por revisor y vencidas; exportación CSV |
| Dashboard | **Inicio**: totales por estado (recibidas, en revisión, pendientes por documentos, listas para comité, aprobadas, aprobadas con ajustes, rechazadas, cerradas), revisiones pendientes, próximas sesiones y actividad reciente |

## Permisos por rol

| Acción | Investigador | Comité | Secretario | Administrador |
| --- | :-: | :-: | :-: | :-: |
| Radicar y cargar documentos de sus solicitudes | ✔ | | | |
| Ver todas las solicitudes | | ✔ | ✔ | ✔ |
| Validar requisitos, asignar responsables, cambiar estado | | | ✔ | ✔ |
| Emitir concepto de revisión | | ✔ (si está asignado) | ✔ | ✔ |
| Solicitar ajustes | | ✔ | ✔ | ✔ |
| Gestionar sesiones, agenda, decisiones y actas | | solo consulta | ✔ | ✔ |
| Reportes | | ✔ | ✔ | ✔ |
| Administrar usuarios | | | | ✔ |

## Estructura

```
main.py            Rutas Flask y control de permisos
models.py          Esquema MySQL, migraciones y lógica de negocio
datos_demo.py      Escenario de demostración completo
templates/         Vistas Jinja2
static/style.css   Estilos
uploads/           Documentos cargados (se crea automáticamente; no se sube a git)
```
