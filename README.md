# Catálogo de Partituras

Aplicación web personal para catalogar, organizar y consultar una colección de partituras musicales. Permite saber exactamente qué tienes, en qué formato y dónde está guardado cada archivo, con un agente de chat con inteligencia artificial para hacer consultas en lenguaje natural en español.

---

## Características principales

- **Catálogo centralizado** — registra partituras digitales (PDF, MuseScore, Sibelius, MusicXML, etc.) y copias en papel
- **Escáner automático** — detecta archivos musicales en tus carpetas y los importa al catálogo con un paso de revisión
- **Importación desde CSV** — importa un inventario existente en formato CSV con un solo comando
- **Ubicación exacta** — cada partitura indica dónde está: Mac, iCloud, iPad, celular o papel
- **Búsqueda por título** — búsqueda insensible a acentos ("cancion" encuentra "Canción")
- **Filtros** — filtra por compositor, instrumento, dificultad y ubicación
- **Agente de chat con IA** — consulta tu colección en español con preguntas como:
  - "¿Tengo el Concierto de Aranjuez?"
  - "¿Qué tengo de Bach?"
  - "¿Qué partituras tengo solo en papel?"
  - "Dame algo de nivel intermedio para piano"
- **Acceso desde cualquier dispositivo** — corre en tu Mac y es accesible desde iPad y celular por WiFi local

---

## Capturas de pantalla

> La app se sirve en `http://localhost:8000`

| Pantalla | Descripción |
|----------|-------------|
| `/` | Lista del catálogo con filtros y búsqueda |
| `/piezas/{id}` | Detalle de una partitura con sus archivos |
| `/agregar` | Formulario para agregar manualmente |
| `/escanear` | Escáner de carpetas con revisión previa |

---

## Requisitos

