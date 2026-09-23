import io
import zipfile
from uuid import uuid4
import pytest

from app.modules.generacion_backend.application.dtos.diagrama_generable_dto import (
    AtributoGenerable,
    ClaseGenerable,
    DiagramaGenerable,
    ReferenciaFKGenerable,
    RelacionGenerable,
)
from app.modules.generacion_backend.application.services.empaquetador_zip import (
    EmpaquetadorZip,
)
from app.modules.generacion_backend.application.services.normalizador_modelo_generado import (
    NormalizadorModeloGenerado,
)
from app.modules.generacion_backend.application.services.renderizador_plantillas_backend import (
    RenderizadorPlantillasBackend,
)


def _crear_diagrama_simple():
    id_clase = uuid4()
    pk = AtributoGenerable(
        id=uuid4(),
        id_clase=id_clase,
        tipo_dato="bigint",
        nombre="id",
        longitud=None,
        precision=None,
        escala=None,
        es_llave_primaria=True,
        permite_nulo=False,
        es_unico=True,
        valor_por_defecto=None,
        orden_de_posicion=1,
        procedencia="manual",
    )
    email = AtributoGenerable(
        id=uuid4(),
        id_clase=id_clase,
        tipo_dato="varchar",
        nombre="correo_electronico",
        longitud=120,
        precision=None,
        escala=None,
        es_llave_primaria=False,
        permite_nulo=False,
        es_unico=True,
        valor_por_defecto=None,
        orden_de_posicion=2,
        procedencia="manual",
    )
    clase = ClaseGenerable(
        id=id_clase,
        id_diagrama=uuid4(),
        nombre="Usuario",
        posicion_x=0,
        posicion_y=0,
        ancho=200,
        atributos=(pk, email),
    )
    return DiagramaGenerable(
        id=uuid4(),
        id_proyecto=uuid4(),
        nombre="Proyecto Tienda",
        numero=1,
        clases=(clase,),
        relaciones=(),
        estructuras_nm=(),
    )


def test_renderizado_plantillas_y_empaquetado_zip():
    diagrama = _crear_diagrama_simple()
    normalizador = NormalizadorModeloGenerado()
    proyecto_spring = normalizador.normalizar(diagrama, version_plantilla="1.0.0")

    assert proyecto_spring.nombre_proyecto == "Proyecto Tienda"
    assert proyecto_spring.slug == "proyecto-tienda"
    assert len(proyecto_spring.entidades) == 1
    assert proyecto_spring.entidades[0].nombre_clase == "Usuario"

    renderizador = RenderizadorPlantillasBackend()
    archivos = renderizador.renderizar(proyecto_spring)

    assert "pom.xml" in archivos
    assert "Dockerfile" in archivos
    assert "docker-compose.yml" in archivos
    assert "README.md" in archivos
    assert "src/main/resources/application.yml" in archivos
    assert "src/main/java/com/drawi/app/Application.java" in archivos
    assert "src/main/java/com/drawi/app/entity/Usuario.java" in archivos
    assert "src/main/java/com/drawi/app/repository/UsuarioRepository.java" in archivos
    assert "src/main/java/com/drawi/app/service/UsuarioService.java" in archivos
    assert "src/main/java/com/drawi/app/controller/UsuarioController.java" in archivos

    # Verificar contenido de Entity
    entity_code = archivos["src/main/java/com/drawi/app/entity/Usuario.java"]
    assert "public class Usuario" in entity_code
    assert "private Long id;" in entity_code
    assert "private String correoElectronico;" in entity_code
    assert "public Long getId()" in entity_code

    # Empaquetado
    empaquetador = EmpaquetadorZip()
    zip_bytes = empaquetador.empaquetar(archivos)

    assert isinstance(zip_bytes, bytes)
    assert len(zip_bytes) > 0

    # Verificar que el ZIP es válido y contiene los archivos
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z:
        nombres = z.namelist()
        assert "pom.xml" in nombres
        assert "src/main/java/com/drawi/app/entity/Usuario.java" in nombres
        assert z.read("pom.xml").decode("utf-8") == archivos["pom.xml"]


