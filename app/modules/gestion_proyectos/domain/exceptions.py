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


class InvitacionNoEncontradaException(NotFoundException):
    code = "INVITACION_NO_ENCONTRADA"
    message = "La invitación solicitada no existe."


class InvitacionExpiradaException(GoneException):
    code = "INVITACION_EXPIRADA"
    message = "La invitación ha expirado y ya no es válida."


class UsuarioBloqueadoException(ForbiddenException):
    code = "USUARIO_BLOQUEADO"
    message = "El usuario se encuentra bloqueado en este proyecto y no puede acceder ni unirse."


class ColaboradorNoEncontradoException(NotFoundException):
    code = "COLABORADOR_NO_ENCONTRADO"
    message = "El colaborador solicitado no pertenece al proyecto."


class OperacionNoPermitidaPropietarioException(ValidationException):
    code = "OPERACION_NO_PERMITIDA_PROPIETARIO"
    message = "No se permite cambiar el rol, bloquear ni remover al propietario del proyecto."


class NoAutorizadoProyectoException(ForbiddenException):
    code = "NO_AUTORIZADO_PROYECTO"
    message = "No tienes permisos de propietario para realizar esta operación en el proyecto."
