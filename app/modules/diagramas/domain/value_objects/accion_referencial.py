from __future__ import annotations

from enum import Enum

from app.modules.diagramas.domain.exceptions import AccionReferencialInvalidaException


class AccionReferencial(str, Enum):
    NO_ACTION = "NO_ACTION"
    RESTRICT = "RESTRICT"
    CASCADE = "CASCADE"
    SET_NULL = "SET_NULL"
    SET_DEFAULT = "SET_DEFAULT"

    @classmethod
    def validar(cls, valor: str | AccionReferencial) -> AccionReferencial:
        if isinstance(valor, cls):
            return valor
        if isinstance(valor, str):
            val_norm = valor.strip().upper()
            for item in cls:
                if item.value == val_norm:
                    return item
        raise AccionReferencialInvalidaException(
            f"La acción referencial '{valor}' no es válida. Valores admitidos: {[a.value for a in cls]}."
        )
