from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(slots=True)
class CampoSpring:
    id: UUID
    nombre_java: str
    nombre_getter: str
    nombre_setter: str
    nombre_sql: str
    tipo_java: str
    tipo_sql: str
    es_pk: bool
    permite_nulo: bool
    es_unico: bool
    valor_por_defecto: str | None
    longitud: int | None
    precision: int | None
    escala: int | None


@dataclass(slots=True)
class AsociacionSpring:
    tipo: str  # "MANY_TO_ONE" | "ONE_TO_MANY" | "ONE_TO_ONE" | "MANY_TO_MANY"
    nombre_campo: str
    nombre_getter: str
    nombre_setter: str
    entidad_destino: str
    columna_fk_sql: str | None = None
    campo_mapeado: str | None = None


@dataclass(slots=True)
class EntidadSpring:
    id: UUID
    nombre_clase: str
    nombre_camel: str
    nombre_tabla: str
    endpoint_path: str
    campos: list[CampoSpring]
    pk: CampoSpring
    asociaciones: list[AsociacionSpring] = field(default_factory=list)
    necesita_bigdecimal: bool = False
    necesita_localdate: bool = False
    necesita_localdatetime: bool = False
    necesita_uuid: bool = False


@dataclass(slots=True)
class ProyectoSpring:
    nombre_proyecto: str
    slug: str
    package_name: str
    package_path: str
    version_plantilla: str
    java_version: str
    spring_boot_version: str
    entidades: list[EntidadSpring] = field(default_factory=list)
