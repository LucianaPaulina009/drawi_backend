# app/shared/infrastructure/db/models.py
#
# ============================================================
# REGISTRY CENTRAL DE MODELOS  ─  ALEMBIC LO IMPORTA AQUÍ
# ============================================================
# Cada vez que agregues un nuevo módulo con tablas SQLModel,
# importa su modelo en este archivo.  Eso es todo lo que
# necesitas para que `alembic revision --autogenerate` lo detecte.
#
# Ejemplo:
#   from app.modules.users.infrastructure.persistence.models.profile_model import ProfileModel
#   from app.modules.orders.infrastructure.persistence.models.order_model import OrderModel
#
# ⚠️  No importes aquí lógica de negocio ni servicios;
#     solo los modelos que heredan de SQLModel con table=True.
# ============================================================

# ruff: noqa: F401
from app.modules.diagramas.infrastructure.persistence.models.diagrama_model import (
    DiagramaModel,
)
from app.modules.diagramas.infrastructure.persistence.models.clase_model import ClaseModel
from app.modules.diagramas.infrastructure.persistence.models.atributo_model import AtributoModel
from app.modules.diagramas.infrastructure.persistence.models.relacion_model import (
    RelacionModel,
)
from app.modules.diagramas.infrastructure.persistence.models.referencia_fk_model import (
    ReferenciaFKModel,
)
from app.modules.gestion_colaboradores.infrastructure.persistence.models.colaborador_proyecto_model import (
    ColaboradorProyectoModel,
)
from app.modules.gestion_colaboradores.infrastructure.persistence.models.invitacion_model import (
    InvitacionModel,
)
from app.modules.gestion_proyectos.infrastructure.persistence.models.proyecto_favorito_model import (
    ProyectoFavoritoModel,
)
from app.modules.gestion_proyectos.infrastructure.persistence.models.proyecto_model import (
    ProyectoModel,
)
from app.shared.infrastructure.db.better_auth import BetterAuthUser
