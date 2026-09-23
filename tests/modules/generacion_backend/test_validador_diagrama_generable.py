from uuid import uuid4
import pytest

from app.modules.generacion_backend.application.dtos.diagrama_generable_dto import (
    AtributoGenerable,
    ClaseGenerable,
    DiagramaGenerable,
    EstructuraRelacionNmGenerable,
    ReferenciaFKGenerable,
    RelacionGenerable,
)
from app.modules.generacion_backend.application.services.validador_diagrama_generable import (
    ValidadorDiagramaGenerable,
)


def _crear_atributo(
    id_clase,
    nombre="id",
    tipo="bigint",
    pk=True,
    nullable=False,
    longitud=None,
    precision=None,
    escala=None,
):
    return AtributoGenerable(
        id=uuid4(),
        id_clase=id_clase,
        tipo_dato=tipo,
        nombre=nombre,
        longitud=longitud,
        precision=precision,
        escala=escala,
        es_llave_primaria=pk,
        permite_nulo=nullable,
        es_unico=pk,
        valor_por_defecto=None,
        orden_de_posicion=1,
        procedencia="manual",
    )


def test_validador_diagrama_vacio_falla():
    diag = DiagramaGenerable(
        id=uuid4(),
        id_proyecto=uuid4(),
        nombre="Diagrama Vacio",
        numero=1,
        clases=(),
        relaciones=(),
        estructuras_nm=(),
    )
    validador = ValidadorDiagramaGenerable()
    resultado = validador.validar(diag)
    assert not resultado.valido
    assert any(e.codigo == "DIAGRAMA_VACIO" for e in resultado.errores_bloqueantes)


def test_validador_clase_sin_pk_falla():
    id_clase = uuid4()
    attr = _crear_atributo(id_clase, nombre="nombre", tipo="varchar", pk=False, longitud=100)
    clase = ClaseGenerable(
        id=id_clase,
        id_diagrama=uuid4(),
        nombre="Usuario",
        posicion_x=0,
        posicion_y=0,
        ancho=200,
        atributos=(attr,),
    )
    diag = DiagramaGenerable(
        id=uuid4(),
        id_proyecto=uuid4(),
        nombre="Diagrama Test",
        numero=1,
        clases=(clase,),
        relaciones=(),
        estructuras_nm=(),
    )
    validador = ValidadorDiagramaGenerable()
    resultado = validador.validar(diag)
    assert not resultado.valido
    assert any(e.codigo == "CLASE_SIN_PK" for e in resultado.errores_bloqueantes)


def test_validador_pk_nullable_falla():
    id_clase = uuid4()
    attr = _crear_atributo(id_clase, nombre="id", tipo="integer", pk=True, nullable=True)
    clase = ClaseGenerable(
        id=id_clase,
        id_diagrama=uuid4(),
        nombre="Usuario",
        posicion_x=0,
        posicion_y=0,
        ancho=200,
        atributos=(attr,),
    )
    diag = DiagramaGenerable(
        id=uuid4(),
        id_proyecto=uuid4(),
        nombre="Diagrama Test",
        numero=1,
        clases=(clase,),
        relaciones=(),
        estructuras_nm=(),
    )
    validador = ValidadorDiagramaGenerable()
    resultado = validador.validar(diag)
    assert not resultado.valido
    assert any(e.codigo == "PK_NULLABLE" for e in resultado.errores_bloqueantes)


def test_validador_tipo_dato_no_soportado():
    id_clase = uuid4()
    pk = _crear_atributo(id_clase, "id", "bigint", pk=True)
    attr_invalido = _crear_atributo(id_clase, "data", "blob_desconocido", pk=False)
    clase = ClaseGenerable(
        id=id_clase,
        id_diagrama=uuid4(),
        nombre="Documento",
        posicion_x=0,
        posicion_y=0,
        ancho=200,
        atributos=(pk, attr_invalido),
    )
    diag = DiagramaGenerable(
        id=uuid4(),
        id_proyecto=uuid4(),
        nombre="Diagrama Test",
        numero=1,
        clases=(clase,),
        relaciones=(),
        estructuras_nm=(),
    )
    validador = ValidadorDiagramaGenerable()
    resultado = validador.validar(diag)
    assert not resultado.valido
    assert any(e.codigo == "TIPO_DATO_NO_SOPORTADO" for e in resultado.errores_bloqueantes)


def test_validador_diagrama_valido_exitoso():
    id_clase_u = uuid4()
    pk_u = _crear_atributo(id_clase_u, "id", "bigint", pk=True)
    nombre_u = _crear_atributo(id_clase_u, "nombre", "varchar", pk=False, longitud=150)
    clase_u = ClaseGenerable(
        id=id_clase_u,
        id_diagrama=uuid4(),
        nombre="Usuario",
        posicion_x=0,
        posicion_y=0,
        ancho=200,
        atributos=(pk_u, nombre_u),
    )

    id_clase_p = uuid4()
    pk_p = _crear_atributo(id_clase_p, "id", "bigint", pk=True)
    fk_p = _crear_atributo(id_clase_p, "id_usuario", "bigint", pk=False)
    precio_p = _crear_atributo(id_clase_p, "precio", "decimal", pk=False, precision=10, escala=2)
    clase_p = ClaseGenerable(
        id=id_clase_p,
        id_diagrama=uuid4(),
        nombre="Pedido",
        posicion_x=250,
        posicion_y=0,
        ancho=200,
        atributos=(pk_p, fk_p, precio_p),
    )

    rel_id = uuid4()
    ref_fk = ReferenciaFKGenerable(
        id=uuid4(),
        id_relacion=rel_id,
        id_atributo_fk=fk_p.id,
        id_atributo_referenciado=pk_u.id,
        on_delete="CASCADE",
        on_update="CASCADE",
    )
    relacion = RelacionGenerable(
        id=rel_id,
        id_diagrama=uuid4(),
        id_clase_origen=id_clase_u,
        id_clase_destino=id_clase_p,
        tipo_relacion="asociacion",
        cardinalidad_origen="1",
        cardinalidad_destino="*",
        conector_origen="right",
        conector_destino="left",
        referencias_fk=(ref_fk,),
    )

    diag = DiagramaGenerable(
        id=uuid4(),
        id_proyecto=uuid4(),
        nombre="E-Commerce",
        numero=1,
        clases=(clase_u, clase_p),
        relaciones=(relacion,),
        estructuras_nm=(),
    )
    validador = ValidadorDiagramaGenerable()
    resultado = validador.validar(diag)
    assert resultado.valido
    assert len(resultado.errores_bloqueantes) == 0


