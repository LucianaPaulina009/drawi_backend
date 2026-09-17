from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.modules.diagramas.domain.exceptions import (
    ActualizacionRelacionVaciaException,
)
from app.modules.diagramas.infrastructure.api.schemas.referencia_fk_schemas import (
    ReferenciaFKRead,
)


class AtributoFkNuevoRequest(BaseModel):
    id_atributo: UUID
    nombre: str
    tipo_dato: str
    longitud: int | None = None
    precision: int | None = None
    escala: int | None = None
    permite_nulo: bool = True
    es_unico: bool = False
    valor_por_defecto: str | None = None


class MaterializacionFKRequest(BaseModel):
    id_referencia_fk: UUID
    id_atributo_referenciado: UUID
    id_atributo_fk: UUID | None = None
    id_clase_fk: UUID | None = None
    atributo_fk_nuevo: AtributoFkNuevoRequest | None = None
    on_delete: str = "NO_ACTION"
    on_update: str = "NO_ACTION"

    @model_validator(mode="after")
    def validar_atributo_fk(self) -> "MaterializacionFKRequest":
        if (self.id_atributo_fk is None) == (self.atributo_fk_nuevo is None):
            raise ValueError("Debe indicar exactamente un atributo FK existente o uno nuevo.")
        if self.atributo_fk_nuevo is not None and self.id_clase_fk is None:
            raise ValueError("Un atributo FK nuevo requiere indicar la clase receptora.")
        return self


class CrearRelacionRequest(BaseModel):
    id_relacion: UUID
    id_clase_origen: UUID
    id_clase_destino: UUID
    tipo_relacion: str
    cardinalidad_origen: str
    cardinalidad_destino: str
    conector_origen: str
    conector_destino: str
    materializacion_fk: list[MaterializacionFKRequest] = Field(default_factory=list)


class ActualizarRelacionRequest(BaseModel):
    id_clase_origen: UUID | None = None
    id_clase_destino: UUID | None = None
    tipo_relacion: str | None = None
    cardinalidad_origen: str | None = None
    cardinalidad_destino: str | None = None
    conector_origen: str | None = None
    conector_destino: str | None = None
    materializacion_fk: list[MaterializacionFKRequest] | None = None

    @model_validator(mode="after")
    def validar_campos(self) -> ActualizarRelacionRequest:
        if all(
            valor is None
            for valor in (
                self.id_clase_origen,
                self.id_clase_destino,
                self.tipo_relacion,
                self.cardinalidad_origen,
                self.cardinalidad_destino,
                self.conector_origen,
                self.conector_destino,
                self.materializacion_fk,
            )
        ):
            raise ActualizacionRelacionVaciaException()
        return self


class RelacionRead(BaseModel):
    id: UUID
    id_diagrama: UUID
    id_clase_origen: UUID
    id_clase_destino: UUID
    tipo_relacion: str
    cardinalidad_origen: str
    cardinalidad_destino: str
    conector_origen: str
    conector_destino: str


class RelacionDetalleRead(RelacionRead):
    referencias_fk: list[ReferenciaFKRead] = Field(default_factory=list)


class ListaRelacionesRead(BaseModel):
    items: list[RelacionDetalleRead] = Field(default_factory=list)
