# Historial de cambios

## [1.1.0] — 2026-11-16

### Añadido

- **Botón "Buscar nuevas"** en el encabezado del catálogo (`/`)
  - Escanea automáticamente las carpetas configuradas en `SCAN_FOLDERS` sin tener que ir a `/escanear`
  - Si no hay archivos nuevos muestra un banner verde: "Todo al día"
  - Si encuentra partituras nuevas muestra un banner amarillo con el conteo y un enlace directo a revisarlas e importarlas
- **Endpoint `GET /api/scan/nuevas`** en `app/routers/scanner.py`
  - Usa las carpetas de `settings.scan_folders` automáticamente
  - Filtra los archivos que ya están importados en la base de datos
  - Devuelve solo los candidatos realmente nuevos

### Archivos modificados

- `app/routers/scanner.py` — nuevo endpoint `/api/scan/nuevas`
- `frontend/templates/index.html` — botón "Buscar nuevas" y lógica JavaScript

---

## [1.0.0] — versión base

### Incluido en la versión inicial

- Catálogo centralizado con filtros por compositor, instrumento, dificultad y ubicación
- Búsqueda por título insensible a acentos
- Escáner automático de carpetas con revisión previa antes de importar
- Importación desde CSV
- Formulario para agregar partituras manualmente
- Agente de chat con IA (requiere API key de Anthropic)
- Acceso desde cualquier dispositivo en la misma red WiFi
