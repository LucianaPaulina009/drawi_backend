"""crear tabla diagramas

Revision ID: a8c641f2d3b7
Revises: 57b884e79e55
Create Date: 2026-09-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8c641f2d3b7"
down_revision: Union[str, Sequence[str], None] = "57b884e79e55"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "diagramas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_eliminacion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id_proyecto", sa.Uuid(), nullable=False),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["id_proyecto"], ["proyectos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_diagramas_id_proyecto", "diagramas", ["id_proyecto"])
    op.create_index(
        "uq_diagramas_proyecto_numero_activo",
        "diagramas",
        ["id_proyecto", "numero"],
        unique=True,
        postgresql_where=sa.text("fecha_eliminacion IS NULL"),
        sqlite_where=sa.text("fecha_eliminacion IS NULL"),
    )
def downgrade() -> None:
    op.drop_index("uq_diagramas_proyecto_numero_activo", table_name="diagramas")
    op.drop_index("ix_diagramas_id_proyecto", table_name="diagramas")
    op.drop_table("diagramas")
