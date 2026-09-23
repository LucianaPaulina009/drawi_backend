from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorBloqueanteSchema(BaseModel):
    codigo: str = Field(description="Código identificador del error estructural")
    mensaje: str = Field(description="Descripción legible del error")
    elemento: str | None = Field(default=None, description="Elemento afectado")
    elemento_tipo: str | None = Field(default=None, description="Tipo de elemento afectado")
    elemento_id: str | None = Field(default=None, description="ID del elemento afectado")
    detalle: str | None = Field(default=None, description="Detalle adicional del error")


class DiagnosticoGeneracionErrorSchema(BaseModel):
    code: str = Field(default="DIAGRAMA_NO_GENERABLE", description="Código del error")
    message: str = Field(
        default="El diagrama contiene errores que deben corregirse",
        description="Mensaje general",
    )
    mensaje_chat: str | None = Field(
        default=None,
        description="Mensaje formateado listo para incrustar en el chat del asistente",
    )
    interaccion_id: str | None = Field(
        default=None,
        description="ID de la interacción de IA persistida en base de datos",
    )
    errores: list[ErrorBloqueanteSchema] = Field(
        default_factory=list, description="Lista de errores detectados"
    )
    errores_bloqueantes: list[ErrorBloqueanteSchema] = Field(
        default_factory=list, description="Alias para retrocompatibilidad"
    )
