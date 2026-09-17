from __future__ import annotations

from enum import Enum

from app.modules.diagramas.domain.exceptions import TipoRelacionInvalidoException


class TipoRelacion(str, Enum):
    ASOCIACION = "asociacion"
    ASOCIACION_DIRIGIDA = "asociacion_dirigida"
    HERENCIA = "herencia"
    REALIZACION = "realizacion"
    DEPENDENCIA = "dependencia"
    AGREGACION = "agregacion"
    COMPOSICION = "composicion"

    @classmethod
    def validar(cls, valor: str | TipoRelacion) -> TipoRelacion:
        if isinstance(valor, cls):
            return valor
        if isinstance(valor, str):
            val_norm = valor.strip().lower()
            for item in cls:
                if item.value == val_norm:
                    return item
        raise TipoRelacionInvalidoException(
            f"El tipo de relación '{valor}' no es válido. Valores admitidos: {[t.value for t in cls]}."
        )
