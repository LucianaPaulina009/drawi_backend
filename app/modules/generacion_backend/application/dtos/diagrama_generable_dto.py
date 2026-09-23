from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AtributoGenerable:
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
    procedencia: str


@dataclass(frozen=True, slots=True)
class ClaseGenerable:
    id: UUID
    id_diagrama: UUID
    nombre: str
    posicion_x: float
    posicion_y: float
    ancho: float
    atributos: tuple[AtributoGenerable, ...] = ()


@dataclass(frozen=True, slots=True)
class ReferenciaFKGenerable:
    id: UUID
    id_relacion: UUID
    id_atributo_fk: UUID
    id_atributo_referenciado: UUID
    on_delete: str
    on_update: str


@dataclass(frozen=True, slots=True)
class RelacionGenerable:
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
    referencias_fk: tuple[ReferenciaFKGenerable, ...] = ()


@dataclass(frozen=True, slots=True)
class EstructuraRelacionNmGenerable:
    id: UUID
    id_diagrama: UUID
    id_clase_origen: UUID
    id_clase_destino: UUID
    id_clase_intermedia: UUID
    id_relacion_origen: UUID
    id_relacion_destino: UUID


@dataclass(frozen=True, slots=True)
class DiagramaGenerable:
    id: UUID
    id_proyecto: UUID
    nombre: str
    numero: int
    clases: tuple[ClaseGenerable, ...] = ()
    relaciones: tuple[RelacionGenerable, ...] = ()
    estructuras_nm: tuple[EstructuraRelacionNmGenerable, ...] = ()
