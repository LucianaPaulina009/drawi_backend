from __future__ import annotations

from uuid import UUID
from pydantic import BaseModel, Field


class AtributoRequest(BaseModel):
    id_atributo: UUID | None = None
    tipo_dato: str
    nombre: str
    longitud: int | None = None
    precision: int | None = None
    escala: int | None = None
    es_llave_primaria: bool = False
    permite_nulo: bool = True
    es_unico: bool = False
    valor_por_defecto: str | None = None
    orden_de_posicion: int | None = Field(default=None, ge=1)


class ActualizarAtributoRequest(BaseModel):
    tipo_dato: str | None = None
    nombre: str | None = None
    longitud: int | None = None
    precision: int | None = None
    escala: int | None = None
    es_llave_primaria: bool | None = None
    permite_nulo: bool | None = None
    es_unico: bool | None = None
    valor_por_defecto: str | None = None
    orden_de_posicion: int | None = Field(default=None, ge=1)


class AtributoRead(BaseModel):
    id: UUID
    id_clase: UUID
    tipo_dato: str
    nombre: str
    longitud: int | None
    precision: int | None
    escala: int | None
    es_llave_primaria: bool
    permite_nulo: bool
    es_unico: bool
    valor_por_defecto: str | None
    orden_de_posicion: int


class ListaAtributosRead(BaseModel):
    items: list[AtributoRead]
