from enum import Enum

from app.modules.diagramas.domain.exceptions import ProcedenciaAtributoInvalidaException


class ProcedenciaAtributo(str, Enum):
    """Origen persistido de un atributo del modelo diseñado."""

    MANUAL = "manual"
    SISTEMA_CLASE = "sistema_clase"
    SISTEMA_FK = "sistema_fk"

    @classmethod
    def validar(cls, valor: str | "ProcedenciaAtributo") -> "ProcedenciaAtributo":
        if isinstance(valor, cls):
            return valor
        if isinstance(valor, str):
            normalizado = valor.strip().lower()
            for item in cls:
                if item.value == normalizado:
                    return item
        raise ProcedenciaAtributoInvalidaException()
