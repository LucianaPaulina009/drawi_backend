from app.shared.domain.exceptions import (
    ConflictException,
    NotFoundException,
    ValidationException,
)


class NombreDiagramaInvalidoException(ValidationException):
    code = "NOMBRE_DIAGRAMA_INVALIDO"
    message = "El nombre del diagrama no puede estar vacío."


class NumeroDiagramaInvalidoException(ValidationException):
    code = "NUMERO_DIAGRAMA_INVALIDO"
    message = "El número del diagrama debe ser un entero positivo."


class ActualizacionDiagramaVaciaException(ValidationException):
    code = "ACTUALIZACION_DIAGRAMA_VACIA"
    message = "Debe proporcionar al menos un campo para actualizar el diagrama."


class DiagramaNoEncontradoException(NotFoundException):
    code = "DIAGRAMA_NO_ENCONTRADO"
    message = "El diagrama solicitado no existe o no pertenece al proyecto indicado."


class UltimoDiagramaException(ConflictException):
    code = "ULTIMO_DIAGRAMA"
    message = "El proyecto debe conservar al menos un diagrama."


class NombreClaseInvalidoException(ValidationException):
    code = "NOMBRE_CLASE_INVALIDO"
    message = "El nombre de la clase no puede estar vacío."


class PosicionClaseInvalidaException(ValidationException):
    code = "POSICION_CLASE_INVALIDA"
    message = "Las posiciones de la clase deben ser números finitos."


class AnchoClaseInvalidoException(ValidationException):
    code = "ANCHO_CLASE_INVALIDO"
    message = "El ancho de la clase debe ser un número mayor que cero."


class ActualizacionClaseVaciaException(ValidationException):
    code = "ACTUALIZACION_CLASE_VACIA"
    message = "Debe proporcionar al menos un campo para actualizar la clase."


class ClaseNoEncontradaException(NotFoundException):
    code = "CLASE_NO_ENCONTRADA"
    message = "La clase solicitada no existe o no pertenece al diagrama indicado."


class NombreAtributoInvalidoException(ValidationException):
    code = "NOMBRE_ATRIBUTO_INVALIDO"
    message = "El nombre del atributo no puede estar vacío."


class TipoDatoInvalidoException(ValidationException):
    code = "TIPO_DATO_INVALIDO"
    message = "El tipo de dato debe ser un texto no vacío."


class ConfiguracionAtributoInvalidaException(ValidationException):
    code = "CONFIGURACION_ATRIBUTO_INVALIDA"
    message = "La configuración del atributo no corresponde con su tipo de dato."


class OrdenAtributoInvalidoException(ValidationException):
    code = "ORDEN_ATRIBUTO_INVALIDO"
    message = "El orden de posición debe ser un entero positivo."


class OrdenAtributoFueraDeSecuenciaException(ConflictException):
    code = "ORDEN_ATRIBUTO_FUERA_DE_SECUENCIA"
    message = "El orden de posición debe pertenecer a la secuencia activa de la clase."


class ActualizacionAtributoVaciaException(ValidationException):
    code = "ACTUALIZACION_ATRIBUTO_VACIA"
    message = "Debe proporcionar al menos un campo para actualizar el atributo."


class AtributoNoEncontradoException(NotFoundException):
    code = "ATRIBUTO_NO_ENCONTRADO"
    message = "El atributo solicitado no existe o no pertenece a la clase indicada."


class ClaseYaExisteException(ConflictException):
    code = "CLASE_YA_EXISTE"
    message = "Ya existe una clase con el identificador proporcionado."


class AtributoYaExisteException(ConflictException):
    code = "ATRIBUTO_YA_EXISTE"
    message = "Ya existe un atributo con el identificador proporcionado."

