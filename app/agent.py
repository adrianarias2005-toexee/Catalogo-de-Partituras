# Agente de chat con herramientas para el catálogo de partituras
import json
from typing import Any

import anthropic
from sqlalchemy.orm import Session

from app import crud
from app.config import settings

# ---------------------------------------------------------------------------
# Prompt del sistema
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "Eres un asistente personal que ayuda a gestionar una colección de partituras musicales. "
    "Tienes acceso a herramientas para buscar y consultar el catálogo. "
    "Responde siempre en español. "
    "Usa las herramientas disponibles para encontrar información precisa sobre las partituras. "
    "Cuando el usuario te haga una pregunta sobre el catálogo, utiliza la herramienta más adecuada "
    "para obtener la información antes de responder."
)

# ---------------------------------------------------------------------------
# Funciones de herramientas (devuelven texto en español)
# ---------------------------------------------------------------------------

def _formatear_pieza(pieza) -> str:
    """Formatea una pieza como línea de lista con sus datos principales."""
    partes = [f"**{pieza.title}**"]
    if pieza.composer:
        partes.append(f"compositor: {pieza.composer}")
    if pieza.instruments:
        try:
            instrumentos = json.loads(pieza.instruments)
            if instrumentos:
                partes.append(f"instrumentos: {', '.join(instrumentos)}")
        except (ValueError, TypeError):
            pass
    if pieza.difficulty:
        partes.append(f"dificultad: {pieza.difficulty}")
    ubicaciones = [a.location_type for a in pieza.archivos]
    if ubicaciones:
        partes.append(f"ubicación: {', '.join(set(ubicaciones))}")
    return "• " + " — ".join(partes)


def tool_search_catalog(db: Session, query: str) -> str:
    """Busca partituras por título (insensible a acentos y mayúsculas)."""
    piezas = crud.search_piezas(db, query=query)
    if not piezas:
        return f"No encontré partituras que coincidan con '{query}'."
    lineas = [f"Encontré {len(piezas)} partitura(s) para '{query}':"]
    for pieza in piezas:
        lineas.append(_formatear_pieza(pieza))
    return "\n".join(lineas)


def tool_filter_by_composer(db: Session, composer: str) -> str:
    """Filtra partituras por compositor."""
    piezas = crud.list_piezas(db, composer=composer)
    if not piezas:
        return f"No encontré partituras del compositor '{composer}'."
    lineas = [f"Encontré {len(piezas)} partitura(s) del compositor '{composer}':"]
    for pieza in piezas:
        lineas.append(_formatear_pieza(pieza))
    return "\n".join(lineas)


def tool_filter_by_instrument(db: Session, instrument: str) -> str:
    """Filtra partituras por instrumento."""
    piezas = crud.list_piezas(db, instrument=instrument)
    if not piezas:
        return f"No encontré partituras para el instrumento '{instrument}'."
    lineas = [f"Encontré {len(piezas)} partitura(s) para '{instrument}':"]
    for pieza in piezas:
        lineas.append(_formatear_pieza(pieza))
    return "\n".join(lineas)


def tool_filter_by_location(db: Session, location_type: str) -> str:
    """Filtra partituras por tipo de ubicación (mac, icloud, ipad, celular, papel)."""
    piezas = crud.list_piezas(db, location_type=location_type)
    if not piezas:
        return f"No encontré partituras con ubicación '{location_type}'."
    lineas = [f"Encontré {len(piezas)} partitura(s) con ubicación '{location_type}':"]
    for pieza in piezas:
        lineas.append(_formatear_pieza(pieza))
    return "\n".join(lineas)


def tool_get_piece_detail(db: Session, pieza_id: int) -> str:
    """Obtiene el detalle completo de una pieza por su ID."""
    pieza = crud.get_pieza(db, pieza_id=pieza_id)
    if pieza is None:
        return f"No encontré ninguna partitura con el ID {pieza_id}."

    lineas = [f"**{pieza.title}** (ID: {pieza.id})"]
    if pieza.composer:
        lineas.append(f"  Compositor: {pieza.composer}")
    if pieza.instruments:
        try:
            instrumentos = json.loads(pieza.instruments)
            if instrumentos:
                lineas.append(f"  Instrumentos: {', '.join(instrumentos)}")
        except (ValueError, TypeError):
            pass
    if pieza.genre:
        lineas.append(f"  Género: {pieza.genre}")
    if pieza.difficulty:
        lineas.append(f"  Dificultad: {pieza.difficulty}")
    if pieza.notes:
        lineas.append(f"  Notas: {pieza.notes}")
    if pieza.archivos:
        lineas.append("  Archivos:")
        for archivo in pieza.archivos:
            info = f"    • Formato: {archivo.format} — Ubicación: {archivo.location_type}"
            if archivo.path:
                info += f" — Ruta: {archivo.path}"
            lineas.append(info)
    else:
        lineas.append("  Sin archivos registrados.")
    return "\n".join(lineas)


