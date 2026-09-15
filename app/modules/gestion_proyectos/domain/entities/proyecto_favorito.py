from __future__ import annotations

from uuid import UUID, uuid4


class ProyectoFavorito:
    """Entidad de dominio para representar la marca de un proyecto como favorito por un usuario."""

    def __init__(
        self,
        id: UUID,
        usuario_id: str,
        proyecto_id: UUID,
    ) -> None:
        self.id = id
        self.usuario_id = usuario_id
        self.proyecto_id = proyecto_id

    @classmethod
    def crear(
        cls,
        *,
        usuario_id: str,
        proyecto_id: UUID,
    ) -> ProyectoFavorito:
        """Constructor nombrado para marcar un proyecto como favorito."""
        return cls(
            id=uuid4(),
            usuario_id=usuario_id,
            proyecto_id=proyecto_id,
        )
