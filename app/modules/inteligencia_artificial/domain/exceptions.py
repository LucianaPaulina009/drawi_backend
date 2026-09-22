from app.shared.domain.exceptions import (
    BadGatewayException,
    ConflictException,
    DomainException,
    ForbiddenException,
    NotFoundException,
    PayloadTooLargeException,
    ServiceUnavailableException,
    UnsupportedMediaTypeException,
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


class ProveedorIaRecuperableException(ServiceUnavailableException, ProveedorIaException):
    code = "ERROR_RECUPERABLE_PROVEEDOR_IA"
    message = "DRAWI no pudo procesar la solicitud porque el servicio de IA está temporalmente ocupado. Intenta nuevamente."


class ProveedorIaNoRecuperableException(BadGatewayException, ProveedorIaException):
    code = "ERROR_NO_RECUPERABLE_PROVEEDOR_IA"
    message = "Error no recuperable en el proveedor de IA."


class RespuestaIaInvalidaException(ValidationException):
    code = "RESPUESTA_IA_INVALIDA"
    message = "La respuesta generada por la IA no cumple con la estructura esperada."


class PlanIaInvalidoException(ValidationException):
    code = "PLAN_IA_INVALIDO"
    message = "El plan de acciones de la IA contiene dependencias no resolubles o no válidas."


class AudioVacioException(ValidationException):
    code = "AUDIO_VACIO"
    message = "El archivo de audio está vacío."


class AudioInvalidoException(ValidationException):
    code = "AUDIO_INVALIDO"
    message = "El archivo de audio no es válido o está corrupto."


class FormatoAudioNoSoportadoException(UnsupportedMediaTypeException):
    code = "FORMATO_AUDIO_NO_SOPORTADO"
    message = "El formato de audio enviado no es compatible con el servicio de transcripción."


class TamanoAudioExcedidoException(PayloadTooLargeException):
    code = "TAMANO_AUDIO_EXCEDIDO"
    message = "El tamaño del audio excede el límite máximo permitido de 10 MiB."


class DuracionAudioExcedidaException(PayloadTooLargeException):
    code = "DURACION_AUDIO_EXCEDIDA"
    message = "La duración del audio excede el límite máximo permitido de 60 segundos."


class ProveedorTranscripcionException(BadGatewayException):
    code = "ERROR_PROVEEDOR_TRANSCRIPCION"
    message = "Error al procesar el audio con el proveedor de transcripción."


class ProveedorTranscripcionRecuperableException(ServiceUnavailableException):
    code = "ERROR_RECUPERABLE_PROVEEDOR_TRANSCRIPCION"
    message = "El servicio de transcripción no está disponible temporalmente o excedió el tiempo de espera."


class ImagenVaciaException(ValidationException):
    code = "IMAGEN_VACIA"
    message = "El archivo de imagen está vacío."


class ImagenInvalidaException(ValidationException):
    code = "IMAGEN_INVALIDA"
    message = "El archivo de imagen no es válido o está corrupto."


class FormatoImagenNoSoportadoException(UnsupportedMediaTypeException):
    code = "FORMATO_IMAGEN_NO_SOPORTADO"
    message = "El formato de imagen no es compatible (se requiere PNG, JPEG o WEBP)."


class TamanoImagenExcedidoException(PayloadTooLargeException):
    code = "TAMANO_IMAGEN_EXCEDIDO"
    message = "El tamaño de la imagen excede el límite máximo permitido de 10 MiB."
