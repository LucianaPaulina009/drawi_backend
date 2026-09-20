from app.modules.diagramas.domain.entities.operacion_diagrama import OperacionDiagrama
from app.modules.diagramas.infrastructure.persistence.models.operacion_diagrama_model import OperacionDiagramaModel


class OperacionDiagramaMapper:
    @staticmethod
    def a_dominio(modelo: OperacionDiagramaModel) -> OperacionDiagrama:
        return OperacionDiagrama(
            id=modelo.id, action_id=modelo.action_id, usuario_id=modelo.usuario_id,
            id_diagrama=modelo.id_diagrama, huella_payload=modelo.huella_payload,
            estado=modelo.estado, respuesta=modelo.respuesta,
        )

    @staticmethod
    def a_modelo(entidad: OperacionDiagrama) -> OperacionDiagramaModel:
        return OperacionDiagramaModel(
            id=entidad.id, action_id=entidad.action_id, usuario_id=entidad.usuario_id,
            id_diagrama=entidad.id_diagrama, huella_payload=entidad.huella_payload,
            estado=entidad.estado, respuesta=entidad.respuesta,
        )

