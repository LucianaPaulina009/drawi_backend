from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.modules.generacion_backend.domain.value_objects.estado_generacion_backend import (
    EstadoGeneracionBackend,
)


class GeneracionBackend:
    """Entidad de dominio para auditar y persistir una ejecución de generación de backend."""

    def __init__(
        self,
        *,
        id: UUID,
        id_diagrama: UUID,
        id_usuario: str,
        estado: EstadoGeneracionBackend | str,
        version_plantilla: str,
        fecha_generacion: datetime | None = None,
        detalle_error: str | None = None,
    ) -> None:
        self.id = id
        self.id_diagrama = id_diagrama
        self.id_usuario = id_usuario
        self.estado = EstadoGeneracionBackend.validar(estado)
        self.version_plantilla = version_plantilla
        if fecha_generacion and fecha_generacion.tzinfo is None:
            fecha_generacion = fecha_generacion.replace(tzinfo=timezone.utc)
        self.fecha_generacion = fecha_generacion or datetime.now(timezone.utc)
        self.detalle_error = detalle_error

    @classmethod
    def iniciar(
        cls,
        *,
        id_diagrama: UUID,
        id_usuario: str,
        version_plantilla: str = "1.0.0",
        fecha_inicio: datetime | None = None,
    ) -> GeneracionBackend:
        """Crea el registro inicial de generación en estado `validando`."""
        return cls(
            id=uuid4(),
            id_diagrama=id_diagrama,
            id_usuario=id_usuario,
            estado=EstadoGeneracionBackend.VALIDANDO,
            version_plantilla=version_plantilla,
            fecha_generacion=fecha_inicio or datetime.now(timezone.utc),
            detalle_error=None,
        )

    def iniciar_generacion(self) -> None:
        self.estado = EstadoGeneracionBackend.GENERANDO

    def iniciar_empaquetado(self) -> None:
        self.estado = EstadoGeneracionBackend.EMPAQUETANDO

    def completar(self) -> None:
        self.estado = EstadoGeneracionBackend.COMPLETADO
        self.detalle_error = None

    def marcar_error(self, detalle: str) -> None:
        self.estado = EstadoGeneracionBackend.ERROR
        self.detalle_error = detalle
