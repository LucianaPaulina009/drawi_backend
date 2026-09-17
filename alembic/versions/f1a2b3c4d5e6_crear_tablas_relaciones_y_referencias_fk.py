"""crear tablas relaciones y referencias_fk

Revision ID: f1a2b3c4d5e6
Revises: e7b1a2c3d4e5
Create Date: 2026-09-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e7b1a2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Tabla relaciones ──────────────────────────────────────────────────────
    op.create_table(
        "relaciones",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_eliminacion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id_diagrama", sa.Uuid(), nullable=False),
        sa.Column("id_clase_origen", sa.Uuid(), nullable=False),
        sa.Column("id_clase_destino", sa.Uuid(), nullable=False),
        sa.Column("tipo_relacion", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("cardinalidad_origen", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("cardinalidad_destino", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("conector_origen", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("conector_destino", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(["id_diagrama"], ["diagramas.id"]),
        sa.ForeignKeyConstraint(["id_clase_origen"], ["clases.id"]),
        sa.ForeignKeyConstraint(["id_clase_destino"], ["clases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_relaciones_id_diagrama", "relaciones", ["id_diagrama"], unique=False)
    op.create_index("ix_relaciones_id_clase_origen", "relaciones", ["id_clase_origen"], unique=False)
    op.create_index("ix_relaciones_id_clase_destino", "relaciones", ["id_clase_destino"], unique=False)

    # ── Tabla referencias_fk ──────────────────────────────────────────────────
    op.create_table(
        "referencias_fk",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_eliminacion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id_relacion", sa.Uuid(), nullable=False),
        sa.Column("id_atributo_fk", sa.Uuid(), nullable=False),
        sa.Column("id_atributo_referenciado", sa.Uuid(), nullable=False),
        sa.Column("on_delete", sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default="NO_ACTION"),
        sa.Column("on_update", sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default="NO_ACTION"),
        sa.ForeignKeyConstraint(["id_relacion"], ["relaciones.id"]),
        sa.ForeignKeyConstraint(["id_atributo_fk"], ["atributos.id"]),
        sa.ForeignKeyConstraint(["id_atributo_referenciado"], ["atributos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_referencias_fk_id_relacion", "referencias_fk", ["id_relacion"], unique=False)
    op.create_index("ix_referencias_fk_id_atributo_fk", "referencias_fk", ["id_atributo_fk"], unique=False)
    op.create_index("ix_referencias_fk_id_atributo_ref", "referencias_fk", ["id_atributo_referenciado"], unique=False)
    op.create_index(
        "uq_referencias_fk_relacion_par_activo",
        "referencias_fk",
        ["id_relacion", "id_atributo_fk", "id_atributo_referenciado"],
        unique=True,
        postgresql_where=sa.text("fecha_eliminacion IS NULL"),
        sqlite_where=sa.text("fecha_eliminacion IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_referencias_fk_relacion_par_activo", table_name="referencias_fk")
    op.drop_index("ix_referencias_fk_id_atributo_ref", table_name="referencias_fk")
    op.drop_index("ix_referencias_fk_id_atributo_fk", table_name="referencias_fk")
    op.drop_index("ix_referencias_fk_id_relacion", table_name="referencias_fk")
    op.drop_table("referencias_fk")

    op.drop_index("ix_relaciones_id_clase_destino", table_name="relaciones")
    op.drop_index("ix_relaciones_id_clase_origen", table_name="relaciones")
    op.drop_index("ix_relaciones_id_diagrama", table_name="relaciones")
    op.drop_table("relaciones")
