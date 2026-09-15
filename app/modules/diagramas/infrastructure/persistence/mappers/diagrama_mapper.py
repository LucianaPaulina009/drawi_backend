from app.modules.diagramas.domain.entities.diagrama import Diagrama
from app.modules.diagramas.infrastructure.persistence.models.diagrama_model import (
    DiagramaModel,
)


class DiagramaMapper:
    """Mapeador entre Diagrama y DiagramaModel."""

    @staticmethod
    def a_dominio(modelo: DiagramaModel) -> Diagrama:
        return Diagrama(
            id=modelo.id,
            id_proyecto=modelo.id_proyecto,
            nombre=modelo.nombre,
            numero=modelo.numero,
        )

    @staticmethod
    def a_modelo(entidad: Diagrama) -> DiagramaModel:
        return DiagramaModel(
            id=entidad.id,
            id_proyecto=entidad.id_proyecto,
            nombre=entidad.nombre,
            numero=entidad.numero,
        )
