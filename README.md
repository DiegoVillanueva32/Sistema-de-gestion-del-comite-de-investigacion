# Comité I+D — Sistema de Gestión del Comité de Investigación

Aplicación web full stack (Python + Flask, HTML5/CSS3/JavaScript y MySQL) que centraliza las solicitudes que los investigadores presentan ante el Comité de Investigación: radicación, carga y validación de documentos, revisión por el comité, solicitudes de ajuste, sesiones, decisiones, actas, notificaciones y reportes, con trazabilidad completa de cada trámite.

**Usuarios:** investigadores, integrantes del comité, secretario(a) del comité y administrador.

> Proyecto final — Herramientas Computacionales, Ingeniería de Sistemas, Universidad Cooperativa de Colombia (Momento evaluativo 3).

## El problema

El trámite ante el comité se hacía por correo y carpetas compartidas: los documentos se perdían entre versiones, el investigador no sabía en qué estado estaba su solicitud, nadie veía quién la revisaba ni si el plazo se había vencido, y cada acta de sesión se transcribía a mano.

## Objetivos

**General:** desarrollar una aplicación web que gestione de principio a fin las solicitudes ante el Comité de Investigación, con trazabilidad de cada paso.

**Específicos:**

1. Permitir que los investigadores se registren, radiquen solicitudes y carguen documentos con versiones.
2. Validar los requisitos de cada tipo de solicitud y bloquear el avance de solicitudes incompletas.
3. Asignar revisores con fechas límite y registrar sus conceptos y solicitudes de ajuste.
4. Programar sesiones, consolidar la agenda, registrar decisiones y generar el acta automáticamente.
5. Dar visibilidad con notificaciones, búsquedas, filtros, reportes e indicadores exportables.
6. Ofrecer una interfaz clara, adaptable al celular y con validaciones inmediatas en el cliente.

## Tecnologías usadas

| Capa | Tecnología | Uso en el proyecto |
| --- | --- | --- |
| Backend | Python 3.11+ y **Flask 3** | Rutas, controladores, sesiones, permisos por rol, API JSON |
| Plantillas | Jinja2 | Renderizado dinámico en el servidor con herencia (`base.html`) |
| Frontend | HTML5 semántico, **CSS3** propio (variables, grid, flexbox, animaciones) | Interfaz con identidad visual oscura, responsive |
| Framework CSS | **Tailwind CSS 3** (CLI, `tailwind.config.js`) | Componentes con `@apply` (botones, alertas, estados, KPIs, tarjetas) y utilidades en las plantillas para layout y responsive |
| Interactividad | **JavaScript** puro (ES2020, sin librerías) | Eventos, validación en el cliente, Fetch API, filtros y orden de tablas |
| Base de datos | **MySQL 8** (MySQL Server + Workbench) | Modelo relacional de 18 tablas con llaves primarias y foráneas |
| Conector | mysql-connector-python | Pool de conexiones y consultas parametrizadas |
| Seguridad | Werkzeug | Hash de contraseñas con sal (scrypt), nombres de archivo seguros |

## Arquitectura (MVC)

```
 Navegador (HTML5 + CSS3 + JavaScript)
     │  formularios (POST)        ▲ HTML renderizado
     │  Fetch API (JSON)          │ JSON
     ▼                            │
 main.py ── Controlador ──────────┘   43 rutas, decoradores de permisos, manejo de errores, API
     │ llama funciones
     ▼
 models.py ── Modelo                  lógica del trámite, transacciones, consultas SQL
     │ SQL parametrizado
     ▼
 MySQL (comite_db)                    18 tablas relacionadas (PK, FK, UNIQUE)

 templates/ ── Vista                  19 plantillas Jinja2 que heredan de base.html
 static/    ── style.css + app.js     estilos e interactividad del cliente
```

