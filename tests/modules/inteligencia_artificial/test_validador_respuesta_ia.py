import pytest

from app.modules.inteligencia_artificial.application.services.validador_respuesta_ia import (
    AccionCrearAtributoSchema,
    AccionCrearClaseSchema,
    AccionCrearRelacionSchema,
    ValidadorRespuestaIa,
)
from app.modules.inteligencia_artificial.domain.exceptions import (
    RespuestaIaInvalidaException,
)


def test_validador_respuesta_texto_puro_sin_acciones():
    json_str = '{"respuesta_usuario": "Hola, ¿en qué te ayudo?", "acciones": []}'
    res = ValidadorRespuestaIa.validar(json_str)

    assert res.respuesta_usuario == "Hola, ¿en qué te ayudo?"
    assert len(res.acciones) == 0


def test_validador_respuesta_con_markdown_fences():
    texto = """```json
    {
      "respuesta_usuario": "Creé la clase Producto.",
      "acciones": [
        {
          "tipo": "crear_clase",
          "referencia": "producto",
          "nombre": "Producto",
          "posicion": {"x": 100, "y": 200}
        }
      ]
    }
    ```"""
    res = ValidadorRespuestaIa.validar(texto)

    assert res.respuesta_usuario == "Creé la clase Producto."
    assert len(res.acciones) == 1
    assert isinstance(res.acciones[0], AccionCrearClaseSchema)
    assert res.acciones[0].referencia == "producto"
    assert res.acciones[0].nombre == "Producto"
    assert res.acciones[0].posicion.x == 100


def test_validador_respuesta_con_acciones_completas():
    json_str = """{
      "respuesta_usuario": "Estructura creada.",
      "acciones": [
        {
          "tipo": "crear_clase",
          "referencia": "cliente",
          "nombre": "Cliente"
        },
        {
          "tipo": "crear_atributo",
          "clase_referencia": "cliente",
          "nombre": "email",
          "tipo_dato": "varchar",
          "longitud": 150,
          "es_unico": true
        },
        {
          "tipo": "crear_relacion",
          "clase_origen_referencia": "cliente",
          "clase_destino_referencia": "pedido",
          "tipo_relacion": "asociacion",
          "cardinalidad_origen": "1",
          "cardinalidad_destino": "1..*",
          "nombre": "Realiza"
        }
      ]
    }"""
    res = ValidadorRespuestaIa.validar(json_str)

    assert len(res.acciones) == 3
    assert isinstance(res.acciones[0], AccionCrearClaseSchema)
    assert isinstance(res.acciones[1], AccionCrearAtributoSchema)
    assert isinstance(res.acciones[2], AccionCrearRelacionSchema)


def test_validador_json_invalido_falla():
    with pytest.raises(RespuestaIaInvalidaException):
        ValidadorRespuestaIa.validar("esto no es json")


def test_validador_tipo_accion_desconocido_falla():
    json_str = '{"respuesta_usuario": "err", "acciones": [{"tipo": "eliminar_base_datos"}]}'
    with pytest.raises(RespuestaIaInvalidaException):
        ValidadorRespuestaIa.validar(json_str)


def test_validador_respuesta_crud_completo():
    from app.modules.inteligencia_artificial.application.services.validador_respuesta_ia import (
        AccionActualizarAtributoSchema,
        AccionActualizarClaseSchema,
        AccionActualizarRelacionSchema,
        AccionEliminarAtributoSchema,
        AccionEliminarClaseSchema,
        AccionEliminarEstructuraNmSchema,
        AccionEliminarRelacionSchema,
    )

    json_str = """{
      "respuesta_usuario": "Operaciones CRUD ejecutadas.",
      "acciones": [
        {
          "tipo": "actualizar_clase",
          "clase_referencia": "Cliente",
          "nuevo_nombre": "ClientePremium"
        },
        {
          "tipo": "actualizar_atributo",
          "clase_referencia": "ClientePremium",
          "atributo_referencia": "telefono",
          "nuevo_nombre": "celular"
        },
        {
          "tipo": "actualizar_relacion",
          "clase_origen_referencia": "ClientePremium",
          "clase_destino_referencia": "Pedido",
          "nuevo_nombre": "compras_cliente"
        },
        {
          "tipo": "eliminar_atributo",
          "clase_referencia": "ClientePremium",
          "atributo_referencia": "fax"
        },
        {
          "tipo": "eliminar_relacion",
          "clase_origen_referencia": "ClientePremium",
          "clase_destino_referencia": "Auditoria"
        },
        {
          "tipo": "eliminar_estructura_nm",
          "clase_origen_referencia": "Estudiante",
          "clase_destino_referencia": "Curso"
        },
        {
          "tipo": "eliminar_clase",
          "clase_referencia": "Auditoria"
        }
      ]
    }"""
    res = ValidadorRespuestaIa.validar(json_str)
    assert len(res.acciones) == 7
    assert isinstance(res.acciones[0], AccionActualizarClaseSchema)
    assert isinstance(res.acciones[1], AccionActualizarAtributoSchema)
    assert isinstance(res.acciones[2], AccionActualizarRelacionSchema)
    assert isinstance(res.acciones[3], AccionEliminarAtributoSchema)
    assert isinstance(res.acciones[4], AccionEliminarRelacionSchema)
    assert isinstance(res.acciones[5], AccionEliminarEstructuraNmSchema)
    assert isinstance(res.acciones[6], AccionEliminarClaseSchema)


def test_validador_respuesta_crear_estructura_nm_con_atributo():
    from app.modules.inteligencia_artificial.application.services.validador_respuesta_ia import (
        AccionCrearAtributoSchema,
        AccionCrearEstructuraNmSchema,
    )

    json_str = """{
      "respuesta_usuario": "Creé la relación muchos a muchos entre Cliente y Vehiculo con el atributo prueba.",
      "acciones": [
        {
          "tipo": "crear_estructura_nm",
          "referencia_intermedia": "cliente_vehiculo",
          "clase_origen_referencia": "Cliente",
          "clase_destino_referencia": "Vehiculo",
          "nombre_intermedia": "Cliente_Vehiculo",
          "posicion": {"x": 350, "y": 250}
        },
        {
          "tipo": "crear_atributo",
          "clase_referencia": "cliente_vehiculo",
          "nombre": "prueba",
          "tipo_dato": "text"
        }
      ]
    }"""
    res = ValidadorRespuestaIa.validar(json_str)
    assert len(res.acciones) == 2
    assert isinstance(res.acciones[0], AccionCrearEstructuraNmSchema)
    assert res.acciones[0].clase_origen_referencia == "Cliente"
    assert res.acciones[0].clase_destino_referencia == "Vehiculo"
    assert res.acciones[0].nombre_intermedia == "Cliente_Vehiculo"
    assert res.acciones[0].posicion.x == 350

    assert isinstance(res.acciones[1], AccionCrearAtributoSchema)
    assert res.acciones[1].clase_referencia == "cliente_vehiculo"
    assert res.acciones[1].nombre == "prueba"
    assert res.acciones[1].tipo_dato == "text"


