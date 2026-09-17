from __future__ import annotations

import uuid
from sqlalchemy import UniqueConstraint
from sqlmodel import Field

from app.shared.infrastructure.db.base_model import BaseModel


class ColaboradorProyectoModel(BaseModel, table=True):
    """Modelo SQLModel de la tabla colaboradores_proyecto."""

    __tablename__ = "colaboradores_proyecto"
    __table_args__ = (
        UniqueConstraint("id_proyecto", "id_usuario", name="uq_colaboradores_proyecto_usuario"),
    )

    id_proyecto: uuid.UUID = Field(foreign_key="proyectos.id", index=True, nullable=False)
    id_usuario: str = Field(foreign_key="user.id", index=True, nullable=False)
    rol: str = Field(default="ver", nullable=False)
    estado: str = Field(default="activo", nullable=False)
