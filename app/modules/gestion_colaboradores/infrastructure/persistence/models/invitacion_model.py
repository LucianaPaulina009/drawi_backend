from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import DateTime, UniqueConstraint
from sqlmodel import Field

from app.shared.infrastructure.db.base_model import BaseModel


class InvitacionModel(BaseModel, table=True):
    """Modelo SQLModel de la tabla invitaciones."""

    __tablename__ = "invitaciones"
    __table_args__ = (
        UniqueConstraint("id_proyecto", name="uq_invitaciones_proyecto_id"),
        UniqueConstraint("codigo_acceso", name="uq_invitaciones_codigo_acceso"),
    )

    id_proyecto: uuid.UUID = Field(foreign_key="proyectos.id", index=True, nullable=False)
    codigo_acceso: str = Field(index=True, nullable=False)
    fecha_expiracion: datetime = Field(
        sa_type=DateTime(timezone=True),
        nullable=False,
    )
