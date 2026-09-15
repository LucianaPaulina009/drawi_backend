"""crear tabla atributos
Revision ID: d9f3a7c1e5b4
Revises: c4e8f9b1d2a6
"""
from alembic import op
import sqlalchemy as sa
revision="d9f3a7c1e5b4"; down_revision="c4e8f9b1d2a6"; branch_labels=None; depends_on=None
def upgrade():
 op.create_table("atributos",sa.Column("id",sa.Uuid(),primary_key=True),sa.Column("fecha_creacion",sa.DateTime(timezone=True),nullable=False),sa.Column("fecha_actualizacion",sa.DateTime(timezone=True),nullable=False),sa.Column("fecha_eliminacion",sa.DateTime(timezone=True)),sa.Column("id_clase",sa.Uuid(),nullable=False),sa.Column("tipo_dato",sa.String(),nullable=False),sa.Column("nombre",sa.String(),nullable=False),sa.Column("longitud",sa.Integer()),sa.Column("precision",sa.Integer()),sa.Column("escala",sa.Integer()),sa.Column("es_llave_primaria",sa.Boolean(),nullable=False),sa.Column("permite_nulo",sa.Boolean(),nullable=False),sa.Column("es_unico",sa.Boolean(),nullable=False),sa.Column("valor_por_defecto",sa.String()),sa.Column("orden_de_posicion",sa.Integer(),nullable=False),sa.ForeignKeyConstraint(["id_clase"],["clases.id"]))
 op.create_index("ix_atributos_id_clase","atributos",["id_clase"])
 op.create_index("uq_atributos_clase_orden_activo","atributos",["id_clase","orden_de_posicion"],unique=True,postgresql_where=sa.text("fecha_eliminacion IS NULL"),sqlite_where=sa.text("fecha_eliminacion IS NULL"))
def downgrade():
 op.drop_index("uq_atributos_clase_orden_activo",table_name="atributos");op.drop_index("ix_atributos_id_clase",table_name="atributos");op.drop_table("atributos")
