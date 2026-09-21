from __future__ import annotations

import json
import re
from typing import Annotated, Any, Literal, Union
from pydantic import BaseModel, Field, ValidationError

from app.modules.inteligencia_artificial.domain.exceptions import (
    RespuestaIaInvalidaException,
)


class PosicionSchema(BaseModel):
    x: float = 200.0
    y: float = 200.0


class AccionCrearClaseSchema(BaseModel):
    tipo: Literal["crear_clase"] = "crear_clase"
    referencia: str
    nombre: str
    posicion: PosicionSchema | None = None
    ancho: float = 280.0


class AccionCrearAtributoSchema(BaseModel):
    tipo: Literal["crear_atributo"] = "crear_atributo"
    clase_referencia: str
    nombre: str
    tipo_dato: str = "varchar"
    longitud: int | None = None
    precision: int | None = None
    escala: int | None = None
    permite_nulo: bool = True
    es_unico: bool = False
    es_llave_primaria: bool = False
    valor_por_defecto: str | None = None


class AccionCrearRelacionSchema(BaseModel):
    tipo: Literal["crear_relacion"] = "crear_relacion"
    clase_origen_referencia: str
    clase_destino_referencia: str
    tipo_relacion: str = "asociacion"
    cardinalidad_origen: str = "1"
    cardinalidad_destino: str = "1..*"
    conector_origen: str = "right"
    conector_destino: str = "left"
    nombre: str | None = None


AccionIaUnion = Annotated[
    Union[AccionCrearClaseSchema, AccionCrearAtributoSchema, AccionCrearRelacionSchema],
    Field(discriminator="tipo"),
]


class RespuestaInterpretadaIa(BaseModel):
    respuesta_usuario: str
    acciones: list[AccionIaUnion] = Field(default_factory=list)


class ValidadorRespuestaIa:
    """Extrae y valida la respuesta estructurada generada por Gemini."""

    @staticmethod
    def limpiar_texto_json(texto: str) -> str:
        t = texto.strip()
        # Si viene envuelto en markdown fences ```json ... ```
        if t.startswith("```"):
            bloques = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", t)
            if bloques:
                return bloques[0].strip()
        # Intentar extraer el primer bloque JSON entre llaves si hay texto circundante
        match = re.search(r"(\{[\s\S]*\})", t)
        if match:
            return match.group(1).strip()
        return t

    @classmethod
    def validar(cls, texto_respuesta: str) -> RespuestaInterpretadaIa:
        texto_limpio = cls.limpiar_texto_json(texto_respuesta)
        try:
            datos = json.loads(texto_limpio)
        except Exception as err:
            raise RespuestaIaInvalidaException(
                f"La IA no devolvió un JSON válido: {str(err)}"
            ) from err

        if not isinstance(datos, dict):
            raise RespuestaIaInvalidaException("El JSON de la IA debe ser un objeto.")

        try:
            return RespuestaInterpretadaIa.model_validate(datos)
        except ValidationError as err:
            raise RespuestaIaInvalidaException(
                f"La estructura de la respuesta IA es inválida: {str(err)}"
            ) from err
