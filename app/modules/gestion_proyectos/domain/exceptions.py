from app.shared.domain.exceptions import (
    ConflictException,
    ForbiddenException,
    GoneException,
    NotFoundException,
    ValidationException,
)


class NombreProyectoInvalidoException(ValidationException):
    code = "NOMBRE_PROYECTO_INVALIDO"
    message = "El nombre del proyecto no puede estar vacío ni superar los 40 caracteres."


class ActualizacionProyectoVaciaException(ValidationException):
    code = "ACTUALIZACION_PROYECTO_VACIA"
    message = "Debe proporcionar al menos un campo para actualizar el proyecto."


class ProyectoNoEncontradoException(NotFoundException):
    code = "PROYECTO_NO_ENCONTRADO"
    message = "El proyecto solicitado no existe o no pertenece al usuario autenticado."


class SlugProyectoEnConflictoException(ConflictException):
    code = "SLUG_PROYECTO_EN_CONFLICTO"
    message = "No se pudo generar un slug único para el proyecto tras los reintentos permitidos."
