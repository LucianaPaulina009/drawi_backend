from __future__ import annotations

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class EnviarMensajeIaRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    texto: str = Field(..., min_length=1, max_length=2000, description="Mensaje para el asistente IA.")
    clave_idempotencia: UUID = Field(..., alias="claveIdempotencia", description="UUID de idempotencia del envío.")
    tipo_interaccion: str | None = Field(default="texto", alias="tipoInteraccion", description="Tipo de interacción ('texto', 'audio').")


class InteraccionIaRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    id_diagrama: UUID = Field(..., alias="idDiagrama")
    id_usuario: str = Field(..., alias="idUsuario")
    tipo_interaccion: str = Field(..., alias="tipoInteraccion")
    entrada_usuario: str | None = Field(default=None, alias="entradaUsuario")
    respuesta_ia: str | None = Field(default=None, alias="respuestaIa")
    url_imagen: str | None = Field(default=None, alias="urlImagen")
    estado: str
    creado_en: datetime | None = Field(default=None, alias="creadoEn")


class ListaInteraccionesIaRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[InteraccionIaRead]
    siguiente_cursor: UUID | None = Field(default=None, alias="siguienteCursor")