- **Modelo (`models.py`):** esquema, migraciones, reglas del flujo (estados, validación de requisitos, decisiones, actas) y acceso a datos dentro de transacciones (`with db()` hace *commit* o *rollback*).
- **Vista (`templates/`):** cada pantalla es una plantilla que extiende `base.html`, donde viven el menú, los mensajes y los estilos.
- **Controlador (`main.py`):** recibe la petición, verifica sesión y rol con decoradores (`@login_required`, `@comite_required`…), valida el formulario, llama al modelo y elige la vista o responde JSON.

### ¿Por qué varias plantillas y no una sola página con `div` ocultos?

- **Seguridad:** el servidor solo envía la vista que el rol puede ver; un `div` oculto con CSS igual llega al navegador.
- **Una URL por pantalla:** `/solicitudes/13` se puede guardar o compartir y el botón Atrás funciona.
- **Sin duplicar código:** la herencia de Jinja2 deja el menú y los estilos en un solo archivo.
- **Trabajo en equipo:** cada integrante edita sus vistas con menos conflictos en git.

El JavaScript se usa donde aporta (validaciones, búsqueda dinámica, notificaciones en vivo), no para simular la navegación.

## Instalación

Requisitos: Python 3.11 o superior y MySQL Server 8 en ejecución (en Windows: `services.msc` → servicio `MySQL80`, o desde Workbench en *Server → Startup/Shutdown*).

1. Clona el repositorio y entra a la carpeta del proyecto.
2. (Recomendado) Crea un entorno virtual:

   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. Instala las dependencias:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Configura la conexión: copia `.env.example` como `.env` y escribe la contraseña de tu MySQL (los mismos datos que usas en Workbench):

   ```powershell
   copy .env.example .env
   ```

   | Variable | Valor por defecto | Descripción |
   | --- | --- | --- |
   | `MYSQL_HOST` | `127.0.0.1` | Servidor de MySQL |
   | `MYSQL_PORT` | `3306` | Puerto |
   | `MYSQL_USER` | `root` | Usuario |
   | `MYSQL_PASSWORD` | *(vacía)* | Contraseña del usuario |
   | `MYSQL_DATABASE` | `comite_db` | Base de datos (se crea sola) |
   | `FLASK_SECRET_KEY` | clave de desarrollo | Clave para firmar la sesión |

   El archivo `.env` no se sube a GitHub. También puedes definir las variables en la terminal (`$env:MYSQL_PASSWORD = "..."`); estas tienen prioridad sobre el archivo.

5. (Opcional) Carga los datos de demostración:

   ```powershell
   python datos_demo.py
   ```

6. Inicia la aplicación y abre `http://127.0.0.1:5000`:

   ```powershell
   python main.py
   ```

La aplicación crea automáticamente la base `comite_db`, sus tablas y los tipos de solicitud con sus requisitos. Si ya tenías la base de una versión anterior, agrega las tablas y columnas nuevas sin borrar datos. No hace falta importar ningún archivo SQL. Los documentos cargados se guardan en la base de datos (columna `documento.contenido`) y además se copian a la carpeta `uploads/`.

## Estilos con Tailwind CSS

Los estilos combinan dos capas:

- `src/tailwind.css` → fuente de Tailwind: los componentes del sistema escritos con `@apply` (`.button`, `.alert`, `.status`, `.kpi`, `.panel`…). Las plantillas también usan utilidades de Tailwind directamente (`grid grid-cols-2 gap-4 max-[1100px]:grid-cols-1`, `text-muted`, `flex justify-end`…).
- `tailwind.config.js` → paleta del tema "Nocturno", tipografías y breakpoints. Escanea `templates/`, `static/app.js` y `main.py`.
- `static/style.css` → reset, variables de color y piezas con efectos propios (barra lateral, buscador, línea de progreso, modal).

El CSS compilado (`static/tailwind.css`) ya está incluido en el repositorio, así que **no hace falta Node.js para ejecutar la aplicación**. Solo si cambias clases en las plantillas, vuelve a compilarlo:

```powershell
npm install
npm run build:css      # o: npm run watch:css mientras desarrollas
```

## Despliegue en Vercel

