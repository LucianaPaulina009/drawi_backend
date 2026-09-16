from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4


def ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


class Invitacion:
    """Entidad de dominio para representar el enlace de invitación temporal a un proyecto."""

    def __init__(
        self,
        id: UUID,
        id_proyecto: UUID,
        codigo_acceso: str,
        fecha_expiracion: datetime,
    ) -> None:
        self.id = id
        self.id_proyecto = id_proyecto
        self.codigo_acceso = codigo_acceso
        self.fecha_expiracion = fecha_expiracion

    @classmethod
    def crear(
        cls,
        *,
        id_proyecto: UUID,
        duracion_dias: int,
    ) -> Invitacion:
        """Fábrica de dominio para generar una nueva invitación con token seguro."""
        codigo = cls.generar_codigo_acceso()
        expiracion = ahora_utc() + timedelta(days=duracion_dias)
        return cls(
            id=uuid4(),
            id_proyecto=id_proyecto,
            codigo_acceso=codigo,
            fecha_expiracion=expiracion,
        )

    def renovar(self, duracion_dias: int) -> None:
        """Renueva el código de acceso y la fecha de expiración."""
        self.codigo_acceso = self.generar_codigo_acceso()
        self.fecha_expiracion = ahora_utc() + timedelta(days=duracion_dias)

    def ha_expirado(self, ahora: datetime | None = None) -> bool:
        """Comprueba si la invitación ha expirado."""
        momento = ahora or ahora_utc()
        if self.fecha_expiracion.tzinfo is None:
            return self.fecha_expiracion <= momento.replace(tzinfo=None)
        return self.fecha_expiracion <= momento

    @staticmethod
    def generar_codigo_acceso() -> str:
        """Genera un token no predecible URL-safe de alta entropía."""
        return secrets.token_urlsafe(24)
