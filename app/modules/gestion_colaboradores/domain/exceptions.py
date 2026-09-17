from app.shared.domain.exceptions import (
    ConflictException,
    ForbiddenException,
    GoneException,
    NotFoundException,
    ValidationException,
)


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
