from __future__ import annotations

from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, Field


# ── Payload de Frames Entrantes (Cliente -> Servidor) ─────────────────────────

class MoverCursorPayload(BaseModel):
    x: float
    y: float


class BloqueoClasePayload(BaseModel):
    idClase: str = Field(alias="idClase")

    model_config = {"populate_by_name": True}


class DragClasePreviewPayload(BaseModel):
    idClase: str = Field(alias="idClase")
    posicionX: float = Field(alias="posicionX")
    posicionY: float = Field(alias="posicionY")

    model_config = {"populate_by_name": True}


class FrameEntranteWS(BaseModel):
    tipo: Literal[
        "MOVER_CURSOR",
        "SOLICITAR_BLOQUEO_CLASE",
        "RENOVAR_BLOQUEO_CLASE",
        "LIBERAR_BLOQUEO_CLASE",
        "ARRASTRAR_CLASE_PREVIEW",
        "PING",
    ]
    payload: dict[str, Any] | None = None


# ── Payload de Frames Salientes (Servidor -> Cliente) ─────────────────────────

class ParticipanteWS(BaseModel):
    idUsuario: str
    nombreUsuario: str
    color: str
    rol: str
    puedeEditar: bool


class BloqueoWS(BaseModel):
    idClase: str
    idUsuario: str
    nombreUsuario: str
    expiraEn: int


class SalaUnidaPayload(BaseModel):
    diagramaId: str
    miUsuarioId: str
    miRol: str
    puedeEditar: bool
    participantes: list[ParticipanteWS]
    bloqueos: list[BloqueoWS]


class CursorActualizadoPayload(BaseModel):
    idUsuario: str
    nombreUsuario: str
    color: str
    x: float
    y: float
    actualizadoEn: int


class DragClaseActualizadoPayload(BaseModel):
    idClase: str
    idUsuario: str
    posicionX: float
    posicionY: float


class BloqueoConcedidoPayload(BaseModel):
    idClase: str
    idUsuario: str
    nombreUsuario: str
    expiraEn: int


class BloqueoDenegadoPayload(BaseModel):
    idClase: str
    bloqueadoPor: str
    mensaje: str


class BloqueoLiberadoPayload(BaseModel):
    idClase: str


class MutacionConfirmadaPayload(BaseModel):
    diagramaId: str
    actionId: str
    tipoOperacion: str
    emisorId: str
    efectos: dict[str, Any]


class ParticipanteDesconectadoPayload(BaseModel):
    idUsuario: str
