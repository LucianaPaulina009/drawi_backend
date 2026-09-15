"""
app/core/errors

Manejo centralizado de excepciones y errores HTTP de la API.
"""

from app.core.errors.exceptions import APIHTTPException
from app.core.errors.handlers import (
    configurar_manejadores_excepciones,
    formatear_error,
)

__all__ = ["APIHTTPException", "configurar_manejadores_excepciones", "formatear_error"]
