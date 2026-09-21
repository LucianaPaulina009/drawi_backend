from app.shared.domain.exceptions import (
    ConflictException,
    DomainException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)


class TipoInteraccionIaInvalidoException(ValidationException):
    code = "TIPO_INTERACCION_IA_INVALIDO"
    message = "El tipo de interacción de IA no es válido."


class EstadoInteraccionIaInvalidoException(ValidationException):
    code = "ESTADO_INTERACCION_IA_INVALIDO"
    message = "El estado de la interacción de IA no es válido."


class EntradaUsuarioInvalidaException(ValidationException):
    code = "ENTRADA_USUARIO_INVALIDA"
    message = "El mensaje del usuario no puede estar vacío."


class ClaveIdempotenciaInvalidaException(ValidationException):
    code = "CLAVE_IDEMPOTENCIA_INVALIDA"
    message = "La clave de idempotencia debe ser un UUID válido."


class ClaveIdempotenciaConflictoException(ConflictException):
    code = "CLAVE_IDEMPOTENCIA_CONFLICTO"
    message = "La clave de idempotencia ya fue utilizada con un contenido distinto."


class InteraccionIaNoEncontradaException(NotFoundException):
    code = "INTERACCION_IA_NO_ENCONTRADA"
    message = "La interacción de IA solicitada no existe."


class ProveedorIaException(DomainException):
    code = "ERROR_PROVEEDOR_IA"
    message = "Error en el proveedor de inteligencia artificial."


class ProveedorIaRecuperableException(ProveedorIaException):
    code = "ERROR_RECUPERABLE_PROVEEDOR_IA"
    message = "Error recuperable (timeout, rate limit o indisponibilidad) en el proveedor de IA."


class ProveedorIaNoRecuperableException(ProveedorIaException):
    code = "ERROR_NO_RECUPERABLE_PROVEEDOR_IA"
    message = "Error no recuperable en el proveedor de IA."


class RespuestaIaInvalidaException(ValidationException):
    code = "RESPUESTA_IA_INVALIDA"
    message = "La respuesta generada por la IA no cumple con la estructura esperada."


class PlanIaInvalidoException(ValidationException):
    code = "PLAN_IA_INVALIDO"
    message = "El plan de acciones de la IA contiene dependencias no resolubles o no válidas."
