from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.modules.diagramas.domain.exceptions import (
    ActualizacionClaseVaciaException,
    NombreClaseInvalidoException,
)
from app.modules.diagramas.infrastructure.api.schemas.atributo_schemas import AtributoRead


class CrearClaseRequest(BaseModel):
    id_clase: UUID | None = None
    id_atributo_inicial: UUID | None = None
    nombre: str = "Tabla"
    posicion_x: float
    posicion_y: float
    ancho: float = Field(default=280.0, gt=0)

    @model_validator(mode="after")
    def validar_nombre(self) -> CrearClaseRequest:
        if self.nombre is not None and not self.nombre.strip():
            raise NombreClaseInvalidoException()
        return self


class ActualizarClaseRequest(BaseModel):
    nombre: str | None = None
    posicion_x: float | None = None
    posicion_y: float | None = None
    ancho: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validar_campos(self) -> ActualizarClaseRequest:
        if all(
            valor is None
            for valor in (self.nombre, self.posicion_x, self.posicion_y, self.ancho)
        ):
            raise ActualizacionClaseVaciaException()
        if self.nombre is not None and not self.nombre.strip():
            raise NombreClaseInvalidoException()
        return self


class ClaseRead(BaseModel):
    id: UUID
    id_diagrama: UUID
    nombre: str
    posicion_x: float
    posicion_y: float
    ancho: float


class ClaseDetalleRead(ClaseRead):
    atributos: list[AtributoRead] = Field(default_factory=list)


class ListaClasesRead(BaseModel):
    items: list[ClaseRead]
