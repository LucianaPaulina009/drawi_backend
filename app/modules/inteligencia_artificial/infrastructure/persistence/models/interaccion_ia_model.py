from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index, JSON, text
from sqlmodel import Field

from app.shared.infrastructure.db.base_model import BaseModel


class InteraccionIaModel(BaseModel, table=True):
    """Modelo SQLModel para interacciones persistentes de IA."""

    __tablename__ = "interacciones_ia"
    __table_args__ = (
        Index("ix_interacciones_ia_id_usuario", "id_usuario"),
        Index("ix_interacciones_ia_id_diagrama", "id_diagrama"),
        Index("ix_interacciones_ia_id_diagrama_fecha_creacion", "id_diagrama", "fecha_creacion"),
        Index(
            "uq_interacciones_ia_usuario_diagrama_clave",
            "id_usuario",
            "id_diagrama",
            "clave_idempotencia",
            unique=True,
            sqlite_where=text("fecha_eliminacion IS NULL"),
            postgresql_where=text("fecha_eliminacion IS NULL"),
        ),
    )

    id_usuario: str = Field(nullable=False)
    id_diagrama: UUID = Field(foreign_key="diagramas.id", nullable=False)
    tipo_interaccion: str = Field(nullable=False, default="texto")
    entrada_usuario: str | None = Field(default=None, nullable=True)
    respuesta_ia: str | None = Field(default=None, nullable=True)
    url_imagen: str | None = Field(default=None, nullable=True)
    estado: str = Field(nullable=False, default="pendiente")
    clave_idempotencia: UUID = Field(nullable=False)
    modelo_utilizado: str | None = Field(default=None, nullable=True)
    detalle_ejecucion: Any = Field(default=None, sa_column=Column(JSON, nullable=True))
