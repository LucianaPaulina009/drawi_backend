from uuid import UUID

from sqlmodel import Session, select

from app.modules.diagramas.domain.entities.operacion_diagrama import OperacionDiagrama
from app.modules.diagramas.domain.repositories.operacion_diagrama_repository import OperacionDiagramaRepository
from app.modules.diagramas.infrastructure.persistence.mappers.operacion_diagrama_mapper import OperacionDiagramaMapper
from app.modules.diagramas.infrastructure.persistence.models.operacion_diagrama_model import OperacionDiagramaModel


class SQLModelOperacionDiagramaRepository(OperacionDiagramaRepository):
    def __init__(self, session: Session) -> None:
        self.bd = session

    def obtener_por_action_id(self, action_id: UUID) -> OperacionDiagrama | None:
        modelo = self.bd.exec(select(OperacionDiagramaModel).where(
            OperacionDiagramaModel.action_id == action_id,
            OperacionDiagramaModel.fecha_eliminacion.is_(None),
        )).first()
        return OperacionDiagramaMapper.a_dominio(modelo) if modelo else None

    def guardar(self, operacion: OperacionDiagrama) -> None:
        self.bd.add(OperacionDiagramaMapper.a_modelo(operacion))

