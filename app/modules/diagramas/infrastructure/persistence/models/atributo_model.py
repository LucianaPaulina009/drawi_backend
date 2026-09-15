from uuid import UUID
from sqlalchemy import Index, text
from sqlmodel import Field
from app.shared.infrastructure.db.base_model import BaseModel


class AtributoModel(BaseModel, table=True):
    __tablename__ = "atributos"
    __table_args__ = (Index("ix_atributos_id_clase", "id_clase"), Index("uq_atributos_clase_orden_activo", "id_clase", "orden_de_posicion", unique=True, sqlite_where=text("fecha_eliminacion IS NULL"), postgresql_where=text("fecha_eliminacion IS NULL")))
    id_clase: UUID = Field(foreign_key="clases.id", nullable=False)
    tipo_dato: str = Field(nullable=False)
    nombre: str = Field(nullable=False)
    longitud: int | None = Field(default=None, nullable=True)
    precision: int | None = Field(default=None, nullable=True)
    escala: int | None = Field(default=None, nullable=True)
    es_llave_primaria: bool = Field(default=False, nullable=False)
    permite_nulo: bool = Field(default=True, nullable=False)
    es_unico: bool = Field(default=False, nullable=False)
    valor_por_defecto: str | None = Field(default=None, nullable=True)
    orden_de_posicion: int = Field(nullable=False)
