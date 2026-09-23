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
        # Normalizar tildes y caracteres especiales frecuentes
        limpio = (
            limpio.replace("á", "a")
            .replace("é", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ú", "u")
        )

        if limpio in {"char", "varchar", "string", "str", "cadena", "caracter", "texto_corto"}:
            return cls.VARCHAR
        if limpio in {"int", "integer", "int4", "entero", "numero", "cantidad", "contador", "edad", "num", "secuencia"}:
            return cls.INTEGER
        if limpio in {"bigint", "int8", "long", "bigserial", "serial"}:
            return cls.BIGINT
        if limpio in {"decimal", "numeric", "float", "double", "real", "money", "moneda", "precio", "monto", "importe", "saldo", "total", "porcentaje"}:
            return cls.DECIMAL
        if limpio in {"boolean", "bool", "booleano", "logico", "flag", "activo", "estado"}:
            return cls.BOOLEAN
        if limpio in {"text", "texto", "clob", "memo", "nota", "descripcion"}:
            return cls.TEXT
        if limpio in {"date", "fecha"}:
            return cls.DATE
        if limpio in {"timestamp", "datetime", "datetime2", "timestamptz", "fecha_hora", "fechahora", "tiempo"}:
            return cls.TIMESTAMP
        try:
            return cls(limpio)
        except ValueError:
            raise TipoDatoInvalidoException()

    @classmethod
    def normalizar_o_inferir(
        cls,
        tipo_dato: str | TipoDato | None,
        nombre_atributo: str = "",
        por_defecto: TipoDato = VARCHAR,
    ) -> TipoDato:
        """Normaliza el tipo de dato o infiere uno adecuado según el nombre del campo si es nulo, vacío o no reconocido."""
        if tipo_dato is not None and isinstance(tipo_dato, (str, cls)):
            try:
                return cls.from_valor(tipo_dato)
            except TipoDatoInvalidoException:
                pass

        import re
        nombre_limpio = (nombre_atributo or "").strip().lower()
        nombre_limpio = (
            nombre_limpio.replace("á", "a")
            .replace("é", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ú", "u")
        )

        if re.search(r"(precio|monto|total|saldo|importe|tarifa|costo|coste|subtotal|descuento|comision|sueldo|salario|pago)", nombre_limpio):
            return cls.DECIMAL
        if re.search(r"(cantidad|numero|num|edad|stock|orden|posicion|pos|contador|cuota|dia|dias|mes|ano|anio|horas|minutos|segundos)", nombre_limpio):
            return cls.INTEGER
        if re.search(r"(id|_id|uuid|serial)", nombre_limpio):
            return cls.BIGINT if "id" in nombre_limpio else cls.VARCHAR
        if re.search(r"(fecha|date)", nombre_limpio):
            return cls.DATE
        if re.search(r"(activo|habilitado|es_|tiene_|bloqueado|verificado|visible)", nombre_limpio):
            return cls.BOOLEAN
        if re.search(r"(descripcion|detalle|observacion|comentario|contenido|texto|nota)", nombre_limpio):
            return cls.TEXT

        return por_defecto

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
