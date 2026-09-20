from app.modules.diagramas.domain.entities.estructura_relacion_nm import EstructuraRelacionNm
from app.modules.diagramas.infrastructure.persistence.models.estructura_relacion_nm_model import EstructuraRelacionNmModel


class EstructuraRelacionNmMapper:
    @staticmethod
    def a_dominio(modelo: EstructuraRelacionNmModel) -> EstructuraRelacionNm:
        return EstructuraRelacionNm(
            id=modelo.id, id_diagrama=modelo.id_diagrama,
            id_clase_origen=modelo.id_clase_origen, id_clase_destino=modelo.id_clase_destino,
            id_clase_intermedia=modelo.id_clase_intermedia,
            id_relacion_origen=modelo.id_relacion_origen, id_relacion_destino=modelo.id_relacion_destino,
        )

    @staticmethod
    def a_modelo(entidad: EstructuraRelacionNm) -> EstructuraRelacionNmModel:
        return EstructuraRelacionNmModel(
            id=entidad.id, id_diagrama=entidad.id_diagrama,
            id_clase_origen=entidad.id_clase_origen, id_clase_destino=entidad.id_clase_destino,
            id_clase_intermedia=entidad.id_clase_intermedia,
            id_relacion_origen=entidad.id_relacion_origen, id_relacion_destino=entidad.id_relacion_destino,
        )

