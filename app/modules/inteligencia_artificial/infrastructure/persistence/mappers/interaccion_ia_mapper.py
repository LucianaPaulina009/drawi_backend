from datetime import timezone

from app.modules.inteligencia_artificial.domain.entities.interaccion_ia import (
    InteraccionIa,
)
from app.modules.inteligencia_artificial.infrastructure.persistence.models.interaccion_ia_model import (
    InteraccionIaModel,
)


class InteraccionIaMapper:
    """Mapeador entre InteraccionIa y InteraccionIaModel."""

    @staticmethod
    def a_dominio(modelo: InteraccionIaModel) -> InteraccionIa:
        creado_en = modelo.fecha_creacion
        if creado_en and creado_en.tzinfo is None:
            creado_en = creado_en.replace(tzinfo=timezone.utc)

        return InteraccionIa(
            id=modelo.id,
            id_usuario=modelo.id_usuario,
            id_diagrama=modelo.id_diagrama,
            tipo_interaccion=modelo.tipo_interaccion,
            entrada_usuario=modelo.entrada_usuario,
            respuesta_ia=modelo.respuesta_ia,
            url_imagen=modelo.url_imagen,
            estado=modelo.estado,
            clave_idempotencia=modelo.clave_idempotencia,
            modelo_utilizado=modelo.modelo_utilizado,
            detalle_ejecucion=modelo.detalle_ejecucion,
            creado_en=creado_en,
        )

    @staticmethod
    def a_modelo(entidad: InteraccionIa) -> InteraccionIaModel:
        return InteraccionIaModel(
            id=entidad.id,
            id_usuario=entidad.id_usuario,
            id_diagrama=entidad.id_diagrama,
            tipo_interaccion=(
                entidad.tipo_interaccion.value
                if hasattr(entidad.tipo_interaccion, "value")
                else str(entidad.tipo_interaccion)
            ),
            entrada_usuario=entidad.entrada_usuario,
            respuesta_ia=entidad.respuesta_ia,
            url_imagen=entidad.url_imagen,
            estado=(
                entidad.estado.value
                if hasattr(entidad.estado, "value")
                else str(entidad.estado)
            ),
            clave_idempotencia=entidad.clave_idempotencia,
            modelo_utilizado=entidad.modelo_utilizado,
            detalle_ejecucion=entidad.detalle_ejecucion,
            fecha_creacion=entidad.creado_en,
        )
