from __future__ import annotations

from enum import Enum

from app.modules.inteligencia_artificial.domain.exceptions import (
    EstadoInteraccionIaInvalidoException,
)


class EstadoInteraccionIa(str, Enum):
    PENDIENTE = "pendiente"
    PROCESANDO = "procesando"
    COMPLETADO = "completado"
    ERROR = "error"

    @classmethod
    def validar(cls, valor: str | EstadoInteraccionIa) -> EstadoInteraccionIa:
        if isinstance(valor, cls):
            return valor
        if isinstance(valor, str):
            val_norm = valor.strip().lower()
            for item in cls:
                if item.value == val_norm:
                    return item
        raise EstadoInteraccionIaInvalidoException(
            f"El estado de interacción '{valor}' no es válido. Valores admitidos: {[e.value for e in cls]}."
        )
