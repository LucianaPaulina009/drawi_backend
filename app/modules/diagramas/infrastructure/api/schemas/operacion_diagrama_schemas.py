from __future__ import annotations

from uuid import UUID
from typing import Any
from pydantic import BaseModel, Field


class OperacionDiagramaRequest(BaseModel):
    tipo: str = Field(..., description="Tipo de operación discriminada del catálogo")
    datos: dict[str, Any] = Field(default_factory=dict, description="Datos de la operación")


class AtributoEfectoRead(BaseModel):
    id: UUID
    id_clase: UUID
    nombre: str
    tipo_dato: str
    longitud: int | None = None
    precision: int | None = None
    escala: int | None = None
    permite_nulo: bool = True
    es_unico: bool = False
    valor_por_defecto: str | None = None
    orden_de_posicion: int
    es_llave_primaria: bool = False
    procedencia: str = "manual"


class ClaseEfectoRead(BaseModel):
    id: UUID
    id_diagrama: UUID
    nombre: str
    posicion_x: float
    posicion_y: float
    ancho: float
    atributos: list[AtributoEfectoRead] = Field(default_factory=list)


class ReferenciaFKEfectoRead(BaseModel):
    id: UUID
    id_relacion: UUID
    id_atributo_fk: UUID
    id_atributo_referenciado: UUID
    on_delete: str = "NO_ACTION"
    on_update: str = "NO_ACTION"


class RelacionEfectoRead(BaseModel):
    id: UUID
    id_diagrama: UUID
    id_clase_origen: UUID
    id_clase_destino: UUID
    tipo_relacion: str
    cardinalidad_origen: str
    cardinalidad_destino: str
    conector_origen: str
    conector_destino: str
    nombre: str | None = None
    referencias_fk: list[ReferenciaFKEfectoRead] = Field(default_factory=list)


class EstructuraNmEfectoRead(BaseModel):
    id: UUID
    id_diagrama: UUID
    id_clase_origen: UUID
    id_clase_destino: UUID
    id_clase_intermedia: UUID
    id_relacion_origen: UUID
    id_relacion_destino: UUID


class EfectosOperacionRead(BaseModel):
    clases_actualizadas: list[ClaseEfectoRead] = Field(default_factory=list)
    clases_eliminadas: list[UUID] = Field(default_factory=list)
    relaciones_actualizadas: list[RelacionEfectoRead] = Field(default_factory=list)
    relaciones_eliminadas: list[UUID] = Field(default_factory=list)
    estructuras_nm_actualizadas: list[EstructuraNmEfectoRead] = Field(default_factory=list)
    estructuras_nm_eliminadas: list[UUID] = Field(default_factory=list)


class OperacionDiagramaResponse(BaseModel):
    action_id: UUID
    id_diagrama: UUID
    tipo: str
    efectos: EfectosOperacionRead
