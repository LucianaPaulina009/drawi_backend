"""crear tablas colaboradores e invitaciones

Revision ID: e7b1a2c3d4e5
Revises: d9f3a7c1e5b4
Create Date: 2026-09-16 02:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'e7b1a2c3d4e5'
down_revision: Union[str, Sequence[str], None] = 'd9f3a7c1e5b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Tabla colaboradores_proyecto ──────────────────────────────────────────
    op.create_table(
        'colaboradores_proyecto',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('fecha_creacion', sa.DateTime(timezone=True), nullable=False),
        sa.Column('fecha_actualizacion', sa.DateTime(timezone=True), nullable=False),
        sa.Column('fecha_eliminacion', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id_proyecto', sa.Uuid(), nullable=False),
        sa.Column('id_usuario', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('rol', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='ver'),
        sa.Column('estado', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='activo'),
        sa.ForeignKeyConstraint(['id_proyecto'], ['proyectos.id'], ),
        sa.ForeignKeyConstraint(['id_usuario'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id_proyecto', 'id_usuario', name='uq_colaboradores_proyecto_usuario'),
    )
    op.create_index(op.f('ix_colaboradores_proyecto_id_proyecto'), 'colaboradores_proyecto', ['id_proyecto'], unique=False)
    op.create_index(op.f('ix_colaboradores_proyecto_id_usuario'), 'colaboradores_proyecto', ['id_usuario'], unique=False)

    # ── Tabla invitaciones ────────────────────────────────────────────────────
    op.create_table(
        'invitaciones',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('fecha_creacion', sa.DateTime(timezone=True), nullable=False),
        sa.Column('fecha_actualizacion', sa.DateTime(timezone=True), nullable=False),
        sa.Column('fecha_eliminacion', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id_proyecto', sa.Uuid(), nullable=False),
        sa.Column('codigo_acceso', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('fecha_expiracion', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['id_proyecto'], ['proyectos.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id_proyecto', name='uq_invitaciones_proyecto_id'),
        sa.UniqueConstraint('codigo_acceso', name='uq_invitaciones_codigo_acceso'),
    )
    op.create_index(op.f('ix_invitaciones_id_proyecto'), 'invitaciones', ['id_proyecto'], unique=False)
    op.create_index(op.f('ix_invitaciones_codigo_acceso'), 'invitaciones', ['codigo_acceso'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_invitaciones_codigo_acceso'), table_name='invitaciones')
    op.drop_index(op.f('ix_invitaciones_id_proyecto'), table_name='invitaciones')
    op.drop_table('invitaciones')
    op.drop_index(op.f('ix_colaboradores_proyecto_id_usuario'), table_name='colaboradores_proyecto')
    op.drop_index(op.f('ix_colaboradores_proyecto_id_proyecto'), table_name='colaboradores_proyecto')
    op.drop_table('colaboradores_proyecto')
