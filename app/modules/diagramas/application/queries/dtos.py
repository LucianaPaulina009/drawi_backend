from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AtributoDTO:
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


@dataclass(frozen=True, slots=True)
class ClaseDTO:
    id: UUID
    id_diagrama: UUID
    nombre: str
    posicion_x: float
    posicion_y: float
    ancho: float


@dataclass(frozen=True, slots=True)
class ClaseDetalleDTO(ClaseDTO):
    atributos: tuple[AtributoDTO, ...]


@dataclass(frozen=True, slots=True)
class DiagramaDTO:
    id: UUID
    id_proyecto: UUID
    nombre: str
    numero: int


@dataclass(frozen=True, slots=True)
class DiagramaDetalleDTO(DiagramaDTO):
    clases: tuple[ClaseDetalleDTO, ...]
