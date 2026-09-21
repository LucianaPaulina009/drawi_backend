from __future__ import annotations

from enum import Enum

from app.modules.diagramas.domain.exceptions import ConectorInvalidoException


class Conector(str, Enum):
    # Valores legacy: se mantienen para registros existentes y se proyectan en
    # el centro del lado correspondiente en el cliente.
    TOP = "top"
    RIGHT = "right"
    BOTTOM = "bottom"
    LEFT = "left"
    TOP_LEFT = "top-left"
    TOP_CENTER = "top-center"
    TOP_RIGHT = "top-right"
    RIGHT_TOP = "right-top"
    RIGHT_CENTER = "right-center"
    RIGHT_BOTTOM = "right-bottom"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_CENTER = "bottom-center"
    BOTTOM_RIGHT = "bottom-right"
    LEFT_TOP = "left-top"
    LEFT_CENTER = "left-center"
    LEFT_BOTTOM = "left-bottom"

    @classmethod
    def a_handle_canonico(cls, valor: str | "Conector") -> str:
        conector = cls.validar(valor)
        return {
            cls.TOP: cls.TOP_CENTER.value,
            cls.RIGHT: cls.RIGHT_CENTER.value,
            cls.BOTTOM: cls.BOTTOM_CENTER.value,
            cls.LEFT: cls.LEFT_CENTER.value,
        }.get(conector, conector.value)

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
