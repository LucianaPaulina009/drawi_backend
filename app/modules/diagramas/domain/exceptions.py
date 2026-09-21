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


class ProcedenciaAtributoInvalidaException(ValidationException):
    code = "PROCEDENCIA_ATRIBUTO_INVALIDA"
    message = "La procedencia del atributo no es válida."


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


class RelacionNoEncontradaException(NotFoundException):
    code = "RELACION_NO_ENCONTRADA"
    message = "La relación solicitada no existe o no pertenece al diagrama indicado."


class RelacionYaExisteException(ConflictException):
    code = "RELACION_YA_EXISTE"
    message = "Ya existe una relación con el identificador proporcionado."


class TipoRelacionInvalidoException(ValidationException):
    code = "TIPO_RELACION_INVALIDO"
    message = "El tipo de relación no es válido."


class CardinalidadInvalidaException(ValidationException):
    code = "CARDINALIDAD_INVALIDA"
    message = "La cardinalidad no tiene un formato válido."


class ConectorInvalidoException(ValidationException):
    code = "CONECTOR_INVALIDO"
    message = "El conector especificado no es válido."


class ConectorOcupadoException(ConflictException):
    code = "CONECTOR_OCUPADO"
    message = "El punto de conexión seleccionado ya está ocupado por otra relación."


class ActualizacionRelacionVaciaException(ValidationException):
    code = "ACTUALIZACION_RELACION_VACIA"
    message = "Debe proporcionar al menos un campo para actualizar la relación."


class ReferenciaFKNoEncontradaException(NotFoundException):
    code = "REFERENCIA_FK_NO_ENCONTRADA"
    message = "La referencia FK solicitada no existe o no pertenece a la relación indicada."


class ReferenciaFKYaExisteException(ConflictException):
    code = "REFERENCIA_FK_YA_EXISTE"
    message = "Ya existe una referencia FK con el identificador proporcionado."


class VinculoReferenciaFKDuplicadoException(ConflictException):
    code = "VINCULO_REFERENCIA_FK_DUPLICADO"
    message = "Ya existe una referencia FK con el mismo par de atributos en esta relación."


class AccionReferencialInvalidaException(ValidationException):
    code = "ACCION_REFERENCIAL_INVALIDA"
    message = "La acción referencial no es válida."


class ActualizacionReferenciaFKVaciaException(ValidationException):
    code = "ACTUALIZACION_REFERENCIA_FK_VACIA"
    message = "Debe proporcionar al menos un campo para actualizar la referencia FK."


class AtributoNoPerteneceAClaseRelacionException(ValidationException):
    code = "ATRIBUTO_NO_PERTENECE_A_CLASE_RELACION"
    message = "El atributo no pertenece a ninguna de las clases involucradas en la relación."


class TipoAtributoIncompatibleException(ValidationException):
    code = "TIPO_ATRIBUTO_INCOMPATIBLE"
    message = "El tipo de dato del atributo FK no es compatible con el atributo referenciado."


class AtributoNoReferenciableException(ValidationException):
    code = "ATRIBUTO_NO_REFERENCIABLE"
    message = "El atributo referenciado debe ser clave primaria o único."


class ConfiguracionReferenciaFKInvalidaException(ValidationException):
    code = "CONFIGURACION_REFERENCIA_FK_INVALIDA"
    message = "La configuración de la referencia FK es incompatible con las propiedades del atributo."


class MaterializacionRelacionRequeridaException(ValidationException):
    code = "MATERIALIZACION_RELACION_REQUERIDA"
    message = "La relación requiere al menos una referencia FK válida para su tipo y cardinalidades."


class EstructuraRelacionNmNoEncontradaException(NotFoundException):
    code = "ESTRUCTURA_RELACION_NM_NO_ENCONTRADA"
    message = "La estructura muchos-a-muchos solicitada no existe en el diagrama indicado."


class ConflictoIdempotenciaException(ConflictException):
    code = "CONFLICTO_IDEMPOTENCIA"
    message = "La clave de idempotencia ya fue usada con un contenido diferente."


class LlavePrimariaProtegidaException(ValidationException):
    code = "LLAVE_PRIMARIA_PROTEGIDA"
    message = "La llave primaria del sistema está protegida y no puede ser eliminada ni alterada estructuralmente."


class LlaveForaneaProtegidaException(ValidationException):
    """Una llave foránea de sistema solo se elimina al cerrar su relación estructural."""

    code = "LLAVE_FORANEA_PROTEGIDA"
    message = "No se puede eliminar la clave foránea."


class LlavePrimariaDuplicadaException(ValidationException):
    code = "LLAVE_PRIMARIA_DUPLICADA"
    message = "La clase ya contiene una llave primaria y no se permite agregar otra."


class AtributoEstructuralInmutableException(ValidationException):
    code = "ATRIBUTO_ESTRUCTURAL_INMUTABLE"
    message = "Los atributos estructurales o con referencias FK activas solo permiten modificar su nombre u orden de posición."


class NombreRelacionInvalidoException(ValidationException):
    code = "NOMBRE_RELACION_INVALIDO"
    message = "El nombre de la relación debe tener entre 1 y 100 caracteres."


class RelacionEstructuralInmutableException(ValidationException):
    code = "RELACION_ESTRUCTURAL_INMUTABLE"
    message = "Las relaciones son inmutables estructuralmente una vez creadas."


class ReferenciaFKEstructuralInmutableException(ValidationException):
    code = "REFERENCIA_FK_ESTRUCTURAL_INMUTABLE"
    message = "Las referencias FK son inmutables estructuralmente una vez creadas junto a su relación."
