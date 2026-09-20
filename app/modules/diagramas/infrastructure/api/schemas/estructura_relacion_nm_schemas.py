from uuid import UUID

from pydantic import BaseModel, Field


class CrearEstructuraRelacionNmRequest(BaseModel):
    id_estructura: UUID
    id_clase_origen: UUID
    id_clase_destino: UUID
    id_clase_intermedia: UUID
    id_atributo_inicial: UUID
    id_atributo_fk_origen: UUID
    id_atributo_fk_destino: UUID
    id_relacion_origen: UUID
    id_relacion_destino: UUID
    id_referencia_fk_origen: UUID
    id_referencia_fk_destino: UUID
    id_atributo_referenciado_origen: UUID
    id_atributo_referenciado_destino: UUID
    nombre_intermedia: str = Field(min_length=1)
    posicion_x: float
    posicion_y: float
    ancho: float = Field(default=280.0, gt=0)


class EstructuraRelacionNmRead(BaseModel):
    id: UUID
    id_clase_intermedia: UUID
    id_relacion_origen: UUID
    id_relacion_destino: UUID

