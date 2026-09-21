from types import SimpleNamespace
from uuid import uuid4

from app.modules.inteligencia_artificial.application.services.resolvedor_referencias_ia import (
    ResolvedorReferenciasIa,
)


def test_resolver_clase_univoce_por_nombre():
    c1_id = uuid4()
    c2_id = uuid4()
    clases = [
        SimpleNamespace(id=c1_id, nombre="Cliente"),
        SimpleNamespace(id=c2_id, nombre="Pedido"),
    ]

    res = ResolvedorReferenciasIa.resolver_clase("cliente", clases)
    assert res.exito is True
    assert res.id == c1_id
    assert res.es_ambiguo is False


def test_resolver_clase_inexistente():
    clases = [SimpleNamespace(id=uuid4(), nombre="Cliente")]
    res = ResolvedorReferenciasIa.resolver_clase("Factura", clases)
    assert res.exito is False
    assert res.es_ambiguo is False
    assert "No se encontró" in (res.motivo or "")


def test_resolver_clase_ambigua():
    clases = [
        SimpleNamespace(id=uuid4(), nombre="Usuario"),
        SimpleNamespace(id=uuid4(), nombre="Usuario"),
    ]
    res = ResolvedorReferenciasIa.resolver_clase("usuario", clases)
    assert res.exito is False
    assert res.es_ambiguo is True
    assert "múltiples clases" in (res.motivo or "")


def test_resolver_atributo_especificando_clase():
    c_id = uuid4()
    a1_id = uuid4()
    a2_id = uuid4()
    clases = [
        SimpleNamespace(
            id=c_id,
            nombre="Cliente",
            atributos=[
                SimpleNamespace(id=a1_id, nombre="id", procedencia="sistema_clase"),
                SimpleNamespace(id=a2_id, nombre="telefono", procedencia="manual"),
            ],
        )
    ]

    res = ResolvedorReferenciasIa.resolver_atributo("Cliente", "telefono", clases)
    assert res.exito is True
    assert res.id == a2_id
    assert res.metadatos["id_clase"] == c_id


def test_resolver_atributo_sin_clase_ambiguo_en_varias_clases():
    c1_id = uuid4()
    c2_id = uuid4()
    a1_id = uuid4()
    a2_id = uuid4()
    clases = [
        SimpleNamespace(
            id=c1_id,
            nombre="Cliente",
            atributos=[SimpleNamespace(id=a1_id, nombre="codigo")],
        ),
        SimpleNamespace(
            id=c2_id,
            nombre="Producto",
            atributos=[SimpleNamespace(id=a2_id, nombre="codigo")],
        ),
    ]

    res = ResolvedorReferenciasIa.resolver_atributo(None, "codigo", clases)
    assert res.exito is False
    assert res.es_ambiguo is True
    assert "múltiples clases" in (res.motivo or "")


def test_resolver_relacion_univoce():
    c1_id = uuid4()
    c2_id = uuid4()
    r_id = uuid4()
    clases = [
        SimpleNamespace(id=c1_id, nombre="Cliente"),
        SimpleNamespace(id=c2_id, nombre="Pedido"),
    ]
    relaciones = [
        SimpleNamespace(id=r_id, id_clase_origen=c1_id, id_clase_destino=c2_id, nombre="cliente_pedidos")
    ]

    res = ResolvedorReferenciasIa.resolver_relacion("Cliente", "Pedido", relaciones, clases)
    assert res.exito is True
    assert res.id == r_id
