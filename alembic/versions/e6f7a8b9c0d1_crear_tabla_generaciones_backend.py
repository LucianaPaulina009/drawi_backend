"""crear tabla generaciones backend

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-09-22 14:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, Sequence[str], None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "generaciones_backend",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("id_diagrama", sa.Uuid(), nullable=False),
        sa.Column("id_usuario", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("estado", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("version_plantilla", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("fecha_generacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detalle_error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["id_diagrama"], ["diagramas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_generaciones_backend_id_diagrama"),
        "generaciones_backend",
        ["id_diagrama"],
        unique=False,
    )
    op.create_index(
        op.f("ix_generaciones_backend_id_usuario"),
        "generaciones_backend",
        ["id_usuario"],
        unique=False,
    )
    op.create_index(
        op.f("ix_generaciones_backend_fecha_generacion"),
        "generaciones_backend",
        ["fecha_generacion"],
        unique=False,
    )
    op.create_index(
        op.f("ix_generaciones_backend_estado"),
        "generaciones_backend",
        ["estado"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_generaciones_backend_estado"), table_name="generaciones_backend")
    op.drop_index(op.f("ix_generaciones_backend_fecha_generacion"), table_name="generaciones_backend")
    op.drop_index(op.f("ix_generaciones_backend_id_usuario"), table_name="generaciones_backend")
    op.drop_index(op.f("ix_generaciones_backend_id_diagrama"), table_name="generaciones_backend")
    op.drop_table("generaciones_backend")
