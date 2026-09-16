from __future__ import annotations

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class InvitacionRead(BaseModel):
    """Representación pública de la invitación activa a un proyecto."""

    id: UUID
    id_proyecto: UUID
    codigo_acceso: str
    fecha_expiracion: datetime


class ValidarInvitacionResponse(BaseModel):
    """Respuesta al consultar y validar la vigencia de una invitación."""

    codigo: str
    proyecto_id: UUID
    proyecto_nombre: str
    proyecto_slug: str
    propietario_nombre: str
    ha_expirado: bool = False


class UnirseInvitacionResponse(BaseModel):
    """Respuesta tras incorporarse exitosamente a un proyecto."""

    proyecto_id: UUID
    proyecto_slug: str
    diagrama_id: UUID | None = None
    rol: str
    mensaje: str = "Te has unido al proyecto exitosamente."
