from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class AtributoReconocidoIa(BaseModel):
    """Atributo o campo reconocido dentro de una clase UML."""

    nombre: str = Field(..., description="Nombre del atributo")
    tipo_detectado: str = Field(
        default="varchar",
        description="Tipo de dato SQL/UML detectado (ej: varchar, integer, boolean, date, timestamp, decimal)",
    )
    es_pk: bool = Field(default=False, description="Indica si es llave primaria")
    es_fk: bool = Field(default=False, description="Indica si es llave foránea")
    fk_destino_ref: Optional[str] = Field(
        default=None,
        description="Referencia semántica o nombre de la clase referenciada por esta FK si es visible o deducible",
    )
    permite_nulo: bool = Field(default=False, description="Indica si admite valores nulos")
    confianza: float = Field(default=1.0, ge=0.0, le=1.0, description="Nivel de confianza en la detección")


class ClaseReconocidaIa(BaseModel):
    """Clase o entidad reconocida dentro del diagrama UML."""

    referencia_semantica: str = Field(
        ...,
        description="Identificador simbólico temporal de la clase (ej: ref_usuario, ref_pedido)",
    )
    nombre: str = Field(..., description="Nombre de la clase o entidad")
    atributos: List[AtributoReconocidoIa] = Field(
        default_factory=list, description="Lista de atributos detectados para la clase"
    )
    posicion_relativa_x: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Posición X relativa aproximada en la imagen [0.0 a 1.0]",
    )
    posicion_relativa_y: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Posición Y relativa aproximada en la imagen [0.0 a 1.0]",
    )


class RelacionReconocidaIa(BaseModel):
    """Relación reconocida entre dos clases del diagrama UML."""

    origen_ref: str = Field(
        ...,
        description="Referencia semántica o nombre de la clase origen",
    )
    destino_ref: str = Field(
        ...,
        description="Referencia semántica o nombre de la clase destino",
    )
    tipo: str = Field(
        default="asociacion",
        description="Tipo de relación: asociacion, asociacion_dirigida, agregacion, composicion, herencia, realizacion, dependencia",
    )
    cardinalidad_origen: str = Field(
        default="1",
        description="Cardinalidad en el extremo origen (ej: '1', '0..1', '0..*', '1..*')",
    )
    cardinalidad_destino: str = Field(
        default="1",
        description="Cardinalidad en el extremo destino (ej: '1', '0..1', '0..*', '1..*')",
    )
    nombre: Optional[str] = Field(
        default=None,
        description="Nombre o verbo de la relación si es visible en la imagen",
    )
    es_nm: bool = Field(
        default=False,
        description="Indica si representa una estructura N:M con cardinalidades * a *",
    )
    es_recursiva: bool = Field(
        default=False,
        description="Indica si es una autorreferencia sobre la misma clase",
    )


class DiagramaReconocidoIa(BaseModel):
    """Estructura normalizada y tipada del diagrama UML reconocido desde una imagen."""

    clases: List[ClaseReconocidaIa] = Field(
        default_factory=list, description="Lista de clases reconocidas en el diagrama"
    )
    relaciones: List[RelacionReconocidaIa] = Field(
        default_factory=list, description="Lista de relaciones reconocidas en el diagrama"
    )
    advertencias: List[str] = Field(
        default_factory=list, description="Advertencias u omisiones de partes ilegibles o ambiguas"
    )
