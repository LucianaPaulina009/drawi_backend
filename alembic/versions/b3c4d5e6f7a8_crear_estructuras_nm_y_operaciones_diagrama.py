"""crear estructuras N:M y operaciones idempotentes del diagramador

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, Sequence[str], None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "estructuras_relacion_nm",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_eliminacion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id_diagrama", sa.Uuid(), nullable=False),
        sa.Column("id_clase_origen", sa.Uuid(), nullable=False),
        sa.Column("id_clase_destino", sa.Uuid(), nullable=False),
        sa.Column("id_clase_intermedia", sa.Uuid(), nullable=False),
        sa.Column("id_relacion_origen", sa.Uuid(), nullable=False),
        sa.Column("id_relacion_destino", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["id_diagrama"], ["diagramas.id"]),
        sa.ForeignKeyConstraint(["id_clase_origen"], ["clases.id"]),
        sa.ForeignKeyConstraint(["id_clase_destino"], ["clases.id"]),
        sa.ForeignKeyConstraint(["id_clase_intermedia"], ["clases.id"]),
        sa.ForeignKeyConstraint(["id_relacion_origen"], ["relaciones.id"]),
        sa.ForeignKeyConstraint(["id_relacion_destino"], ["relaciones.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_estructuras_nm_diagrama", "estructuras_relacion_nm", ["id_diagrama"])
    op.create_index("ix_estructuras_nm_intermedia", "estructuras_relacion_nm", ["id_clase_intermedia"])
    op.create_table(
        "operaciones_diagrama",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_eliminacion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("action_id", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("id_diagrama", sa.Uuid(), nullable=False),
        sa.Column("huella_payload", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("estado", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("respuesta", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["id_diagrama"], ["diagramas.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_operaciones_diagrama_action", "operaciones_diagrama", ["action_id"], unique=True)
    op.create_index("ix_operaciones_diagrama_usuario_id", "operaciones_diagrama", ["usuario_id"])
    op.create_index("ix_operaciones_diagrama_id_diagrama", "operaciones_diagrama", ["id_diagrama"])


def downgrade() -> None:
    op.drop_index("ix_operaciones_diagrama_id_diagrama", table_name="operaciones_diagrama")
    op.drop_index("ix_operaciones_diagrama_usuario_id", table_name="operaciones_diagrama")
    op.drop_index("uq_operaciones_diagrama_action", table_name="operaciones_diagrama")
    op.drop_table("operaciones_diagrama")
    op.drop_index("ix_estructuras_nm_intermedia", table_name="estructuras_relacion_nm")
    op.drop_index("ix_estructuras_nm_diagrama", table_name="estructuras_relacion_nm")
    op.drop_table("estructuras_relacion_nm")
