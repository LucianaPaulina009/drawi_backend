from uuid import UUID

from sqlalchemy import Column, Index, JSON
from sqlmodel import Field

from app.shared.infrastructure.db.base_model import BaseModel


class OperacionDiagramaModel(BaseModel, table=True):
    __tablename__ = "operaciones_diagrama"
    __table_args__ = (Index("uq_operaciones_diagrama_action", "action_id", unique=True),)

    action_id: UUID = Field(nullable=False)
    usuario_id: str = Field(nullable=False, index=True)
    id_diagrama: UUID = Field(foreign_key="diagramas.id", nullable=False, index=True)
    huella_payload: str = Field(nullable=False)
    estado: str = Field(nullable=False, default="confirmada")
    respuesta: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))