def test_renderizado_asociacion_many_to_one_con_join_column_insertable_false():
    id_u = uuid4()
    pk_u = AtributoGenerable(id=uuid4(), id_clase=id_u, tipo_dato="bigint", nombre="id", longitud=None, precision=None, escala=None, es_llave_primaria=True, permite_nulo=False, es_unico=True, valor_por_defecto=None, orden_de_posicion=1, procedencia="manual")
    clase_u = ClaseGenerable(id=id_u, id_diagrama=uuid4(), nombre="Cliente", posicion_x=0, posicion_y=0, ancho=200, atributos=(pk_u,))

    id_v = uuid4()
    pk_v = AtributoGenerable(id=uuid4(), id_clase=id_v, tipo_dato="bigint", nombre="id", longitud=None, precision=None, escala=None, es_llave_primaria=True, permite_nulo=False, es_unico=True, valor_por_defecto=None, orden_de_posicion=1, procedencia="manual")
    clase_v = ClaseGenerable(id=id_v, id_diagrama=uuid4(), nombre="Vehiculo", posicion_x=0, posicion_y=0, ancho=200, atributos=(pk_v,))

    id_inter = uuid4()
    pk_inter = AtributoGenerable(id=uuid4(), id_clase=id_inter, tipo_dato="bigint", nombre="id", longitud=None, precision=None, escala=None, es_llave_primaria=True, permite_nulo=False, es_unico=True, valor_por_defecto=None, orden_de_posicion=1, procedencia="manual")
    fk_u = AtributoGenerable(id=uuid4(), id_clase=id_inter, tipo_dato="bigint", nombre="cliente_id", longitud=None, precision=None, escala=None, es_llave_primaria=False, permite_nulo=False, es_unico=False, valor_por_defecto=None, orden_de_posicion=2, procedencia="sistema_fk")
    fk_v = AtributoGenerable(id=uuid4(), id_clase=id_inter, tipo_dato="bigint", nombre="vehiculo_id", longitud=None, precision=None, escala=None, es_llave_primaria=False, permite_nulo=False, es_unico=False, valor_por_defecto=None, orden_de_posicion=3, procedencia="sistema_fk")
    clase_inter = ClaseGenerable(id=id_inter, id_diagrama=uuid4(), nombre="ClienteVehiculo", posicion_x=0, posicion_y=0, ancho=200, atributos=(pk_inter, fk_u, fk_v))

    rel_id = uuid4()
    ref_fk = ReferenciaFKGenerable(id=uuid4(), id_relacion=rel_id, id_atributo_fk=fk_u.id, id_atributo_referenciado=pk_u.id, on_delete="NO_ACTION", on_update="NO_ACTION")
    rel_u = RelacionGenerable(
        id=rel_id, id_diagrama=uuid4(), id_clase_origen=id_u, id_clase_destino=id_inter,
        tipo_relacion="asociacion", cardinalidad_origen="1", cardinalidad_destino="0..*",
        conector_origen="right", conector_destino="left", referencias_fk=(ref_fk,)
    )

    diag = DiagramaGenerable(
        id=uuid4(), id_proyecto=uuid4(), nombre="App Transportes", numero=1,
        clases=(clase_u, clase_v, clase_inter), relaciones=(rel_u,), estructuras_nm=()
    )
    proyecto_spring = NormalizadorModeloGenerado().normalizar(diag)
    archivos = RenderizadorPlantillasBackend().renderizar(proyecto_spring)

    inter_code = archivos["src/main/java/com/drawi/app/entity/ClienteVehiculo.java"]
    assert "@JoinColumn(name = \"cliente_id\", insertable = false, updatable = false)" in inter_code
    assert "private Cliente cliente;" in inter_code
    assert "private Long clienteId;" in inter_code


def test_archivos_renderizados_y_empaquetados_no_contienen_bom():
    diagrama = _crear_diagrama_simple()
    normalizador = NormalizadorModeloGenerado()
    proyecto_spring = normalizador.normalizar(diagrama, version_plantilla="1.0.0")

    renderizador = RenderizadorPlantillasBackend()
    archivos = renderizador.renderizar(proyecto_spring)

    # 1. Ningún archivo renderizado como string debe comenzar con el caracter BOM '\ufeff'
    for ruta, contenido in archivos.items():
        assert not contenido.startswith("\ufeff"), f"Archivo {ruta} contiene caracter BOM en string"

    # 2. Ningún archivo empaquetado en el ZIP debe comenzar con los bytes b'\xef\xbb\xbf'
    empaquetador = EmpaquetadorZip()
    zip_bytes = empaquetador.empaquetar(archivos)

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z:
        for nombre in z.namelist():
            raw_bytes = z.read(nombre)
            assert not raw_bytes.startswith(b"\xef\xbb\xbf"), f"Archivo en ZIP {nombre} contiene bytes UTF-8 BOM"

    # 3. Ninguna plantilla .j2 en disco debe tener bytes BOM
    templates_dir = renderizador.templates_dir
    for template_file in templates_dir.glob("*.j2"):
        bytes_contenido = template_file.read_bytes()
        assert not bytes_contenido.startswith(b"\xef\xbb\xbf"), f"Plantilla {template_file.name} contiene bytes BOM"


