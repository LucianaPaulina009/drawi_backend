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