# ---------------------------------------------------------------------------
# Definición de herramientas para la API de Anthropic
# ---------------------------------------------------------------------------

TOOLS: list[dict[str, Any]] = [
    {
        "name": "search_catalog",
        "description": (
            "Busca partituras musicales por título o palabra clave en el catálogo. "
            "La búsqueda es insensible a acentos y mayúsculas."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Término de búsqueda (título o parte del título de la partitura)",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "filter_by_composer",
        "description": "Filtra el catálogo de partituras por nombre del compositor.",
        "input_schema": {
            "type": "object",
            "properties": {
                "composer": {
                    "type": "string",
                    "description": "Nombre del compositor (puede ser parcial)",
                }
            },
            "required": ["composer"],
        },
    },
    {
        "name": "filter_by_instrument",
        "description": "Filtra el catálogo de partituras por instrumento musical.",
        "input_schema": {
            "type": "object",
            "properties": {
                "instrument": {
                    "type": "string",
                    "description": "Nombre del instrumento (p.ej. 'Flauta', 'Piano', 'Violín')",
                }
            },
            "required": ["instrument"],
        },
    },
    {
        "name": "filter_by_location",
        "description": (
            "Filtra las partituras según el tipo de ubicación donde están almacenadas. "
            "Tipos válidos: mac, icloud, ipad, celular, papel."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "location_type": {
                    "type": "string",
                    "description": "Tipo de ubicación: mac, icloud, ipad, celular o papel",
                    "enum": ["mac", "icloud", "ipad", "celular", "papel"],
                }
            },
            "required": ["location_type"],
        },
    },
    {
        "name": "get_piece_detail",
        "description": "Obtiene todos los detalles de una partitura específica por su ID numérico.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pieza_id": {
                    "type": "integer",
                    "description": "ID numérico de la partitura en el catálogo",
                }
            },
            "required": ["pieza_id"],
        },
    },
]


# ---------------------------------------------------------------------------
# Despachador de herramientas
# ---------------------------------------------------------------------------

def _ejecutar_herramienta(db: Session, nombre: str, argumentos: dict) -> str:
    """Ejecuta la herramienta indicada y devuelve el resultado como texto."""
    if nombre == "search_catalog":
        return tool_search_catalog(db, query=argumentos["query"])
    elif nombre == "filter_by_composer":
        return tool_filter_by_composer(db, composer=argumentos["composer"])
    elif nombre == "filter_by_instrument":
        return tool_filter_by_instrument(db, instrument=argumentos["instrument"])
    elif nombre == "filter_by_location":
        return tool_filter_by_location(db, location_type=argumentos["location_type"])
    elif nombre == "get_piece_detail":
        return tool_get_piece_detail(db, pieza_id=int(argumentos["pieza_id"]))
    else:
        return f"Herramienta desconocida: {nombre}"


# ---------------------------------------------------------------------------
# Función principal del agente
# ---------------------------------------------------------------------------

def run_agent(db: Session, messages: list[dict]) -> str:
    """
    Ejecuta el agente de chat con historial de conversación.

    Recibe el historial completo de mensajes (role: user/assistant),
    llama a la API de Anthropic con las herramientas disponibles y
    maneja el ciclo de tool_use hasta obtener una respuesta final.

    Returns:
        Texto de la respuesta final del asistente.
    Raises:
        ValueError: Si la clave de API de Anthropic no está configurada.
    """
    if not settings.anthropic_api_key:
        raise ValueError(
            "La clave de API de Anthropic no está configurada. "
            "Establece ANTHROPIC_API_KEY en las variables de entorno."
        )

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    conversacion = list(messages)

    while True:
        respuesta = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=conversacion,
        )

        # Si Claude terminó sin llamar herramientas → devolver texto final
        if respuesta.stop_reason == "end_turn":
            textos = [
                bloque.text
                for bloque in respuesta.content
                if bloque.type == "text"
            ]
            return "\n".join(textos)

        # Si Claude quiere usar herramientas → ejecutarlas y continuar
        if respuesta.stop_reason == "tool_use":
            # Añadir la respuesta del asistente (con bloques tool_use) al historial
            conversacion.append({
                "role": "assistant",
                "content": respuesta.content,
            })

            # Ejecutar todas las herramientas solicitadas y recopilar resultados
            resultados_herramientas = []
            for bloque in respuesta.content:
                if bloque.type == "tool_use":
                    resultado = _ejecutar_herramienta(db, bloque.name, bloque.input)
                    resultados_herramientas.append({
                        "type": "tool_result",
                        "tool_use_id": bloque.id,
                        "content": resultado,
                    })

            # Añadir los resultados al historial y continuar el bucle
            conversacion.append({
                "role": "user",
                "content": resultados_herramientas,
            })
            continue

        # Cualquier otro stop_reason: devolver el texto disponible
        textos = [
            bloque.text
            for bloque in respuesta.content
            if bloque.type == "text"
        ]
        return "\n".join(textos) if textos else "No se pudo generar una respuesta."
