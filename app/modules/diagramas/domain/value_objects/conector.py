from __future__ import annotations

from enum import Enum

from app.modules.diagramas.domain.exceptions import ConectorInvalidoException


class Conector(str, Enum):
    TOP = "top"
    RIGHT = "right"
    BOTTOM = "bottom"
    LEFT = "left"

    @classmethod
    def validar(cls, valor: str | Conector) -> Conector:
        if isinstance(valor, cls):
            return valor
        if isinstance(valor, str):
            val_norm = valor.strip().lower()
            for item in cls:
                if item.value == val_norm:
                    return item
        raise ConectorInvalidoException(
            f"El conector '{valor}' no es válido. Valores admitidos: {[c.value for c in cls]}."
        )
