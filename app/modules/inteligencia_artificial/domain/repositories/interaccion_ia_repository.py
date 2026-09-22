from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.inteligencia_artificial.domain.entities.interaccion_ia import (
    InteraccionIa,
)


class InteraccionIaRepository(ABC):
    """Contrato de persistencia de interacciones con IA."""

    @abstractmethod
    def obtener_por_id(self, interaccion_id: UUID) -> InteraccionIa | None:
        """Obtiene una interacción activa por su ID."""

    @abstractmethod
    def obtener_por_idempotencia(
        self, id_usuario: str, id_diagrama: UUID, clave_idempotencia: UUID
    ) -> InteraccionIa | None:
        """Obtiene una interacción activa por la combinación única (usuario, diagrama, clave)."""

    @abstractmethod
    def listar_por_diagrama(
        self,
        id_diagrama: UUID,
        limite: int = 40,
        antes_de_id: UUID | None = None,
    ) -> list[InteraccionIa]:
        """Lista las interacciones activas de un diagrama en orden cronológico."""

    def listar_recientes_por_diagrama(
        self,
        id_diagrama: UUID,
        limite: int = 5,
    ) -> list[InteraccionIa]:
        """Lista las N interacciones activas más recientes de un diagrama en orden cronológico."""
        return self.listar_por_diagrama(id_diagrama=id_diagrama, limite=limite)

    @abstractmethod
    def guardar(self, interaccion: InteraccionIa) -> None:
        """Guarda o actualiza una interacción."""

    @abstractmethod
    def eliminar(self, interaccion_id: UUID) -> None:
        """Marca una interacción como eliminada lógicamente."""
