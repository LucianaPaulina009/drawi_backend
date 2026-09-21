"""crear tabla interacciones ia

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-09-20 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, Sequence[str], None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "interacciones_ia",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_eliminacion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id_usuario", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("id_diagrama", sa.Uuid(), nullable=False),
        sa.Column("tipo_interaccion", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("entrada_usuario", sa.Text(), nullable=True),
        sa.Column("respuesta_ia", sa.Text(), nullable=True),
        sa.Column("url_imagen", sa.Text(), nullable=True),
        sa.Column("estado", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("clave_idempotencia", sa.Uuid(), nullable=False),
        sa.Column("modelo_utilizado", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("detalle_ejecucion", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["id_diagrama"], ["diagramas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_interacciones_ia_id_usuario"),
        "interacciones_ia",
        ["id_usuario"],
        unique=False,
    )
    op.create_index(
        op.f("ix_interacciones_ia_id_diagrama"),
        "interacciones_ia",
        ["id_diagrama"],
        unique=False,
    )
    op.create_index(
        op.f("ix_interacciones_ia_id_diagrama_fecha_creacion"),
        "interacciones_ia",
        ["id_diagrama", "fecha_creacion"],
        unique=False,
    )
    op.create_index(
        "uq_interacciones_ia_usuario_diagrama_clave",
        "interacciones_ia",
        ["id_usuario", "id_diagrama", "clave_idempotencia"],
        unique=True,
        sqlite_where=sa.text("fecha_eliminacion IS NULL"),
        postgresql_where=sa.text("fecha_eliminacion IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_interacciones_ia_usuario_diagrama_clave", table_name="interacciones_ia")
    op.drop_index(op.f("ix_interacciones_ia_id_diagrama_fecha_creacion"), table_name="interacciones_ia")
    op.drop_index(op.f("ix_interacciones_ia_id_diagrama"), table_name="interacciones_ia")
    op.drop_index(op.f("ix_interacciones_ia_id_usuario"), table_name="interacciones_ia")
    op.drop_table("interacciones_ia")