def test_validador_estructura_nm_valida_con_intermedia_exitoso():
    id_diag = uuid4()
    id_orig = uuid4()
    pk_orig = _crear_atributo(id_orig, "id", "bigint", pk=True)
    clase_orig = ClaseGenerable(id=id_orig, id_diagrama=id_diag, nombre="Estudiante", posicion_x=0, posicion_y=0, ancho=200, atributos=(pk_orig,))

    id_dest = uuid4()
    pk_dest = _crear_atributo(id_dest, "id", "bigint", pk=True)
    clase_dest = ClaseGenerable(id=id_dest, id_diagrama=id_diag, nombre="Curso", posicion_x=400, posicion_y=0, ancho=200, atributos=(pk_dest,))

    id_inter = uuid4()
    pk_inter = _crear_atributo(id_inter, "id", "bigint", pk=True)
    fk_orig = _crear_atributo(id_inter, "estudiante_id", "bigint", pk=False)
    fk_dest = _crear_atributo(id_inter, "curso_id", "bigint", pk=False)
    clase_inter = ClaseGenerable(id=id_inter, id_diagrama=id_diag, nombre="EstudianteCurso", posicion_x=200, posicion_y=200, ancho=220, atributos=(pk_inter, fk_orig, fk_dest))

    rel_orig_id = uuid4()
    rel_orig = RelacionGenerable(
        id=rel_orig_id, id_diagrama=id_diag, id_clase_origen=id_orig, id_clase_destino=id_inter,
        tipo_relacion="asociacion", cardinalidad_origen="1", cardinalidad_destino="0..*",
        conector_origen="right", conector_destino="left",
        referencias_fk=(ReferenciaFKGenerable(id=uuid4(), id_relacion=rel_orig_id, id_atributo_fk=fk_orig.id, id_atributo_referenciado=pk_orig.id, on_delete="CASCADE", on_update="CASCADE"),)
    )

    rel_dest_id = uuid4()
    rel_dest = RelacionGenerable(
        id=rel_dest_id, id_diagrama=id_diag, id_clase_origen=id_dest, id_clase_destino=id_inter,
        tipo_relacion="asociacion", cardinalidad_origen="1", cardinalidad_destino="0..*",
        conector_origen="left", conector_destino="right",
        referencias_fk=(ReferenciaFKGenerable(id=uuid4(), id_relacion=rel_dest_id, id_atributo_fk=fk_dest.id, id_atributo_referenciado=pk_dest.id, on_delete="CASCADE", on_update="CASCADE"),)
    )

    nm = EstructuraRelacionNmGenerable(
        id=uuid4(), id_diagrama=id_diag, id_clase_origen=id_orig, id_clase_destino=id_dest,
        id_clase_intermedia=id_inter, id_relacion_origen=rel_orig_id, id_relacion_destino=rel_dest_id,
    )

    diag = DiagramaGenerable(
        id=id_diag, id_proyecto=uuid4(), nombre="Universidad", numero=1,
        clases=(clase_orig, clase_dest, clase_inter),
        relaciones=(rel_orig, rel_dest),
        estructuras_nm=(nm,),
    )
    validador = ValidadorDiagramaGenerable()
    resultado = validador.validar(diag)
    assert resultado.valido
    assert len(resultado.errores_bloqueantes) == 0


def test_validador_estructura_nm_clase_intermedia_inexistente_falla():
    id_diag = uuid4()
    id_orig = uuid4()
    clase_orig = ClaseGenerable(id=id_orig, id_diagrama=id_diag, nombre="Estudiante", posicion_x=0, posicion_y=0, ancho=200, atributos=(_crear_atributo(id_orig, "id", "bigint", pk=True),))
    id_dest = uuid4()
    clase_dest = ClaseGenerable(id=id_dest, id_diagrama=id_diag, nombre="Curso", posicion_x=400, posicion_y=0, ancho=200, atributos=(_crear_atributo(id_dest, "id", "bigint", pk=True),))

    nm = EstructuraRelacionNmGenerable(
        id=uuid4(), id_diagrama=id_diag, id_clase_origen=id_orig, id_clase_destino=id_dest,
        id_clase_intermedia=uuid4(), id_relacion_origen=uuid4(), id_relacion_destino=uuid4(),
    )

    diag = DiagramaGenerable(
        id=id_diag, id_proyecto=uuid4(), nombre="Universidad", numero=1,
        clases=(clase_orig, clase_dest),
        relaciones=(),
        estructuras_nm=(nm,),
    )
    validador = ValidadorDiagramaGenerable()
    resultado = validador.validar(diag)
    assert not resultado.valido
    assert any(e.codigo == "NM_CLASE_INTERMEDIA_INEXISTENTE" for e in resultado.errores_bloqueantes)

