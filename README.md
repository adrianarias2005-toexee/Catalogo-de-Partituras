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

## Licencia

Proyecto personal — uso libre.
