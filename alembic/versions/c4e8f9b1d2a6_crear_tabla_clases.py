"""crear tabla clases

Revision ID: c4e8f9b1d2a6
Revises: a8c641f2d3b7
Create Date: 2026-09-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4e8f9b1d2a6"
down_revision: Union[str, Sequence[str], None] = "a8c641f2d3b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_eliminacion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id_diagrama", sa.Uuid(), nullable=False),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("posicion_x", sa.Float(), nullable=False),
        sa.Column("posicion_y", sa.Float(), nullable=False),
        sa.Column("ancho", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["id_diagrama"], ["diagramas.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clases_id_diagrama", "clases", ["id_diagrama"])


def downgrade() -> None:
    op.drop_index("ix_clases_id_diagrama", table_name="clases")
    op.drop_table("clases")
