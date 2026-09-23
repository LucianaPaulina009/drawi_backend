from __future__ import annotations

from app.modules.generacion_backend.domain.entities.generacion_backend import (
    GeneracionBackend,
)
from app.modules.generacion_backend.domain.value_objects.estado_generacion_backend import (
    EstadoGeneracionBackend,
)
from app.modules.generacion_backend.infrastructure.persistence.models.generacion_backend_model import (
    GeneracionBackendModel,
)


class GeneracionBackendMapper:
    """Mapea entre la entidad de dominio GeneracionBackend y el modelo de persistencia."""

    @staticmethod
    def a_dominio(modelo: GeneracionBackendModel) -> GeneracionBackend:
        return GeneracionBackend(
            id=modelo.id,
            id_diagrama=modelo.id_diagrama,
            id_usuario=modelo.id_usuario,
            estado=EstadoGeneracionBackend(modelo.estado),
            version_plantilla=modelo.version_plantilla,
            fecha_generacion=modelo.fecha_generacion,
            detalle_error=modelo.detalle_error,
        )

    @staticmethod
    def a_modelo(entidad: GeneracionBackend) -> GeneracionBackendModel:
        return GeneracionBackendModel(
            id=entidad.id,
            id_diagrama=entidad.id_diagrama,
            id_usuario=entidad.id_usuario,
            estado=entidad.estado.value,
            version_plantilla=entidad.version_plantilla,
            fecha_generacion=entidad.fecha_generacion,
            detalle_error=entidad.detalle_error,
        )
