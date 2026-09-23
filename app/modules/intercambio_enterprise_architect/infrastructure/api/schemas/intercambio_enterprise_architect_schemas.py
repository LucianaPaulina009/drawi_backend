from __future__ import annotations

from uuid import UUID
from pydantic import BaseModel, Field


class ResultadoImportacionEaResponse(BaseModel):
    diagrama_id: UUID
    clases_importadas: int
    atributos_importados: int
    relaciones_importadas: int
    estructuras_nm_importadas: int
    advertencias: list[str] = Field(default_factory=list)
