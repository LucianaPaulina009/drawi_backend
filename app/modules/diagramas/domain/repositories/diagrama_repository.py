from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.diagramas.domain.entities.diagrama import Diagrama


class DiagramaRepository(ABC):
    """Contrato de persistencia de páginas de proyecto."""

    @abstractmethod
    def obtener_por_id(self, diagrama_id: UUID) -> Diagrama | None:
        """Obtiene un diagrama activo por identificador."""

    @abstractmethod
    def listar_por_proyecto(self, proyecto_id: UUID) -> list[Diagrama]:
        """Lista diagramas activos de un proyecto por número ascendente."""

    @abstractmethod
    def obtener_numeros_activos_por_proyecto(self, proyecto_id: UUID) -> list[int]:
        """Obtiene los números activos de un proyecto por orden ascendente."""

    @abstractmethod
    def contar_activos_por_proyecto(self, proyecto_id: UUID) -> int:
        """Cuenta los diagramas activos del proyecto."""

    @abstractmethod
    def guardar(self, diagrama: Diagrama) -> None:
        """Guarda o actualiza un diagrama."""

    @abstractmethod
    def eliminar(self, diagrama_id: UUID) -> None:
        """Marca un diagrama como eliminado lógicamente."""
