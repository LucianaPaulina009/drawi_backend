from uuid import UUID

from sqlalchemy import Index
from sqlmodel import Field

from app.shared.infrastructure.db.base_model import BaseModel


class EstructuraRelacionNmModel(BaseModel, table=True):
    __tablename__ = "estructuras_relacion_nm"
    __table_args__ = (
        Index("ix_estructuras_nm_diagrama", "id_diagrama"),
        Index("ix_estructuras_nm_intermedia", "id_clase_intermedia"),
    )

    id_diagrama: UUID = Field(foreign_key="diagramas.id", nullable=False)
    id_clase_origen: UUID = Field(foreign_key="clases.id", nullable=False)
    id_clase_destino: UUID = Field(foreign_key="clases.id", nullable=False)
    id_clase_intermedia: UUID = Field(foreign_key="clases.id", nullable=False)
    id_relacion_origen: UUID = Field(foreign_key="relaciones.id", nullable=False)
    id_relacion_destino: UUID = Field(foreign_key="relaciones.id", nullable=False)

