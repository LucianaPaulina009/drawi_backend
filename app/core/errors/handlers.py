from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.shared.domain.exceptions import (
    ConflictException,
    DomainException,
    ForbiddenException,
    GoneException,
    NotFoundException,
    ValidationException,
)


def formatear_error(codigo: str, mensaje: str) -> dict[str, dict[str, str]]:
    """Formato universal para las respuestas de error."""
    return {"error": {"code": codigo, "message": mensaje}}


def configurar_manejadores_excepciones(app: FastAPI) -> None:
    # ── 1. Errores de Dominio ─────────────────────────────────────────────────

    @app.exception_handler(NotFoundException)
    async def manejar_no_encontrado(solicitud: Request, excepcion: NotFoundException):
        return JSONResponse(status_code=404, content=formatear_error(excepcion.code, excepcion.message))

    @app.exception_handler(ConflictException)
    async def manejar_conflicto(solicitud: Request, excepcion: ConflictException):
        return JSONResponse(status_code=409, content=formatear_error(excepcion.code, excepcion.message))

    @app.exception_handler(ForbiddenException)
    async def manejar_prohibido(solicitud: Request, excepcion: ForbiddenException):
        return JSONResponse(status_code=403, content=formatear_error(excepcion.code, excepcion.message))

    @app.exception_handler(GoneException)
    async def manejar_recurso_expirado(solicitud: Request, excepcion: GoneException):
        return JSONResponse(status_code=410, content=formatear_error(excepcion.code, excepcion.message))

    @app.exception_handler(ValidationException)
    async def manejar_validacion(solicitud: Request, excepcion: ValidationException):
        return JSONResponse(status_code=400, content=formatear_error(excepcion.code, excepcion.message))

    @app.exception_handler(DomainException)
    async def manejar_dominio_generico(solicitud: Request, excepcion: DomainException):
        return JSONResponse(status_code=400, content=formatear_error(excepcion.code, excepcion.message))

    # ── 2. Errores de Pydantic / Validación de Request ────────────────────────

    @app.exception_handler(RequestValidationError)
    async def manejar_validacion_solicitud(solicitud: Request, excepcion: RequestValidationError):
        error = excepcion.errors()[0]
        campo = ".".join(str(ubicacion) for ubicacion in error["loc"])
        mensaje = f"Error en '{campo}': {error['msg']}"

        return JSONResponse(
            status_code=422,
            content=formatear_error("SCHEMA_VALIDATION_ERROR", mensaje),
        )

    # ── 3. Errores Genéricos HTTP (ej. 401, 403 o rutas 404 no definidas) ─────

    @app.exception_handler(StarletteHTTPException)
    async def manejar_excepcion_http(solicitud: Request, excepcion: StarletteHTTPException):
        return JSONResponse(
            status_code=excepcion.status_code,
            content=formatear_error(
                getattr(excepcion, "code", f"HTTP_ERROR_{excepcion.status_code}"),
                str(excepcion.detail),
            ),
            headers=excepcion.headers,
        )

    # ── 4. Paracaídas Final (Errores 500 no capturados) ───────────────────────

    @app.exception_handler(Exception)
    async def manejar_excepcion_no_controlada(solicitud: Request, excepcion: Exception):
        import logging
        logging.getLogger(__name__).error("Excepción no controlada", exc_info=excepcion)

        return JSONResponse(
            status_code=500,
            content=formatear_error("INTERNAL_SERVER_ERROR", "Ha ocurrido un error interno del servidor."),
        )
