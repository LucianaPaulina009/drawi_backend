from __future__ import annotations

from uuid import uuid4

from app.modules.diagramas.application.queries.dtos import (
    AtributoDTO,
    ClaseDetalleDTO,
)
from app.modules.inteligencia_artificial.application.schemas.diagrama_reconocido_ia import (
    AtributoReconocidoIa,
    ClaseReconocidaIa,
)
from app.modules.inteligencia_artificial.application.services.servicio_layout_importacion import (
    BoundingBox,
    ServicioLayoutImportacion,
)


def test_bounding_box_interseccion():
    b1 = BoundingBox(x_min=0, y_min=0, x_max=100, y_max=100)
    b2 = BoundingBox(x_min=50, y_min=50, x_max=150, y_max=150)
    b3 = BoundingBox(x_min=200, y_min=200, x_max=300, y_max=300)

    assert b1.intersecta(b2, margen=10.0) is True
    assert b1.intersecta(b3, margen=10.0) is False


def test_estimar_dimensiones_clase():
    ancho, alto = ServicioLayoutImportacion.estimar_dimensiones_clase(cantidad_atributos=3)
    assert ancho == 220.0
    assert alto == 70.0 + (3 * 26.0)

    ancho_custom, alto_custom = ServicioLayoutImportacion.estimar_dimensiones_clase(
        cantidad_atributos=0, ancho=300.0
    )
    assert ancho_custom == 300.0
    assert alto_custom == 70.0


def test_layout_diagrama_vacio():
    clases_rec = [
        ClaseReconocidaIa(
            referencia_semantica="ref_usuario",
            nombre="Usuario",
            atributos=[AtributoReconocidoIa(nombre="id", es_pk=True)],
            posicion_relativa_x=0.2,
            posicion_relativa_y=0.2,
        ),
        ClaseReconocidaIa(
            referencia_semantica="ref_perfil",
            nombre="Perfil",
            atributos=[AtributoReconocidoIa(nombre="id", es_pk=True)],
            posicion_relativa_x=0.8,
            posicion_relativa_y=0.8,
        ),
    ]

    posiciones = ServicioLayoutImportacion.calcular_posiciones(
        clases_reconocidas=clases_rec,
        clases_existentes=[],
    )

    assert len(posiciones) == 2
    assert "ref_usuario" in posiciones
    assert "ref_perfil" in posiciones

    x_u, y_u = posiciones["ref_usuario"]
    x_p, y_p = posiciones["ref_perfil"]
    assert x_p > x_u
    assert y_p > y_u


def test_layout_con_clases_existentes_no_colisiona():
    diag_id = uuid4()
    clase_existente = ClaseDetalleDTO(
        id=uuid4(),
        id_diagrama=diag_id,
        nombre="Cliente",
        posicion_x=100.0,
        posicion_y=100.0,
        ancho=250.0,
        atributos=(
            AtributoDTO(
                id=uuid4(),
                id_clase=uuid4(),
                tipo_dato="integer",
                nombre="id",
                longitud=None,
                precision=None,
                escala=None,
                es_llave_primaria=True,
                permite_nulo=False,
                es_unico=False,
                valor_por_defecto=None,
                orden_de_posicion=1,
                procedencia="sistema_clase",
            ),
        ),
    )

    clases_rec = [
        ClaseReconocidaIa(
            referencia_semantica="ref_orden",
            nombre="Orden",
            atributos=[AtributoReconocidoIa(nombre="id", es_pk=True)],
            posicion_relativa_x=0.1,
            posicion_relativa_y=0.1,
        )
    ]

    posiciones = ServicioLayoutImportacion.calcular_posiciones(
        clases_reconocidas=clases_rec,
        clases_existentes=[clase_existente],
    )

    x_orden, y_orden = posiciones["ref_orden"]
    # Debe ubicarse a la derecha o fuera del bounding box de Cliente
    assert x_orden >= 100.0 + 250.0 or y_orden > 100.0 + 100.0
