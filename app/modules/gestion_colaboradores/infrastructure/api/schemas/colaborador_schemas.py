from __future__ import annotations

from uuid import UUID
from pydantic import BaseModel, Field

from app.modules.gestion_colaboradores.domain.value_objects.rol_colaborador import (
    RolColaborador,
)


class CambiarRolRequest(BaseModel):
    """Petición para modificar el rol de un colaborador."""

    rol: RolColaborador = Field(
        ..., description="Nuevo rol del colaborador: 'ver', 'editor' o 'comentarista'."
    )


class MiembroRead(BaseModel):
    """Representación de un miembro (propietario o colaborador) de un proyecto."""

    id: UUID
    usuario_id: str
    nombre: str
    email: str
    avatar_url: str | None = None
    rol: str
    estado: str
    es_propietario: bool


class ListaMiembrosRead(BaseModel):
    """Listado de todos los miembros pertenecientes a un proyecto."""

    items: list[MiembroRead]
