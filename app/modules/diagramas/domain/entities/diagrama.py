from __future__ import annotations

from uuid import UUID, uuid4

from app.modules.diagramas.domain.exceptions import (
    NombreDiagramaInvalidoException,
    NumeroDiagramaInvalidoException,
)


class Diagrama:
    """Página interna de un proyecto."""

    def __init__(
        self,
        *,
        id: UUID,
        id_proyecto: UUID,
        nombre: str,
        numero: int,
    ) -> None:
        self.id = id
        self.id_proyecto = id_proyecto
        self.nombre = self.normalizar_nombre(nombre)
        self.numero = self.validar_numero(numero)

    @classmethod
    def crear(
        cls,
        *,
        id_proyecto: UUID,
        numero: int,
        nombre: str | None = None,
    ) -> Diagrama:
        numero_validado = cls.validar_numero(numero)
        return cls(
            id=uuid4(),
            id_proyecto=id_proyecto,
            nombre=nombre if nombre is not None else f"Página {numero_validado}",
            numero=numero_validado,
        )

    def actualizar(self, *, nombre: str | None = None) -> None:
        if nombre is not None:
            self.nombre = self.normalizar_nombre(nombre)

    @staticmethod
    def normalizar_nombre(nombre: str) -> str:
        if not isinstance(nombre, str):
            raise NombreDiagramaInvalidoException("El nombre del diagrama debe ser texto.")
        nombre_limpio = nombre.strip()
        if not nombre_limpio:
            raise NombreDiagramaInvalidoException()
        return nombre_limpio

    @staticmethod
    def validar_numero(numero: int) -> int:
        if isinstance(numero, bool) or not isinstance(numero, int) or numero < 1:
            raise NumeroDiagramaInvalidoException()
        return numero

    @staticmethod
    def obtener_siguiente_numero(numeros_ocupados: list[int]) -> int:
        """Retorna el menor entero positivo que no está ocupado."""
        esperado = 1
        for numero in sorted(set(numeros_ocupados)):
            if numero < esperado:
                continue
            if numero == esperado:
                esperado += 1
                continue
            break
        return esperado
