from __future__ import annotations

from uuid import UUID, uuid4

from app.modules.diagramas.domain.exceptions import (
    ConfiguracionAtributoInvalidaException,
    NombreAtributoInvalidoException,
    OrdenAtributoInvalidoException,
    TipoDatoInvalidoException,
)

NO_DEFINIDO = object()


class Atributo:
    """Propiedad ordenable de una clase dentro de un diagrama."""

    def __init__(self, *, id: UUID, id_clase: UUID, tipo_dato: str, nombre: str, longitud: int | None, precision: int | None, escala: int | None, es_llave_primaria: bool, permite_nulo: bool, es_unico: bool, valor_por_defecto: str | None, orden_de_posicion: int) -> None:
        self.id = id
        self.id_clase = id_clase
        self.tipo_dato = self.normalizar_tipo(tipo_dato)
        self.nombre = self.normalizar_nombre(nombre)
        self.longitud, self.precision, self.escala = self.normalizar_configuracion(self.tipo_dato, longitud, precision, escala)
        self.es_llave_primaria = bool(es_llave_primaria)
        self.permite_nulo = bool(permite_nulo)
        self.es_unico = bool(es_unico)
        self.valor_por_defecto = valor_por_defecto
        self.orden_de_posicion = self.validar_orden(orden_de_posicion)

    @classmethod
    def crear(cls, *, id_clase: UUID, tipo_dato: str, nombre: str, orden_de_posicion: int, longitud: int | None = None, precision: int | None = None, escala: int | None = None, es_llave_primaria: bool = False, permite_nulo: bool = True, es_unico: bool = False, valor_por_defecto: str | None = None) -> Atributo:
        return cls(id=uuid4(), id_clase=id_clase, tipo_dato=tipo_dato, nombre=nombre, longitud=longitud, precision=precision, escala=escala, es_llave_primaria=es_llave_primaria, permite_nulo=permite_nulo, es_unico=es_unico, valor_por_defecto=valor_por_defecto, orden_de_posicion=orden_de_posicion)

    def actualizar(self, *, tipo_dato: str | object = NO_DEFINIDO, nombre: str | object = NO_DEFINIDO, longitud: int | None | object = NO_DEFINIDO, precision: int | None | object = NO_DEFINIDO, escala: int | None | object = NO_DEFINIDO, es_llave_primaria: bool | object = NO_DEFINIDO, permite_nulo: bool | object = NO_DEFINIDO, es_unico: bool | object = NO_DEFINIDO, valor_por_defecto: str | None | object = NO_DEFINIDO, orden_de_posicion: int | object = NO_DEFINIDO) -> None:
        nuevo_tipo = self.normalizar_tipo(tipo_dato) if tipo_dato is not NO_DEFINIDO else self.tipo_dato
        if nombre is not NO_DEFINIDO:
            self.nombre = self.normalizar_nombre(nombre)
        cambio_tipo = nuevo_tipo != self.tipo_dato
        self.tipo_dato = nuevo_tipo
        longitud_final = longitud if longitud is not NO_DEFINIDO else (None if cambio_tipo else self.longitud)
        precision_final = precision if precision is not NO_DEFINIDO else (None if cambio_tipo else self.precision)
        escala_final = escala if escala is not NO_DEFINIDO else (None if cambio_tipo else self.escala)
        self.longitud, self.precision, self.escala = self.normalizar_configuracion(nuevo_tipo, longitud_final, precision_final, escala_final)
        if es_llave_primaria is not NO_DEFINIDO: self.es_llave_primaria = bool(es_llave_primaria)
        if permite_nulo is not NO_DEFINIDO: self.permite_nulo = bool(permite_nulo)
        if es_unico is not NO_DEFINIDO: self.es_unico = bool(es_unico)
        if valor_por_defecto is not NO_DEFINIDO: self.valor_por_defecto = valor_por_defecto
        if orden_de_posicion is not NO_DEFINIDO: self.orden_de_posicion = self.validar_orden(orden_de_posicion)

    @staticmethod
    def normalizar_nombre(nombre: str) -> str:
        if not isinstance(nombre, str) or not (limpio := nombre.strip()): raise NombreAtributoInvalidoException()
        return limpio

    @staticmethod
    def normalizar_tipo(tipo_dato: str) -> str:
        if not isinstance(tipo_dato, str) or not (limpio := tipo_dato.strip().lower()): raise TipoDatoInvalidoException()
        return limpio

    @staticmethod
    def validar_orden(orden: int) -> int:
        if isinstance(orden, bool) or not isinstance(orden, int) or orden < 1: raise OrdenAtributoInvalidoException()
        return orden

    @classmethod
    def normalizar_configuracion(cls, tipo: str, longitud: int | None, precision: int | None, escala: int | None) -> tuple[int | None, int | None, int | None]:
        if tipo in {"char", "varchar"}:
            if longitud is not None and (isinstance(longitud, bool) or not isinstance(longitud, int) or longitud < 1): raise ConfiguracionAtributoInvalidaException()
            return longitud, None, None
        if tipo in {"decimal", "numeric"}:
            if precision is not None and (isinstance(precision, bool) or not isinstance(precision, int) or precision < 1): raise ConfiguracionAtributoInvalidaException()
            if escala is not None and (isinstance(escala, bool) or not isinstance(escala, int) or escala < 0 or precision is None or escala > precision): raise ConfiguracionAtributoInvalidaException()
            return None, precision, escala
        return None, None, None
