from __future__ import annotations

from typing import Any


class GeneracionBackendException(Exception):
    """Excepción base del módulo de generación backend."""

    def __init__(self, mensaje: str = "Error en la generación de backend.") -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


class DiagramaNoGenerableException(GeneracionBackendException):
    """Lanzada cuando el diagrama no supera las validaciones estructurales para backend."""

    def __init__(
        self,
        mensaje: str = "El diagrama contiene errores estructurales que impiden generar el backend.",
        errores_bloqueantes: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(mensaje)
        self.errores_bloqueantes = errores_bloqueantes or []


class GeneracionBackendNoEncontradaException(GeneracionBackendException):
    """Lanzada cuando no se encuentra un registro de generación."""

    def __init__(self, mensaje: str = "Registro de generación backend no encontrado.") -> None:
        super().__init__(mensaje)


class ErrorRenderizadoPlantillaException(GeneracionBackendException):
    """Lanzada cuando ocurre un error al renderizar las plantillas de código."""

    def __init__(self, mensaje: str = "Error al renderizar las plantillas de código fuente.") -> None:
        super().__init__(mensaje)


class ErrorEmpaquetadoZipException(GeneracionBackendException):
    """Lanzada cuando ocurre un error al empaquetar el ZIP del proyecto."""

    def __init__(self, mensaje: str = "Error al empaquetar el archivo ZIP del proyecto.") -> None:
        super().__init__(mensaje)
