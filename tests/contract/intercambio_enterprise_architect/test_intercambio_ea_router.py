from __future__ import annotations

import io
from uuid import UUID, uuid4


def _crear_proyecto_y_obtener_id(client) -> UUID:
    assert client.post("/api/proyectos/crear").status_code == 201
    listado = client.get("/api/proyectos/listado")
    assert listado.status_code == 200
    return UUID(listado.json()["items"][0]["id"])


def test_exportar_diagrama_vacio_falla_400(client):
    proyecto_id = _crear_proyecto_y_obtener_id(client)
    listado = client.get(f"/api/proyectos/{proyecto_id}/diagramas")
    assert listado.status_code == 200
    diagrama_id = UUID(listado.json()["items"][0]["id"])

    # Diagrama recién creado está en blanco: exportar debe retornar 400
    res = client.get(
        f"/api/diagramas/{diagrama_id}/enterprise-architect/exportar",
        params={"proyecto_id": str(proyecto_id)},
    )
    assert res.status_code == 400
    data = res.json()
    assert data["error"]["code"] == "DIAGRAMA_VACIO"


def test_importar_en_diagrama_no_vacio_falla_409(client):
    proyecto_id = _crear_proyecto_y_obtener_id(client)
    listado = client.get(f"/api/proyectos/{proyecto_id}/diagramas")
    diagrama_id = UUID(listado.json()["items"][0]["id"])

    # Crear una clase
    res_clase = client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={"nombre": "Cliente", "posicion_x": 100, "posicion_y": 100},
    )
    assert res_clase.status_code == 201

    xml_valido = """<?xml version="1.0"?>
    <xmi:XMI xmi:version="2.1" xmlns:uml="http://schema.omg.org/spec/UML/2.1" xmlns:xmi="http://schema.omg.org/spec/XMI/2.1">
        <uml:Model xmi:type="uml:Model" name="EA_Model">
            <packagedElement xmi:type="uml:Class" xmi:id="EAID_1" name="Factura"/>
        </uml:Model>
    </xmi:XMI>
    """

    archivos = {
        "archivo": ("modelo.xml", io.BytesIO(xml_valido.encode("utf-8")), "application/xml")
    }
    datos = {"proyecto_id": str(proyecto_id)}

    res_import = client.post(
        f"/api/diagramas/{diagrama_id}/enterprise-architect/importar",
        data=datos,
        files=archivos,
    )
    assert res_import.status_code == 409
    data = res_import.json()
    assert data["error"]["code"] == "DIAGRAMA_NO_ESTA_EN_BLANCO"


def test_exportar_e_importar_roundtrip_enterprise_architect(client):
    proyecto_id = _crear_proyecto_y_obtener_id(client)
    listado = client.get(f"/api/proyectos/{proyecto_id}/diagramas")
    diag_1_id = UUID(listado.json()["items"][0]["id"])

    # 1. Crear Clase Producto
    res_c1 = client.post(
        f"/api/diagramas/{diag_1_id}/clases",
        json={"nombre": "Producto", "posicion_x": 150, "posicion_y": 120},
    )
    assert res_c1.status_code == 201
    c1_id = res_c1.json()["id"]

    # Agregar atributo precio
    res_attr = client.post(
        f"/api/clases/{c1_id}/atributos",
        json={"nombre": "precio", "tipo_dato": "decimal"},
    )
    assert res_attr.status_code == 201

    # 2. Crear Clase Categoria
    res_c2 = client.post(
        f"/api/diagramas/{diag_1_id}/clases",
        json={"nombre": "Categoria", "posicion_x": 500, "posicion_y": 120},
    )
    assert res_c2.status_code == 201
    c2_id = res_c2.json()["id"]
    c2_pk = res_c2.json()["atributos"][0]["id"]

    # 3. Crear relación 1:N Categoria -> Producto
    res_rel = client.post(
        f"/api/diagramas/{diag_1_id}/relaciones",
        json={
            "id_relacion": str(uuid4()),
            "id_clase_origen": c2_id,
            "id_clase_destino": c1_id,
            "tipo_relacion": "asociacion",
            "cardinalidad_origen": "1",
            "cardinalidad_destino": "0..*",
            "conector_origen": "right",
            "conector_destino": "left",
            "nombre": "pertenece",
            "materializacion_fk": [
                {
                    "id_referencia_fk": str(uuid4()),
                    "id_clase_fk": c1_id,
                    "id_atributo_referenciado": c2_pk,
                    "atributo_fk_nuevo": {
                        "id_atributo": str(uuid4()),
                        "nombre": "id_categoria",
                        "tipo_dato": "integer",
                        "permite_nulo": True,
                        "es_unico": False,
                    },
                }
            ],
        },
    )
    assert res_rel.status_code == 201

    # 4. Exportar el diagrama 1 a Enterprise Architect XML
    res_export = client.get(
        f"/api/diagramas/{diag_1_id}/enterprise-architect/exportar",
        params={"proyecto_id": str(proyecto_id)},
    )
    assert res_export.status_code == 200
    assert "application/xml" in res_export.headers["content-type"]
    assert "attachment" in res_export.headers["content-disposition"]
    xml_generado = res_export.text
    assert "Producto" in xml_generado
    assert "Categoria" in xml_generado
    assert "pertenece" in xml_generado

    # 5. Crear una nueva página (diagrama 2) que estará en blanco
    res_diag_2 = client.post(f"/api/proyectos/{proyecto_id}/diagramas", json={})
    assert res_diag_2.status_code == 201
    diag_2_id = UUID(res_diag_2.json()["id"])

    # 6. Importar el XML generado en el diagrama 2 en blanco
    archivos = {
        "archivo": ("export_ea.xml", io.BytesIO(xml_generado.encode("utf-8")), "application/xml")
    }
    datos = {"proyecto_id": str(proyecto_id)}

    res_import = client.post(
        f"/api/diagramas/{diag_2_id}/enterprise-architect/importar",
        data=datos,
        files=archivos,
    )
    assert res_import.status_code == 200
    import_data = res_import.json()
    assert import_data["clases_importadas"] == 2
    assert import_data["relaciones_importadas"] == 1
    assert import_data["atributos_importados"] >= 1

    # 7. Consultar detalle del diagrama 2 para verificar elementos persistidos
    res_detalle = client.get(f"/api/proyectos/{proyecto_id}/diagramas/{diag_2_id}")
    assert res_detalle.status_code == 200
    detalle = res_detalle.json()
    nombres_clases = [c["nombre"] for c in detalle["clases"]]
    assert "Producto" in nombres_clases
    assert "Categoria" in nombres_clases
    assert len(detalle["relaciones"]) == 1
    assert detalle["relaciones"][0]["tipo_relacion"] == "asociacion"
