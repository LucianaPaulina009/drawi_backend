from __future__ import annotations

from uuid import UUID

from app.modules.diagramas.domain.exceptions import (
    ActualizacionDiagramaVaciaException,
    NombreDiagramaInvalidoException,
)
from app.modules.diagramas.infrastructure.api.schemas.atributo_schemas import AtributoRead
from pydantic import BaseModel, Field, model_validator


class CrearDiagramaRequest(BaseModel):
    nombre: str | None = Field(default=None, description="Nombre opcional de la página.")

    @model_validator(mode="after")
    def validar_nombre(self) -> CrearDiagramaRequest:
        if self.nombre is not None and not self.nombre.strip():
            raise NombreDiagramaInvalidoException()
        return self


class ActualizarDiagramaRequest(BaseModel):
    nombre: str | None = Field(default=None, description="Nuevo nombre de la página.")

    @model_validator(mode="after")
    def validar_campos(self) -> ActualizarDiagramaRequest:
        if self.nombre is None:
            raise ActualizacionDiagramaVaciaException()
        if not self.nombre.strip():
            raise NombreDiagramaInvalidoException()
        return self


class DiagramaRead(BaseModel):
    id: UUID
    id_proyecto: UUID
    nombre: str
    numero: int


class ListaDiagramasRead(BaseModel):
    items: list[DiagramaRead]


class ClaseEnDiagramaRead(BaseModel):
    id: UUID
    id_diagrama: UUID
    nombre: str
    posicion_x: float
    posicion_y: float
    ancho: float
    atributos: list[AtributoRead] = Field(default_factory=list)


class DiagramaDetalleRead(DiagramaRead):
    clases: list[ClaseEnDiagramaRead] = Field(default_factory=list)
