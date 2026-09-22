from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TranscripcionIaResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    texto: str = Field(..., description="Texto reconocido de la grabación de voz.")
    idioma: str | None = Field(default=None, description="Código de idioma utilizado o detectado.")
