from uuid import UUID

import pytest

from app.modules.diagramas.domain.entities.atributo import Atributo
from app.modules.diagramas.domain.exceptions import (
    ConfiguracionAtributoInvalidaException,
    LlaveForaneaProtegidaException,
    LlavePrimariaProtegidaException,
    NombreAtributoInvalidoException,
)
from app.modules.diagramas.application.validaciones import validar_eliminacion_atributo
from app.modules.diagramas.domain.value_objects.procedencia_atributo import ProcedenciaAtributo


def test_atributo_normaliza_campos_dependientes_del_tipo_de_dato():
    atributo = Atributo.crear(
        id_clase=UUID(int=1),
        tipo_dato=" VARCHAR ",
        nombre=" codigo ",
        longitud=40,
        precision=10,
        escala=2,
        orden_de_posicion=1,
    )

    assert atributo.tipo_dato == "varchar"
    assert atributo.nombre == "codigo"
    assert (atributo.longitud, atributo.precision, atributo.escala) == (40, None, None)

    atributo.actualizar(tipo_dato="numeric", precision=12, escala=3)

    assert (atributo.longitud, atributo.precision, atributo.escala) == (None, 12, 3)


def test_tipo_sin_configuracion_limpia_longitud_precision_y_escala():
    atributo = Atributo.crear(
        id_clase=UUID(int=1),
        tipo_dato="numeric",
        nombre="total",
        precision=10,
        escala=2,
        orden_de_posicion=1,
    )

    atributo.actualizar(tipo_dato="boolean")

    assert (atributo.longitud, atributo.precision, atributo.escala) == (None, None, None)


def test_escala_no_puede_superar_la_precision():
    with pytest.raises(ConfiguracionAtributoInvalidaException):
        Atributo.crear(
            id_clase=UUID(int=1),
            tipo_dato="numeric",
            nombre="monto",
            precision=3,
            escala=4,
            orden_de_posicion=1,
        )


@pytest.mark.parametrize("nombre", ["", "   "])
def test_nombre_atributo_vacio_es_invalido(nombre: str):
    with pytest.raises(NombreAtributoInvalidoException):
        Atributo.crear(
            id_clase=UUID(int=1),
            tipo_dato="text",
            nombre=nombre,
            orden_de_posicion=1,
        )


def test_tipo_dato_enum_invalido_lanza_excepcion():
    from app.modules.diagramas.domain.exceptions import TipoDatoInvalidoException

    with pytest.raises(TipoDatoInvalidoException):
        Atributo.crear(
            id_clase=UUID(int=1),
            tipo_dato="tipo_inventado",
            nombre="campo",
            orden_de_posicion=1,
        )


def test_llave_primaria_no_permite_nulo():
    # Intentar actualizar PK a permite_nulo=True debe fallar
    atributo = Atributo.crear(
        id_clase=UUID(int=1),
        tipo_dato="integer",
        nombre="id",
        orden_de_posicion=1,
        es_llave_primaria=True,
    )
    assert atributo.es_llave_primaria is True
    assert atributo.permite_nulo is False

    with pytest.raises(LlavePrimariaProtegidaException):
        atributo.actualizar(permite_nulo=True)


def test_atributo_crear_con_id_personalizado():
    custom_id = UUID("11111111-2222-3333-4444-555555555555")
    atributo = Atributo.crear(
        id=custom_id,
        id_clase=UUID(int=1),
        tipo_dato="integer",
        nombre="id",
        orden_de_posicion=1,
    )
    assert atributo.id == custom_id


def test_llave_foranea_de_sistema_no_se_puede_eliminar_directamente():
    atributo = Atributo.crear(
        id_clase=UUID(int=1),
        tipo_dato="integer",
        nombre="cliente_id",
        orden_de_posicion=2,
        permite_nulo=False,
        procedencia=ProcedenciaAtributo.SISTEMA_FK,
    )

    with pytest.raises(LlaveForaneaProtegidaException, match="clave foránea"):
        validar_eliminacion_atributo(atributo)


def test_tipo_dato_soporta_sinonimos_y_tildes():
    from app.modules.diagramas.domain.value_objects.tipo_dato import TipoDato

    assert TipoDato.from_valor("número") == TipoDato.INTEGER
    assert TipoDato.from_valor("cantidad") == TipoDato.INTEGER
    assert TipoDato.from_valor("precio") == TipoDato.DECIMAL
    assert TipoDato.from_valor("string") == TipoDato.VARCHAR
    assert TipoDato.from_valor("texto") == TipoDato.TEXT
    assert TipoDato.from_valor("booleano") == TipoDato.BOOLEAN
    assert TipoDato.from_valor("fecha") == TipoDato.DATE
    assert TipoDato.from_valor("datetime") == TipoDato.TIMESTAMP


def test_tipo_dato_normalizar_o_inferir():
    from app.modules.diagramas.domain.value_objects.tipo_dato import TipoDato

    assert TipoDato.normalizar_o_inferir(None, "precio") == TipoDato.DECIMAL
    assert TipoDato.normalizar_o_inferir("", "número") == TipoDato.INTEGER
    assert TipoDato.normalizar_o_inferir("desconocido", "cantidad") == TipoDato.INTEGER
    assert TipoDato.normalizar_o_inferir(None, "descripcion") == TipoDato.TEXT
    assert TipoDato.normalizar_o_inferir(None, "campo_generico") == TipoDato.VARCHAR