- **Python 3.11 o superior**
- **macOS** (probado en macOS; funciona en Linux con ajustes menores de rutas)
- **Cuenta de Anthropic** con API key (para el agente de chat)
  - Puedes obtener una en [console.anthropic.com](https://console.anthropic.com)

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/adrianarias2005-toexee/Catalogo-de-Partituras.git
cd Catalogo-de-Partituras
```

### 2. Instalar las dependencias de Python

Se recomienda usar un entorno virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

O directamente sin entorno virtual:

```bash
pip3 install -r requirements.txt
```

### 3. Crear el archivo de configuración

Copia el archivo de ejemplo y edítalo con tus datos:

```bash
cp .env.example .env
```

Abre `.env` con cualquier editor de texto y rellena los valores:

```env
# Ruta donde se guarda la base de datos (se crea automáticamente)
DB_PATH=partituras.db

# Carpetas que el escáner revisará por defecto (separadas por coma)
SCAN_FOLDERS=~/Documents/Musica

# Tu API key de Anthropic (necesaria para el agente de chat)
ANTHROPIC_API_KEY=sk-ant-...

# Puerto del servidor (8000 por defecto)
PORT=8000
```

> **Importante:** nunca subas el archivo `.env` a GitHub — ya está incluido en `.gitignore`.

---

## Importar un inventario CSV existente (opcional)

Si tienes un archivo CSV con partituras ya catalogadas, puedes importarlo antes de arrancar la app. El formato esperado tiene las columnas:

```
archivo, titulo, compositor, instrumentos, genero, ...
```

Ejecuta:

```bash
python3 -c "
import os
os.environ.setdefault('DB_PATH', 'partituras.db')
from app.database import SessionLocal, engine, Base
from app import models
Base.metadata.create_all(bind=engine)
from app.csv_import import import_csv
db = SessionLocal()
created, skipped = import_csv(db, os.path.expanduser('~/ruta/a/tu/inventario.csv'))
db.close()
print(f'Importadas: {created}, omitidas: {skipped}')
"
```

---

## Arrancar la aplicación

```bash
./run.sh
```

O equivalentemente:

```bash
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Luego abre en tu navegador:

```
http://localhost:8000
```

### Acceso desde iPad o celular

Como el servidor escucha en `0.0.0.0`, puedes acceder desde cualquier dispositivo en la misma red WiFi usando la IP de tu Mac:

```
http://192.168.1.X:8000
```

Puedes encontrar la IP de tu Mac en **Configuración del Sistema → Wi-Fi → Detalles**.

---

## Estructura del proyecto

```
Catalogo-de-Partituras/
├── app/
│   ├── main.py          # Servidor FastAPI, rutas HTML y montaje de estáticos
│   ├── config.py        # Configuración desde .env
│   ├── database.py      # Conexión SQLite con SQLAlchemy
│   ├── models.py        # Modelos ORM: Pieza y Archivo
│   ├── schemas.py       # Esquemas Pydantic para la API
│   ├── crud.py          # Operaciones de base de datos
│   ├── scanner.py       # Escáner de archivos (funciones puras)
│   ├── csv_import.py    # Importación desde CSV
│   ├── agent.py         # Agente de chat con Claude API
│   └── routers/
│       ├── catalog.py   # Endpoints /api/piezas
│       ├── scanner.py   # Endpoints /api/scan
│       └── chat.py      # Endpoint /api/chat
├── frontend/
│   ├── templates/       # Plantillas Jinja2
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── detail.html
│   │   ├── add.html
│   │   ├── scan_review.html
│   │   └── partials/
│   └── static/
│       ├── style.css
│       └── chat.js
├── tests/               # Suite de pruebas (67 tests)
├── requirements.txt
├── run.sh               # Script de arranque
├── .env.example         # Plantilla de configuración
└── .gitignore
```

---

## Formatos de archivo soportados

El escáner detecta automáticamente los siguientes tipos de archivo musical:

| Extensión | Formato |
|-----------|---------|
| `.pdf` | PDF (partitura escaneada o exportada) |
| `.mscz` / `.mscx` | MuseScore |
| `.mxl` / `.musicxml` | MusicXML |
| `.sib` | Sibelius |
| `.musx` | Finale |
| `.capx` | Capella |

---

## Uso del agente de chat

El agente requiere una `ANTHROPIC_API_KEY` configurada en `.env`. Una vez configurada, puedes preguntarle cosas como:

- **"¿Tengo la Suite nº 1 de Bach?"** → te dice si existe y en qué dispositivo está
- **"¿Qué tengo de Chopin?"** → lista todas las partituras de ese compositor
- **"¿Qué tengo para guitarra sola?"** → filtra por instrumento
- **"¿Qué tengo solo en papel sin versión digital?"** → detecta partituras sin archivo digital
- **"¿Qué tengo guardado en iCloud?"** → filtra por ubicación
- **"Dame algo de nivel intermedio para piano"** → recomendación con filtros
- **"¿Tengo las 6 Suites de Bach o solo algunas?"** → verifica completitud de una colección

---

## Ejecutar las pruebas

```bash
python3 -m pytest tests/ -v
```

La suite incluye 67 pruebas que cubren modelos, CRUD, escáner, importación CSV y la API REST.

---

## API REST

La app expone una API JSON completa en `/api/`:

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/piezas` | Lista de partituras (con filtros y paginación) |
| `GET` | `/api/piezas/search?q=` | Búsqueda por título |
| `POST` | `/api/piezas` | Crear nueva partitura |
| `GET` | `/api/piezas/{id}` | Detalle de una partitura |
| `PATCH` | `/api/piezas/{id}` | Actualizar datos |
| `DELETE` | `/api/piezas/{id}` | Eliminar |
| `POST` | `/api/piezas/{id}/archivos` | Agregar archivo a una partitura |
| `DELETE` | `/api/archivos/{id}` | Eliminar un archivo |
| `POST` | `/api/scan` | Iniciar escaneo de carpetas |
| `POST` | `/api/scan/confirm` | Confirmar candidatos al catálogo |
| `POST` | `/api/chat` | Enviar mensaje al agente de chat |

---

## Tecnologías utilizadas

| Tecnología | Uso |
|------------|-----|
| [FastAPI](https://fastapi.tiangolo.com) | Framework web y API REST |
| [SQLAlchemy](https://www.sqlalchemy.org) | ORM y manejo de base de datos |
| [SQLite](https://www.sqlite.org) | Base de datos local (un solo archivo) |
| [Pydantic](https://docs.pydantic.dev) | Validación de datos y esquemas |
| [Jinja2](https://jinja.palletsprojects.com) | Plantillas HTML del frontend |
| [HTMX](https://htmx.org) | Interactividad en el frontend sin JavaScript pesado |
| [Anthropic Claude](https://www.anthropic.com) | Modelo de IA para el agente de chat |

---

## Mejoras futuras (roadmap)

Lo que sigue después de tener la app funcionando con la colección completa. Están ordenadas de mayor a menor prioridad práctica.

---

### 1. Estado y seguimiento por partitura

**Qué es:** Agregar un campo de "estado" a cada partitura para saber en qué punto estás con ella.

**Estados posibles:**
- `pendiente` — la tienes pero aún no la has trabajado
- `en_progreso` — la estás estudiando o ensayando actualmente
- `dominada` — ya la tienes lista
- `archivada` — ya no la usas activamente

**Cómo se implementa:**
- Agregar columna `estado` a la tabla `piezas` en `app/models.py`
- Agregar filtro por estado en la barra lateral de `index.html`
- Agregar selector de estado en el formulario de detalle `detail.html`
- Agregar herramienta al agente: "¿Qué estoy estudiando actualmente?"

**Archivos a modificar:** `app/models.py`, `app/schemas.py`, `app/crud.py`, `frontend/templates/index.html`, `frontend/templates/detail.html`, `app/agent.py`

---

### 2. Historial de chat persistente

**Qué es:** Ahora el chat olvida todo al cerrar o recargar el navegador. Con esta mejora el historial se guarda en la base de datos y puedes retomar conversaciones anteriores.

**Cómo se implementa:**
- Crear tabla `conversaciones` en la BD con columnas: `id`, `created_at`, `messages` (JSON)
- Guardar cada conversación al cerrar el panel de chat
- Mostrar las últimas N conversaciones en un menú desplegable dentro del panel
- El agente recibe el historial guardado como contexto inicial

**Archivos a modificar:** `app/models.py`, `app/routers/chat.py`, `frontend/static/chat.js`, `frontend/templates/base.html`

---

### 3. Exportar el catálogo a CSV

**Qué es:** Un botón para descargar todo el catálogo (o los resultados de un filtro) como archivo CSV, útil para respaldos o para abrir en Excel/Numbers.

**Cómo se implementa:**
- Agregar endpoint `GET /api/piezas/exportar.csv` que devuelva un `StreamingResponse` con el CSV generado dinámicamente
- Incluir columnas: título, compositor, instrumentos, género, dificultad, notas, ubicaciones, rutas
- Agregar botón "Exportar CSV" en la barra superior de `index.html`
- Opcionalmente: exportar solo los resultados del filtro activo (pasar los mismos parámetros de filtro al endpoint)

**Archivos a modificar:** `app/routers/catalog.py`, `frontend/templates/index.html`

---

### 4. Metadatos extendidos desde MuseScore

**Qué es:** El CSV de inventario ya tiene datos ricos (tempo, número de compases, tonalidad, número de instrumentos) que actualmente no se muestran en la app. Esta mejora los muestra en la pantalla de detalle.

**Columnas del CSV disponibles:** `tempo_bpm`, `n_compases`, `tonalidad`, `n_instrumentos`, `tiene_acordes`, `servicio`

**Cómo se implementa:**
- Agregar columnas opcionales a la tabla `piezas`: `tempo_bpm`, `n_compases`, `tonalidad`
- Actualizar `csv_import.py` para leer y guardar esos campos
- Mostrarlos como datos secundarios en `detail.html` (debajo de los metadatos principales)
- Agregar herramientas al agente: "¿Qué tengo con más de 100 compases?" o "¿Qué está en Do mayor?"

**Archivos a modificar:** `app/models.py`, `app/schemas.py`, `app/csv_import.py`, `frontend/templates/detail.html`, `app/agent.py`

---

### 5. Autocompletado en búsqueda y filtros

**Qué es:** Al escribir en la barra de búsqueda o en los campos de compositor/instrumento, que aparezcan sugerencias basadas en lo que ya está en el catálogo.

**Cómo se implementa:**
- Agregar endpoint `GET /api/piezas/sugerencias?q=&campo=titulo` que devuelva hasta 10 coincidencias parciales
- Usar el elemento HTML nativo `<datalist>` conectado al input de búsqueda (no requiere JavaScript extra)
- Para compositores e instrumentos, los dropdowns actuales ya se pueblan desde la BD — se pueden convertir en inputs con autocompletado

**Archivos a modificar:** `app/routers/catalog.py`, `frontend/templates/index.html`, `frontend/templates/add.html`

---

### 6. Modo oscuro

**Qué es:** Un interruptor para cambiar entre tema claro y oscuro, guardando la preferencia del usuario.

**Cómo se implementa:**
- Agregar variables CSS para los colores en `style.css` bajo `[data-theme="dark"]`
- Agregar botón de toggle en el header de `base.html`
- Guardar la preferencia en `localStorage` del navegador con unas pocas líneas de JavaScript
- La preferencia se aplica automáticamente al cargar la página

**Archivos a modificar:** `frontend/static/style.css`, `frontend/templates/base.html`

---

### 7. Visor de PDF integrado

**Qué es:** Al hacer clic en una partitura que está guardada en el Mac o iCloud, abrirla directamente dentro de la app sin salir al navegador ni al Finder.

**Cómo se implementa:**
- Agregar endpoint `GET /api/archivos/{id}/ver` que sirva el archivo con el `Content-Type` correcto
- Usar el elemento HTML `<iframe>` o `<embed>` en `detail.html` para mostrar el PDF
- Aplica solo a archivos con `location_type="mac"` o `location_type="icloud"` y `format="pdf"`
- Para archivos MuseScore (`.mscz`), mostrar un enlace a "Abrir en MuseScore" en lugar del visor

**Archivos a modificar:** `app/routers/catalog.py`, `frontend/templates/detail.html`

---

### 8. Notificaciones cuando el agente no encuentra algo

**Qué es:** Si preguntas al chat "¿Tengo la Sinfonía nº 5 de Beethoven?" y no está en el catálogo, que el agente te ofrezca agregarla al instante desde la misma conversación.

**Cómo se implementa:**
- Agregar una herramienta al agente: `crear_pieza(titulo, compositor, notas)` que llame a `crud.create_pieza`
- El agente puede proponer crear la entrada y esperar confirmación del usuario antes de ejecutar
- Mostrar en el chat un botón "Sí, agrégala" que confirme la operación

**Archivos a modificar:** `app/agent.py`, `frontend/static/chat.js`

---

## Licencia

Proyecto personal — uso libre.
