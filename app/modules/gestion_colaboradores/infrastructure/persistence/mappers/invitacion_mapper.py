from __future__ import annotations

from app.modules.gestion_colaboradores.domain.entities.invitacion import Invitacion
from app.modules.gestion_colaboradores.infrastructure.persistence.models.invitacion_model import (
    InvitacionModel,
)


class InvitacionMapper:
    """Mapper entre la entidad de dominio Invitacion y el modelo SQLModel."""

    @staticmethod
    def a_dominio(modelo: InvitacionModel) -> Invitacion:
        return Invitacion(
            id=modelo.id,
            id_proyecto=modelo.id_proyecto,
            codigo_acceso=modelo.codigo_acceso,
            fecha_expiracion=modelo.fecha_expiracion,
        )

    @staticmethod
    def a_modelo(entidad: Invitacion) -> InvitacionModel:
        return InvitacionModel(
            id=entidad.id,
            id_proyecto=entidad.id_proyecto,
            codigo_acceso=entidad.codigo_acceso,
            fecha_expiracion=entidad.fecha_expiracion,
        )
