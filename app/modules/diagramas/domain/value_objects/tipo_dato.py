from __future__ import annotations

from enum import StrEnum

from app.modules.diagramas.domain.exceptions import (
    ConfiguracionAtributoInvalidaException,
    TipoDatoInvalidoException,
)


class TipoDato(StrEnum):
    """Tipos de datos soportados para atributos en diagramas UML."""

    INTEGER = "integer"
    BIGINT = "bigint"
    VARCHAR = "varchar"
    TEXT = "text"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATE = "date"
    TIMESTAMP = "timestamp"

    @classmethod
    def from_valor(cls, valor: str | TipoDato) -> TipoDato:
        if isinstance(valor, cls):
            return valor
        if not isinstance(valor, str) or not valor.strip():
            raise TipoDatoInvalidoException()
        limpio = valor.strip().lower()
        if limpio in {"char", "varchar"}:
            return cls.VARCHAR
        if limpio in {"decimal", "numeric"}:
            return cls.DECIMAL
        try:
            return cls(limpio)
        except ValueError:
            raise TipoDatoInvalidoException()

    def normalizar_configuracion(
        self,
        longitud: int | None,
        precision: int | None,
        escala: int | None,
    ) -> tuple[int | None, int | None, int | None]:
        if self == TipoDato.VARCHAR:
            if longitud is not None and (
                isinstance(longitud, bool)
                or not isinstance(longitud, int)
                or longitud < 1
            ):
                raise ConfiguracionAtributoInvalidaException()
            return longitud, None, None
        if self == TipoDato.DECIMAL:
            if precision is not None and (
                isinstance(precision, bool)
                or not isinstance(precision, int)
                or precision < 1
            ):
                raise ConfiguracionAtributoInvalidaException()
            if escala is not None and (
                isinstance(escala, bool)
                or not isinstance(escala, int)
                or escala < 0
                or precision is None
                or escala > precision
            ):
                raise ConfiguracionAtributoInvalidaException()
            return None, precision, escala
        return None, None, None
