from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.diagramas.domain.entities.operacion_diagrama import OperacionDiagrama


class OperacionDiagramaRepository(ABC):
    @abstractmethod
    def obtener_por_action_id(self, action_id: UUID) -> OperacionDiagrama | None: ...

    @abstractmethod
    def guardar(self, operacion: OperacionDiagrama) -> None: ...

