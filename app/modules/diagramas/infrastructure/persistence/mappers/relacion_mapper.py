from __future__ import annotations

from app.modules.diagramas.domain.entities.relacion import Relacion
from app.modules.diagramas.infrastructure.persistence.models.relacion_model import (
    RelacionModel,
)


class RelacionMapper:
    """Mapeador entre la entidad de dominio Relacion y el modelo de persistencia RelacionModel."""

    @staticmethod
    def a_dominio(modelo: RelacionModel) -> Relacion:
        return Relacion(
            id=modelo.id,
            id_diagrama=modelo.id_diagrama,
            id_clase_origen=modelo.id_clase_origen,
            id_clase_destino=modelo.id_clase_destino,
            tipo_relacion=modelo.tipo_relacion,
            cardinalidad_origen=modelo.cardinalidad_origen,
            cardinalidad_destino=modelo.cardinalidad_destino,
            conector_origen=modelo.conector_origen,
            conector_destino=modelo.conector_destino,
        )

    @staticmethod
    def a_modelo(entidad: Relacion) -> RelacionModel:
        return RelacionModel(
            id=entidad.id,
            id_diagrama=entidad.id_diagrama,
            id_clase_origen=entidad.id_clase_origen,
            id_clase_destino=entidad.id_clase_destino,
            tipo_relacion=entidad.tipo_relacion,
            cardinalidad_origen=entidad.cardinalidad_origen,
            cardinalidad_destino=entidad.cardinalidad_destino,
            conector_origen=entidad.conector_origen,
            conector_destino=entidad.conector_destino,
        )
