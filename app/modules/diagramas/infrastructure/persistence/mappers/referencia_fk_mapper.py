from __future__ import annotations

from app.modules.diagramas.domain.entities.referencia_fk import ReferenciaFK
from app.modules.diagramas.infrastructure.persistence.models.referencia_fk_model import (
    ReferenciaFKModel,
)


class ReferenciaFKMapper:
    """Mapeador entre la entidad de dominio ReferenciaFK y el modelo de persistencia ReferenciaFKModel."""

    @staticmethod
    def a_dominio(modelo: ReferenciaFKModel) -> ReferenciaFK:
        return ReferenciaFK(
            id=modelo.id,
            id_relacion=modelo.id_relacion,
            id_atributo_fk=modelo.id_atributo_fk,
            id_atributo_referenciado=modelo.id_atributo_referenciado,
            on_delete=modelo.on_delete,
            on_update=modelo.on_update,
        )

    @staticmethod
    def a_modelo(entidad: ReferenciaFK) -> ReferenciaFKModel:
        return ReferenciaFKModel(
            id=entidad.id,
            id_relacion=entidad.id_relacion,
            id_atributo_fk=entidad.id_atributo_fk,
            id_atributo_referenciado=entidad.id_atributo_referenciado,
            on_delete=entidad.on_delete,
            on_update=entidad.on_update,
        )
