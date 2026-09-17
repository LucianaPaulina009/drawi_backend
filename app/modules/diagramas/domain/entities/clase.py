from __future__ import annotations

from math import isfinite
from uuid import UUID, uuid4

from app.modules.diagramas.domain.exceptions import (
    AnchoClaseInvalidoException,
    NombreClaseInvalidoException,
    PosicionClaseInvalidaException,
)


class Clase:
    """Entidad de dominio que representa una clase en un diagrama."""

    def __init__(
        self,
        *,
        id: UUID,
        id_diagrama: UUID,
        nombre: str,
        posicion_x: float,
        posicion_y: float,
        ancho: float,
    ) -> None:
        self.id = id
        self.id_diagrama = id_diagrama
        self.nombre = self.normalizar_nombre(nombre)
        self.posicion_x = self.validar_posicion(posicion_x)
        self.posicion_y = self.validar_posicion(posicion_y)
        self.ancho = self.validar_ancho(ancho)

    @classmethod
    def crear(
        cls,
        *,
        id_diagrama: UUID,
        nombre: str = "Tabla",
        posicion_x: float,
        posicion_y: float,
        ancho: float,
        id: UUID | None = None,
    ) -> Clase:
        return cls(
            id=id or uuid4(),
            id_diagrama=id_diagrama,
            nombre="Tabla" if nombre is None else nombre,
            posicion_x=posicion_x,
            posicion_y=posicion_y,
            ancho=ancho,
        )

    def actualizar(
        self,
        *,
        nombre: str | None = None,
        posicion_x: float | None = None,
        posicion_y: float | None = None,
        ancho: float | None = None,
    ) -> None:
        if nombre is not None:
            self.nombre = self.normalizar_nombre(nombre)
        if posicion_x is not None:
            self.posicion_x = self.validar_posicion(posicion_x)
        if posicion_y is not None:
            self.posicion_y = self.validar_posicion(posicion_y)
        if ancho is not None:
            self.ancho = self.validar_ancho(ancho)

    @staticmethod
    def normalizar_nombre(nombre: str) -> str:
        if not isinstance(nombre, str):
            raise NombreClaseInvalidoException("El nombre de la clase debe ser texto.")
        nombre_limpio = nombre.strip()
        if not nombre_limpio:
            raise NombreClaseInvalidoException()
        return nombre_limpio

    @staticmethod
    def validar_posicion(posicion: float) -> float:
        if isinstance(posicion, bool) or not isinstance(posicion, (int, float)):
            raise PosicionClaseInvalidaException()
        posicion_numerica = float(posicion)
        if not isfinite(posicion_numerica):
            raise PosicionClaseInvalidaException()
        return posicion_numerica

    @staticmethod
    def validar_ancho(ancho: float) -> float:
        if isinstance(ancho, bool) or not isinstance(ancho, (int, float)):
            raise AnchoClaseInvalidoException()
        ancho_numerico = float(ancho)
        if not isfinite(ancho_numerico) or ancho_numerico <= 0:
            raise AnchoClaseInvalidoException()
        return ancho_numerico
