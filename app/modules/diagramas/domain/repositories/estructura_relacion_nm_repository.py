from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.diagramas.domain.entities.estructura_relacion_nm import EstructuraRelacionNm


class EstructuraRelacionNmRepository(ABC):
    @abstractmethod
    def obtener_por_id(self, estructura_id: UUID) -> EstructuraRelacionNm | None: ...

    @abstractmethod
    def listar_por_diagrama(self, diagrama_id: UUID) -> list[EstructuraRelacionNm]: ...

    @abstractmethod
    def obtener_por_recurso(self, recurso_id: UUID) -> EstructuraRelacionNm | None: ...

    @abstractmethod
    def guardar(self, estructura: EstructuraRelacionNm) -> None: ...

    @abstractmethod
    def eliminar(self, estructura_id: UUID) -> None: ...

