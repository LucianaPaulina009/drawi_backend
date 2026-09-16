from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class MiembroProyectoDTO:
    id: UUID
    usuario_id: str
    nombre: str
    email: str
    avatar_url: str | None
    rol: str
    estado: str
    es_propietario: bool


class MiembrosProyectoReader(ABC):
    """Puerto para consultar la lista consolidada de miembros enriquecida con datos de usuario."""

    @abstractmethod
    def listar_miembros_proyecto(self, id_proyecto: UUID) -> list[MiembroProyectoDTO]:
        """Retorna el propietario y todos los colaboradores activos/bloqueados del proyecto."""
