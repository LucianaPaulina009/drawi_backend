from __future__ import annotations

from enum import Enum

from app.modules.inteligencia_artificial.domain.exceptions import (
    TipoInteraccionIaInvalidoException,
)


class TipoInteraccionIa(str, Enum):
    TEXTO = "texto"
    AUDIO = "audio"
    IMAGEN = "imagen"
    GENERACION_BACKEND = "generacion_backend"
    ACCION = "accion"
    RESULTADO = "resultado"
    ERROR = "error"

    @classmethod
    def validar(cls, valor: str | TipoInteraccionIa) -> TipoInteraccionIa:
        if isinstance(valor, cls):
            return valor
        if isinstance(valor, str):
            val_norm = valor.strip().lower()
            for item in cls:
                if item.value == val_norm:
                    return item
        raise TipoInteraccionIaInvalidoException(
            f"El tipo de interacción '{valor}' no es válido. Valores admitidos: {[t.value for t in cls]}."
        )
