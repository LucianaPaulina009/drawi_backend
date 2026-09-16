from __future__ import annotations

from uuid import UUID
from sqlmodel import Session, select

from app.modules.gestion_proyectos.application.ports.readers.miembros_proyecto_reader import (
    MiembroProyectoDTO,
    MiembrosProyectoReader,
)
from app.modules.gestion_proyectos.infrastructure.persistence.models.colaborador_proyecto_model import (
    ColaboradorProyectoModel,
)
from app.modules.gestion_proyectos.infrastructure.persistence.models.proyecto_model import (
    ProyectoModel,
)
from app.shared.infrastructure.db.better_auth import BetterAuthUser


class SQLModelMiembrosProyectoReader(MiembrosProyectoReader):
    """Implementación SQLModel para consultar la lista de miembros de un proyecto."""

    def __init__(self, bd: Session) -> None:
        self.bd = bd

    def listar_miembros_proyecto(self, id_proyecto: UUID) -> list[MiembroProyectoDTO]:
        # 1. Obtener proyecto y propietario
        sentencia_proyecto = select(ProyectoModel).where(
            ProyectoModel.id == id_proyecto,
            ProyectoModel.fecha_eliminacion.is_(None),
        )
        proyecto = self.bd.exec(sentencia_proyecto).first()
        if proyecto is None:
            return []

        resultado: list[MiembroProyectoDTO] = []

        # Propietario
        sentencia_owner_user = select(BetterAuthUser).where(
            BetterAuthUser.id == proyecto.propietario_id
        )
        owner_user = self.bd.exec(sentencia_owner_user).first()
        nombre_propietario = owner_user.name if owner_user else "Propietario"
        email_propietario = owner_user.email if owner_user else ""
        image_propietario = getattr(owner_user, "image", None) if owner_user else None

        resultado.append(
            MiembroProyectoDTO(
                id=proyecto.id,  # Referencia para la fila del propietario
                usuario_id=proyecto.propietario_id,
                nombre=nombre_propietario,
                email=email_propietario,
                avatar_url=image_propietario,
                rol="propietario",
                estado="activo",
                es_propietario=True,
            )
        )

        # 2. Obtener colaboradores
        sentencia_colabs = (
            select(ColaboradorProyectoModel, BetterAuthUser)
            .outerjoin(BetterAuthUser, ColaboradorProyectoModel.id_usuario == BetterAuthUser.id)
            .where(
                ColaboradorProyectoModel.id_proyecto == id_proyecto,
                ColaboradorProyectoModel.fecha_eliminacion.is_(None),
            )
            .order_by(ColaboradorProyectoModel.fecha_creacion.asc())
        )
        filas = self.bd.exec(sentencia_colabs).all()

        for colab, user in filas:
            nombre = user.name if user else colab.id_usuario
            email = user.email if user else ""
            avatar_url = getattr(user, "image", None) if user else None

            resultado.append(
                MiembroProyectoDTO(
                    id=colab.id,
                    usuario_id=colab.id_usuario,
                    nombre=nombre,
                    email=email,
                    avatar_url=avatar_url,
                    rol=colab.rol,
                    estado=colab.estado,
                    es_propietario=False,
                )
            )

        return resultado
