from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ItemProyectoUsuarioDTO:
    """Proyección inmutable de un proyecto para el listado de usuario."""

    id: UUID
    nombre: str
    color: str
    icono: str
    fecha_actualizacion: datetime
    es_favorito: bool
    slug: str
    propietario_id: str = ""
    es_dueno: bool = True



class ListadoProyectosUsuarioReader(ABC):
    """Puerto de lectura especializado para listar proyectos con su estado de favorito."""

    @abstractmethod
    def listar_por_usuario(
        self, usuario_id: str, solo_favoritos: bool = False
    ) -> list[ItemProyectoUsuarioDTO]:
        """Obtiene la lista de proyectos activos de un usuario, opcionalmente filtrada por favoritos."""
