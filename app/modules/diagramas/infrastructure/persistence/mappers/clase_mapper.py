from app.modules.diagramas.domain.entities.clase import Clase
from app.modules.diagramas.infrastructure.persistence.models.clase_model import ClaseModel


class ClaseMapper:
    """Mapeador entre Clase y ClaseModel."""

    @staticmethod
    def a_dominio(modelo: ClaseModel) -> Clase:
        return Clase(
            id=modelo.id,
            id_diagrama=modelo.id_diagrama,
            nombre=modelo.nombre,
            posicion_x=modelo.posicion_x,
            posicion_y=modelo.posicion_y,
            ancho=modelo.ancho,
        )

    @staticmethod
    def a_modelo(entidad: Clase) -> ClaseModel:
        return ClaseModel(
            id=entidad.id,
            id_diagrama=entidad.id_diagrama,
            nombre=entidad.nombre,
            posicion_x=entidad.posicion_x,
            posicion_y=entidad.posicion_y,
            ancho=entidad.ancho,
        )
