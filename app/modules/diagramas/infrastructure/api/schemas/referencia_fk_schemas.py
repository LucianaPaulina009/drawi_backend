from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.modules.diagramas.domain.exceptions import (
    ActualizacionReferenciaFKVaciaException,
)


class CrearReferenciaFKRequest(BaseModel):
    id_referencia_fk: UUID
    id_atributo_fk: UUID
    id_atributo_referenciado: UUID
    on_delete: str = "NO_ACTION"
    on_update: str = "NO_ACTION"


class ActualizarReferenciaFKRequest(BaseModel):
    id_atributo_fk: UUID | None = None
    id_atributo_referenciado: UUID | None = None
    on_delete: str | None = None
    on_update: str | None = None

    @model_validator(mode="after")
    def validar_campos(self) -> ActualizarReferenciaFKRequest:
        if all(
            valor is None
            for valor in (
                self.id_atributo_fk,
                self.id_atributo_referenciado,
                self.on_delete,
                self.on_update,
            )
        ):
            raise ActualizacionReferenciaFKVaciaException()
        return self


class ReferenciaFKRead(BaseModel):
    id: UUID
    id_relacion: UUID
    id_atributo_fk: UUID
    id_atributo_referenciado: UUID
    on_delete: str
    on_update: str


class ListaReferenciasFKRead(BaseModel):
    items: list[ReferenciaFKRead] = Field(default_factory=list)
