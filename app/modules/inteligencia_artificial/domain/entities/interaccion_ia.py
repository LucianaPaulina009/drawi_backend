from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from app.modules.inteligencia_artificial.domain.exceptions import (
    EntradaUsuarioInvalidaException,
)
from app.modules.inteligencia_artificial.domain.value_objects.estado_interaccion_ia import (
    EstadoInteraccionIa,
)
from app.modules.inteligencia_artificial.domain.value_objects.tipo_interaccion_ia import (
    TipoInteraccionIa,
)


class InteraccionIa:
    """Representa una interacción persistente de conversación o acción con DRAWI."""

    def __init__(
        self,
        *,
        id: UUID,
        id_usuario: str,
        id_diagrama: UUID,
        tipo_interaccion: TipoInteraccionIa | str,
        entrada_usuario: str | None,
        respuesta_ia: str | None,
        url_imagen: str | None,
        estado: EstadoInteraccionIa | str,
        clave_idempotencia: UUID,
        modelo_utilizado: str | None = None,
        detalle_ejecucion: dict[str, Any] | list[Any] | None = None,
        creado_en: datetime | None = None,
    ) -> None:
        self.id = id
        self.id_usuario = id_usuario
        self.id_diagrama = id_diagrama
        self.tipo_interaccion = TipoInteraccionIa.validar(tipo_interaccion)
        self.entrada_usuario = self._validar_entrada_usuario(self.tipo_interaccion, entrada_usuario)
        self.respuesta_ia = respuesta_ia
        self.url_imagen = url_imagen
        self.estado = EstadoInteraccionIa.validar(estado)
        self.clave_idempotencia = clave_idempotencia
        self.modelo_utilizado = modelo_utilizado
        self.detalle_ejecucion = detalle_ejecucion
        if creado_en and creado_en.tzinfo is None:
            creado_en = creado_en.replace(tzinfo=timezone.utc)
        self.creado_en = creado_en or datetime.now(timezone.utc)

    @classmethod
    def crear(
        cls,
        *,
        id_usuario: str,
        id_diagrama: UUID,
        clave_idempotencia: UUID,
        tipo_interaccion: TipoInteraccionIa | str = TipoInteraccionIa.TEXTO,
        entrada_usuario: str | None = None,
        url_imagen: str | None = None,
        creado_en: datetime | None = None,
    ) -> InteraccionIa:
        return cls(
            id=uuid4(),
            id_usuario=id_usuario,
            id_diagrama=id_diagrama,
            tipo_interaccion=tipo_interaccion,
            entrada_usuario=entrada_usuario,
            respuesta_ia=None,
            url_imagen=url_imagen,
            estado=EstadoInteraccionIa.PENDIENTE,
            clave_idempotencia=clave_idempotencia,
            modelo_utilizado=None,
            detalle_ejecucion=None,
            creado_en=creado_en,
        )

    def marcar_procesando(self) -> None:
        self.estado = EstadoInteraccionIa.PROCESANDO

    def completar(
        self,
        *,
        respuesta_ia: str,
        modelo_utilizado: str | None = None,
        detalle_ejecucion: dict[str, Any] | list[Any] | None = None,
    ) -> None:
        self.estado = EstadoInteraccionIa.COMPLETADO
        self.respuesta_ia = respuesta_ia
        self.modelo_utilizado = modelo_utilizado
        self.detalle_ejecucion = detalle_ejecucion

    def marcar_error(
        self,
        *,
        respuesta_ia: str,
        modelo_utilizado: str | None = None,
        detalle_ejecucion: dict[str, Any] | list[Any] | None = None,
    ) -> None:
        self.estado = EstadoInteraccionIa.ERROR
        self.respuesta_ia = respuesta_ia
        self.modelo_utilizado = modelo_utilizado
        self.detalle_ejecucion = detalle_ejecucion

    @staticmethod
    def _validar_entrada_usuario(
        tipo: TipoInteraccionIa, entrada: str | None
    ) -> str | None:
        if tipo == TipoInteraccionIa.TEXTO:
            if not isinstance(entrada, str) or not entrada.strip():
                raise EntradaUsuarioInvalidaException()
            return entrada.strip()
        return entrada.strip() if isinstance(entrada, str) and entrada.strip() else entrada
