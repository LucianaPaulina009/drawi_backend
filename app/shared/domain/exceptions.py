class DomainException(Exception):
    """Clase base para todos los errores de negocio."""

    code: str = "INTERNAL_DOMAIN_ERROR"
    message: str = "Ocurrió un error inesperado en el dominio."

    def __init__(self, message: str | None = None, code: str | None = None):
        if message:
            self.message = message
        if code:
            self.code = code
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


class NotFoundException(DomainException):
    """Mapea a HTTP 404 (Not Found)."""

    code = "NOT_FOUND"


class ValidationException(DomainException):
    """Mapea a HTTP 400 (Bad Request)."""

    code = "VALIDATION_ERROR"


class ConflictException(DomainException):
    """Mapea a HTTP 409 (Conflict)."""

    code = "CONFLICT_ERROR"


class ForbiddenException(DomainException):
    """Mapea a HTTP 403 (Forbidden)."""

    code = "FORBIDDEN"


class GoneException(DomainException):
    """Mapea a HTTP 410 (Gone)."""

    code = "GONE"


class PayloadTooLargeException(DomainException):
    """Mapea a HTTP 413 (Payload Too Large)."""

    code = "PAYLOAD_TOO_LARGE"


class UnsupportedMediaTypeException(DomainException):
    """Mapea a HTTP 415 (Unsupported Media Type)."""

    code = "UNSUPPORTED_MEDIA_TYPE"


class BadGatewayException(DomainException):
    """Mapea a HTTP 502 (Bad Gateway)."""

    code = "BAD_GATEWAY"


class ServiceUnavailableException(DomainException):
    """Mapea a HTTP 503 (Service Unavailable)."""

    code = "SERVICE_UNAVAILABLE"
