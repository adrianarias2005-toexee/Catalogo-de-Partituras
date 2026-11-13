# Router para el endpoint de chat con el agente de partituras
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import agent
from app.database import get_db

chat_router = APIRouter(prefix="/api", tags=["chat"])


# ---------------------------------------------------------------------------
# Esquemas de entrada y salida
# ---------------------------------------------------------------------------

class MensajeChat(BaseModel):
    role: str  # "user" o "assistant"
    content: str


class SolicitudChat(BaseModel):
    messages: list[MensajeChat]


class RespuestaChat(BaseModel):
    response: str


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@chat_router.post("/chat", response_model=RespuestaChat)
def chat(solicitud: SolicitudChat, db: Session = Depends(get_db)):
    """
    Endpoint de chat con el agente de partituras.

    Recibe el historial de mensajes y devuelve la respuesta del agente.
    """
    mensajes = [{"role": m.role, "content": m.content} for m in solicitud.messages]
    try:
        respuesta = agent.run_agent(db, mensajes)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return RespuestaChat(response=respuesta)