Vercel no puede conectarse a un MySQL instalado en tu computador, así que la base debe estar en la nube (por ejemplo **Aiven for MySQL**, plan gratuito).

1. Crea un servicio MySQL en la nube y copia sus datos de conexión (host, puerto, usuario, contraseña, base; en Aiven la base es `defaultdb`).
2. Crea las tablas y los usuarios demo **desde tu computador**. Pega los datos de conexión en `credenciales_nube.txt` (archivo ignorado por git; si no existe, créalo con las mismas variables de `.env.example`) y ejecuta:

   ```powershell
   python iniciar_nube.py --demo     # --demo también carga el escenario de demostración
   ```

   O manualmente, con variables de entorno (en PowerShell):

   ```powershell
   $env:MYSQL_HOST="<host>"; $env:MYSQL_PORT="<puerto>"; $env:MYSQL_USER="<usuario>"
   $env:MYSQL_PASSWORD="<contraseña>"; $env:MYSQL_DATABASE="defaultdb"
   flask --app main init-db
   python datos_demo.py      # opcional: carga el escenario de demostración
   ```

3. Sube el proyecto a GitHub, entra a [vercel.com](https://vercel.com) → **Add New → Project** → importa el repositorio (Framework preset: *Other*).
4. En **Environment Variables** agrega `DATABASE_URL` (la URL pública `mysql://usuario:clave@host:puerto/base` de tu proveedor) y `FLASK_SECRET_KEY`, y luego haz clic en **Deploy**. También puedes usar las variables sueltas `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD` y `MYSQL_DATABASE`.

Archivos usados por Vercel: `api/index.py` (expone la app Flask), `vercel.json` (envía todas las rutas a Flask) y `.vercelignore`. En Vercel cada archivo subido puede pesar como máximo 4.5 MB (límite de la plataforma).

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

## Interactividad en el cliente (JavaScript)

Todo está en `static/app.js`, en JavaScript puro y organizado por módulos que se activan solo si la página tiene los elementos que usan.

| Funcionalidad | Eventos / API | Dónde verla |
| --- | --- | --- |
| Validación en el cliente con mensajes en español (obligatorios, correo, longitud mínima, formato, contraseñas que coinciden, fecha no anterior a hoy, tamaño y extensión del archivo) | `submit`, `blur`, `input`, `change` | Registro, login, radicar solicitud, usuarios, sesiones, carga de documentos |
| Búsqueda dinámica de solicitudes mientras se escribe, con navegación por teclado y atajo `/` o `Ctrl+K` | `input`, `keydown`, **Fetch API** + `AbortController` | Buscador del menú lateral |
| Notificaciones en vivo: el contador se actualiza cada 30 s y el panel permite marcar como leídas sin recargar | `click`, **Fetch API** (GET y POST) | Campana del menú |
| Filtro instantáneo de tablas con contador de resultados | `input`, `keydown` | Solicitudes, usuarios, investigadores, decisiones, sesiones |
| Orden de columnas al hacer clic en el encabezado (también con teclado) | `click`, `keydown` | Las mismas tablas |
| Modal propio de confirmación para eliminar | `submit`, `click`, `<dialog>` | Eliminar solicitud, sesión o usuario |
| Mostrar u ocultar contraseña, contador de caracteres, requisitos según el tipo de solicitud | `click`, `input`, `change` | Formularios |
| Aviso de cambios sin guardar, botón con indicador de carga para evitar envíos dobles | `beforeunload`, `submit` | Radicar / editar solicitud |
| Animaciones de KPIs y barras de reportes (respetan *reducir movimiento*) | `requestAnimationFrame` | Inicio y Reportes |
| Menú desplegable en celular | `click` | Pantallas de menos de 900 px |

La validación en el cliente mejora la experiencia, pero el servidor vuelve a validar todo: nunca se confía solo en el navegador.

## API JSON

| Método | Ruta | Respuesta |
| --- | --- | --- |
| GET | `/api/buscar?q=texto` | Solicitudes que coinciden (el investigador solo ve las suyas) |
| GET | `/api/notificaciones` | Número de pendientes y últimas 5 notificaciones |
| POST | `/api/notificaciones/leer` | Marca todas como leídas |

Todas exigen sesión iniciada.

## Base de datos

MySQL con 18 tablas InnoDB, llaves primarias autoincrementales, 23 llaves foráneas y restricciones `UNIQUE` (correo, documento, código de solicitud, número de sesión). Tablas principales:

```
rol ─< usuario ─── investigador
          │
tipo_solicitud ─< requisito          sesion_comite ─< agenda_sesion >─ solicitud
          │                                │
          └──< solicitud >── investigador  └── acta
                  │
     documento, validacion_requisito, asignacion_revision, revision,
     observacion, decision, historial_estado, actuacion
                                                      notificacion >── usuario
```

- **Integridad:** las llaves foráneas impiden registros huérfanos; un usuario con historial no se borra, se desactiva.
- **Transacciones:** cada operación se confirma completa o se revierte (`models.db()`).
- **Seguridad:** todas las consultas usan parámetros (sin concatenar texto), lo que evita la inyección SQL; las contraseñas se guardan con hash y sal. Las cuentas creadas con la versión anterior (SHA-256) se actualizan solas al iniciar sesión.

## Manejo de errores

- Páginas propias para 403 (sin permiso), 404 (no existe), 413 (archivo de más de 16 MB) y 500 (error inesperado, que queda registrado en el log).
- Validaciones en el servidor con mensajes claros (correo duplicado, requisitos faltantes, formato de archivo, fechas inválidas).

## Cumplimiento de los lineamientos del proyecto

| Lineamiento | Cómo se cumple |
| --- | --- |
| Python 3.x + Flask | `main.py` (Flask 3) |
| Arquitectura MVC | Modelo `models.py`, Vista `templates/`, Controlador `main.py` |
| Rutas, controladores, formularios, validaciones | 43 rutas + 3 de API; validación en servidor y cliente |
| CRUD completo | Usuarios (crear, ver, editar, eliminar), solicitudes, sesiones, documentos |
| Conexión a base de datos y manejo de errores | MySQL con pool de conexiones; manejadores 403, 404, 413 y 500 |
| HTML5 semántico, CSS3 propio, JavaScript | `header`, `nav`, `main`, `section`, `aside`, `dialog`; `style.css`; `app.js` |
| Eventos JS, validación en cliente, renderizado dinámico | Ver *Interactividad en el cliente* |
| Valor agregado: animaciones, Fetch API, responsive | Animaciones CSS/JS, buscador y notificaciones con Fetch, diseño adaptable |
| Gestión (CRUD) + Consulta (reportes, filtros, búsquedas) | Módulos de solicitudes, usuarios y sesiones; Reportes con CSV, filtros y buscador |
| Modelo relacional con PK, FK e integridad | 18 tablas, 23 llaves foráneas |
| README, requirements.txt, `.env` | Este archivo, `requirements.txt`, `.env.example` |

## Estructura

```
main.py            Controlador: rutas Flask, permisos, API JSON y manejo de errores
models.py          Modelo: esquema MySQL, migraciones y lógica del trámite
datos_demo.py      Escenario de demostración completo
templates/         Vistas Jinja2 (base.html + 18 vistas)
static/style.css   Estilos propios: reset, variables del tema y efectos especiales
static/tailwind.css  CSS de Tailwind compilado (generado desde src/tailwind.css)
src/tailwind.css   Fuente de Tailwind: componentes con @apply
tailwind.config.js Configuración de Tailwind (paleta, fuentes, archivos a escanear)
package.json       Scripts para compilar Tailwind (npm run build:css)
static/app.js      Interactividad del cliente: validaciones, Fetch API, filtros, animaciones
.env.example       Plantilla de configuración de la conexión
uploads/           Copia local de documentos cargados (no se sube a git)
api/index.py       Punto de entrada para Vercel
vercel.json        Configuración de Vercel (todas las rutas van a Flask)
```
