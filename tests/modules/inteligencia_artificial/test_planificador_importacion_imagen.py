from __future__ import annotations

from uuid import uuid4

from app.modules.diagramas.application.queries.dtos import (
    AtributoDTO,
    ClaseDetalleDTO,
    DiagramaDetalleDTO,
)
from app.modules.inteligencia_artificial.application.schemas.diagrama_reconocido_ia import (
    AtributoReconocidoIa,
    ClaseReconocidaIa,
    DiagramaReconocidoIa,
    RelacionReconocidaIa,
)
from app.modules.inteligencia_artificial.application.services.planificador_importacion_imagen import (
    PlanificadorImportacionImagen,
)
from app.modules.inteligencia_artificial.application.services.validador_respuesta_ia import (
    AccionCrearAtributoSchema,
    AccionCrearClaseSchema,
    AccionCrearEstructuraNmSchema,
    AccionCrearRelacionSchema,
)


def test_planificador_diagrama_vacio():
    diag_rec = DiagramaReconocidoIa(
        clases=[
            ClaseReconocidaIa(
                referencia_semantica="ref_user",
                nombre="Usuario",
                atributos=[
                    AtributoReconocidoIa(nombre="id", tipo_detectado="integer", es_pk=True),
                    AtributoReconocidoIa(nombre="email", tipo_detectado="varchar", es_pk=False),
                ],
            ),
            ClaseReconocidaIa(
                referencia_semantica="ref_post",
                nombre="Post",
                atributos=[
                    AtributoReconocidoIa(nombre="id", tipo_detectado="integer", es_pk=True),
                    AtributoReconocidoIa(nombre="titulo", tipo_detectado="varchar", es_pk=False),
                ],
            ),
        ],
        relaciones=[
            RelacionReconocidaIa(
                origen_ref="ref_user",
                destino_ref="ref_post",
                tipo="asociacion",
                cardinalidad_origen="1",
                cardinalidad_destino="0..*",
                nombre="publica",
            )
        ],
    )

    posiciones = {
        "ref_user": (100, 100),
        "ref_post": (450, 100),
    }

    plan = PlanificadorImportacionImagen.construir_plan(
        diagrama_reconocido=diag_rec,
        diagrama_existente=None,
        posiciones_layout=posiciones,
    )

    assert len(plan.clases_reutilizadas) == 0
    assert len(plan.clases_creadas_referencias) == 2

    # Verificar orden de acciones: Clases -> Atributos -> Relaciones
    clases = [a for a in plan.acciones if isinstance(a, AccionCrearClaseSchema)]
    atributos = [a for a in plan.acciones if isinstance(a, AccionCrearAtributoSchema)]
    relaciones = [a for a in plan.acciones if isinstance(a, AccionCrearRelacionSchema)]

    assert len(clases) == 2
    assert len(atributos) == 2  # email y titulo (los 'id' son creados por defecto con la clase)
    assert len(relaciones) == 1

    # Verificar que las clases van antes que los atributos en la lista
    assert isinstance(plan.acciones[0], AccionCrearClaseSchema)
    assert isinstance(plan.acciones[1], AccionCrearClaseSchema)


def test_planificador_reconciliacion_clase_existente_exacta():
    diag_id = uuid4()
    clase_ex_id = uuid4()
    clase_existente = ClaseDetalleDTO(
        id=clase_ex_id,
        id_diagrama=diag_id,
        nombre="Usuario",
        posicion_x=100.0,
        posicion_y=100.0,
        ancho=250.0,
        atributos=(
            AtributoDTO(
                id=uuid4(),
                id_clase=clase_ex_id,
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

    diag_existente = DiagramaDetalleDTO(
        id=diag_id,
        id_proyecto=uuid4(),
        nombre="Diag",
        numero=1,
        clases=(clase_existente,),
        relaciones=(),
        estructuras_nm=(),
    )

    diag_rec = DiagramaReconocidoIa(
        clases=[
            ClaseReconocidaIa(
                referencia_semantica="ref_u",
                nombre="usuario",  # case-insensitive match
                atributos=[
                    AtributoReconocidoIa(nombre="telefono", tipo_detectado="varchar"),
                ],
            ),
            ClaseReconocidaIa(
                referencia_semantica="ref_p",
                nombre="Perfil",
                atributos=[
                    AtributoReconocidoIa(nombre="biografia", tipo_detectado="text"),
                ],
            ),
        ],
        relaciones=[
            RelacionReconocidaIa(
                origen_ref="ref_u",
                destino_ref="ref_p",
                tipo="asociacion",
                cardinalidad_origen="1",
                cardinalidad_destino="1",
            )
        ],
    )

    plan = PlanificadorImportacionImagen.construir_plan(
        diagrama_reconocido=diag_rec,
        diagrama_existente=diag_existente,
        posiciones_layout={"ref_p": (450, 100)},
    )

    # Debe reutilizar 'Usuario'
    assert "Usuario" in plan.clases_reutilizadas
    assert plan.clases_existentes_mapeo["ref_u"] == clase_ex_id

    # No debe crear clase para Usuario, solo para Perfil
    clases_a_crear = [a for a in plan.acciones if isinstance(a, AccionCrearClaseSchema)]
    assert len(clases_a_crear) == 1
    assert clases_a_crear[0].nombre == "Perfil"

    # Atributo telefono de la clase existente es reconciliado y agregado para completar la entidad
    attrs_creados = [a for a in plan.acciones if isinstance(a, AccionCrearAtributoSchema)]
    assert any(a.nombre == "telefono" and a.clase_referencia == "ref_u" for a in attrs_creados)
    assert len(plan.atributos_omitidos) == 0


def test_planificador_relacion_nm():
    diag_rec = DiagramaReconocidoIa(
        clases=[
            ClaseReconocidaIa(
                referencia_semantica="ref_est",
                nombre="Estudiante",
                atributos=[AtributoReconocidoIa(nombre="id", es_pk=True)],
            ),
            ClaseReconocidaIa(
                referencia_semantica="ref_cur",
                nombre="Curso",
                atributos=[AtributoReconocidoIa(nombre="id", es_pk=True)],
            ),
        ],
        relaciones=[
            RelacionReconocidaIa(
                origen_ref="ref_est",
                destino_ref="ref_cur",
                tipo="asociacion",
                cardinalidad_origen="0..*",
                cardinalidad_destino="0..*",
                nombre="inscripcion",
                es_nm=True,
            )
        ],
    )

    plan = PlanificadorImportacionImagen.construir_plan(
        diagrama_reconocido=diag_rec,
        diagrama_existente=None,
        posiciones_layout={"ref_est": (100, 100), "ref_cur": (500, 100)},
    )

    acciones_nm = [a for a in plan.acciones if isinstance(a, AccionCrearEstructuraNmSchema)]
    assert len(acciones_nm) == 1
    assert acciones_nm[0].clase_origen_referencia == "ref_est"
    assert acciones_nm[0].clase_destino_referencia == "ref_cur"
    assert acciones_nm[0].nombre_intermedia == "inscripcion"


def test_planificador_relacion_recursiva():
    diag_rec = DiagramaReconocidoIa(
        clases=[
            ClaseReconocidaIa(
                referencia_semantica="ref_emp",
                nombre="Empleado",
                atributos=[AtributoReconocidoIa(nombre="id", es_pk=True)],
            ),
        ],
        relaciones=[
            RelacionReconocidaIa(
                origen_ref="ref_emp",
                destino_ref="ref_emp",
                tipo="asociacion",
                cardinalidad_origen="1",
                cardinalidad_destino="0..*",
                nombre="supervisa",
                es_recursiva=True,
            )
        ],
    )

    plan = PlanificadorImportacionImagen.construir_plan(
        diagrama_reconocido=diag_rec,
        diagrama_existente=None,
        posiciones_layout={"ref_emp": (100, 100)},
    )

    relaciones = [a for a in plan.acciones if isinstance(a, AccionCrearRelacionSchema)]
    assert len(relaciones) == 1
    assert relaciones[0].clase_origen_referencia == "ref_emp"
    assert relaciones[0].clase_destino_referencia == "ref_emp"
    assert relaciones[0].cardinalidad_origen == "1"
    assert relaciones[0].cardinalidad_destino == "0..*"
    assert relaciones[0].nombre == "supervisa"


def test_planificador_fk_explicita_1_a_n_excluye_atributo_manual():
    diag_rec = DiagramaReconocidoIa(
        clases=[
            ClaseReconocidaIa(
                referencia_semantica="ref_cli",
                nombre="Cliente",
                atributos=[AtributoReconocidoIa(nombre="id", tipo_detectado="integer", es_pk=True)],
            ),
            ClaseReconocidaIa(
                referencia_semantica="ref_ped",
                nombre="Pedido",
                atributos=[
                    AtributoReconocidoIa(nombre="id", tipo_detectado="integer", es_pk=True),
                    AtributoReconocidoIa(
                        nombre="cliente_id",
                        tipo_detectado="integer",
                        es_pk=False,
                        es_fk=True,
                        fk_destino_ref="ref_cli",
                    ),
                    AtributoReconocidoIa(nombre="total", tipo_detectado="decimal", es_pk=False),
                ],
            ),
        ],
        relaciones=[
            RelacionReconocidaIa(
                origen_ref="ref_cli",
                destino_ref="ref_ped",
                tipo="asociacion",
                cardinalidad_origen="1",
                cardinalidad_destino="0..*",
                nombre="realiza",
            )
        ],
    )

    plan = PlanificadorImportacionImagen.construir_plan(
        diagrama_reconocido=diag_rec,
        diagrama_existente=None,
        posiciones_layout={"ref_cli": (100, 100), "ref_ped": (450, 100)},
    )

    atributos_creados = [a for a in plan.acciones if isinstance(a, AccionCrearAtributoSchema)]
    relaciones_creadas = [a for a in plan.acciones if isinstance(a, AccionCrearRelacionSchema)]

    # 'total' debe crearse, pero 'cliente_id' debe quedar excluido de creación manual
    nombres_attrs = [a.nombre for a in atributos_creados]
    assert "total" in nombres_attrs
    assert "cliente_id" not in nombres_attrs

    # La relación debe llevar nombre_fk='cliente_id' y clase_fk_referencia='ref_ped'
    assert len(relaciones_creadas) == 1
    assert relaciones_creadas[0].nombre_fk == "cliente_id"
    assert relaciones_creadas[0].clase_fk_referencia == "ref_ped"


def test_planificador_fk_explicita_1_a_1_sin_duplicados():
    diag_rec = DiagramaReconocidoIa(
        clases=[
            ClaseReconocidaIa(
                referencia_semantica="ref_usr",
                nombre="Usuario",
                atributos=[AtributoReconocidoIa(nombre="id", es_pk=True)],
            ),
            ClaseReconocidaIa(
                referencia_semantica="ref_per",
                nombre="Perfil",
                atributos=[
                    AtributoReconocidoIa(nombre="id", es_pk=True),
                    AtributoReconocidoIa(nombre="usuario_id", es_fk=True),
                    AtributoReconocidoIa(nombre="bio", tipo_detectado="text"),
                ],
            ),
        ],
        relaciones=[
            RelacionReconocidaIa(
                origen_ref="ref_usr",
                destino_ref="ref_per",
                tipo="asociacion",
                cardinalidad_origen="1",
                cardinalidad_destino="1",
            )
        ],
    )

    plan = PlanificadorImportacionImagen.construir_plan(
        diagrama_reconocido=diag_rec,
        diagrama_existente=None,
        posiciones_layout={"ref_usr": (100, 100), "ref_per": (450, 100)},
    )

    attrs = [a for a in plan.acciones if isinstance(a, AccionCrearAtributoSchema)]
    rels = [a for a in plan.acciones if isinstance(a, AccionCrearRelacionSchema)]

    nombres = [a.nombre for a in attrs]
    assert "usuario_id" not in nombres
    assert "bio" in nombres

    assert len(rels) == 1
    assert rels[0].nombre_fk == "usuario_id"
    assert rels[0].clase_fk_referencia == "ref_per"


def test_planificador_atributo_cliente_id_sin_relacion_permanece_manual():
    diag_rec = DiagramaReconocidoIa(
        clases=[
            ClaseReconocidaIa(
                referencia_semantica="ref_aud",
                nombre="Auditoria",
                atributos=[
                    AtributoReconocidoIa(nombre="id", es_pk=True),
                    AtributoReconocidoIa(nombre="cliente_id", es_pk=False, es_fk=False),
                    AtributoReconocidoIa(nombre="evento", tipo_detectado="varchar"),
                ],
            ),
        ],
        relaciones=[],
    )

    plan = PlanificadorImportacionImagen.construir_plan(
        diagrama_reconocido=diag_rec,
        diagrama_existente=None,
        posiciones_layout={"ref_aud": (100, 100)},
    )

    attrs = [a for a in plan.acciones if isinstance(a, AccionCrearAtributoSchema)]
    nombres = [a.nombre for a in attrs]
    assert "cliente_id" in nombres
    assert "evento" in nombres


def test_planificador_fk_marcada_sin_relacion_no_inventa_destino():
    diag_rec = DiagramaReconocidoIa(
        clases=[
            ClaseReconocidaIa(
                referencia_semantica="ref_aud",
                nombre="Auditoria",
                atributos=[
                    AtributoReconocidoIa(nombre="id", es_pk=True),
                    AtributoReconocidoIa(nombre="empresa_externa_id", es_pk=False, es_fk=True),
                ],
            ),
        ],
        relaciones=[],
    )

    plan = PlanificadorImportacionImagen.construir_plan(
        diagrama_reconocido=diag_rec,
        diagrama_existente=None,
        posiciones_layout={"ref_aud": (100, 100)},
    )

    attrs = [a for a in plan.acciones if isinstance(a, AccionCrearAtributoSchema)]
    nombres = [a.nombre for a in attrs]
    # Al no haber relación, no se inventa destino y se crea como atributo manual
    assert "empresa_externa_id" in nombres


def test_planificador_recursividad_con_fk_supervisor():
    diag_rec = DiagramaReconocidoIa(
        clases=[
            ClaseReconocidaIa(
                referencia_semantica="ref_emp",
                nombre="Empleado",
                atributos=[
                    AtributoReconocidoIa(nombre="id", es_pk=True),
                    AtributoReconocidoIa(nombre="supervisor_id", es_fk=True),
                    AtributoReconocidoIa(nombre="cargo", tipo_detectado="varchar"),
                ],
            ),
        ],
        relaciones=[
            RelacionReconocidaIa(
                origen_ref="ref_emp",
                destino_ref="ref_emp",
                tipo="asociacion",
                cardinalidad_origen="1",
                cardinalidad_destino="0..*",
                nombre="supervisa",
                es_recursiva=True,
            )
        ],
    )

    plan = PlanificadorImportacionImagen.construir_plan(
        diagrama_reconocido=diag_rec,
        diagrama_existente=None,
        posiciones_layout={"ref_emp": (100, 100)},
    )

    attrs = [a for a in plan.acciones if isinstance(a, AccionCrearAtributoSchema)]
    rels = [a for a in plan.acciones if isinstance(a, AccionCrearRelacionSchema)]

    nombres = [a.nombre for a in attrs]
    assert "supervisor_id" not in nombres
    assert "cargo" in nombres

    assert len(rels) == 1
    assert rels[0].nombre_fk == "supervisor_id"
    assert rels[0].clase_fk_referencia == "ref_emp"


def test_planificador_multiples_fks_en_misma_clase():
    diag_rec = DiagramaReconocidoIa(
        clases=[
            ClaseReconocidaIa(
                referencia_semantica="ref_cli",
                nombre="Cliente",
                atributos=[AtributoReconocidoIa(nombre="id", es_pk=True)],
            ),
            ClaseReconocidaIa(
                referencia_semantica="ref_vend",
                nombre="Vendedor",
                atributos=[AtributoReconocidoIa(nombre="id", es_pk=True)],
            ),
            ClaseReconocidaIa(
                referencia_semantica="ref_suc",
                nombre="Sucursal",
                atributos=[AtributoReconocidoIa(nombre="id", es_pk=True)],
            ),
            ClaseReconocidaIa(
                referencia_semantica="ref_fac",
                nombre="Factura",
                atributos=[
                    AtributoReconocidoIa(nombre="id", es_pk=True),
                    AtributoReconocidoIa(nombre="cliente_id", es_fk=True),
                    AtributoReconocidoIa(nombre="vendedor_id", es_fk=True),
                    AtributoReconocidoIa(nombre="sucursal_id", es_fk=True),
                    AtributoReconocidoIa(nombre="monto", tipo_detectado="decimal"),
                ],
            ),
        ],
        relaciones=[
            RelacionReconocidaIa(
                origen_ref="ref_cli",
                destino_ref="ref_fac",
                tipo="asociacion",
                cardinalidad_origen="1",
                cardinalidad_destino="0..*",
            ),
            RelacionReconocidaIa(
                origen_ref="ref_vend",
                destino_ref="ref_fac",
                tipo="asociacion",
                cardinalidad_origen="1",
                cardinalidad_destino="0..*",
            ),
            RelacionReconocidaIa(
                origen_ref="ref_suc",
                destino_ref="ref_fac",
                tipo="asociacion",
                cardinalidad_origen="1",
                cardinalidad_destino="0..*",
            ),
        ],
    )

    plan = PlanificadorImportacionImagen.construir_plan(
        diagrama_reconocido=diag_rec,
        diagrama_existente=None,
        posiciones_layout={
            "ref_cli": (100, 100),
            "ref_vend": (100, 300),
            "ref_suc": (100, 500),
            "ref_fac": (500, 300),
        },
    )

    attrs = [a for a in plan.acciones if isinstance(a, AccionCrearAtributoSchema)]
    rels = [a for a in plan.acciones if isinstance(a, AccionCrearRelacionSchema)]

    nombres = [a.nombre for a in attrs]
    assert "cliente_id" not in nombres
    assert "vendedor_id" not in nombres
    assert "sucursal_id" not in nombres
    assert "monto" in nombres

    assert len(rels) == 3
    nombres_fks = {r.nombre_fk for r in rels}
    assert nombres_fks == {"cliente_id", "vendedor_id", "sucursal_id"}


def test_planificador_tipos_relacion_herencia_y_composicion():
    diag_rec = DiagramaReconocidoIa(
        clases=[
            ClaseReconocidaIa(
                referencia_semantica="ref_persona",
                nombre="Persona",
                atributos=[AtributoReconocidoIa(nombre="id", es_pk=True)],
            ),
            ClaseReconocidaIa(
                referencia_semantica="ref_estudiante",
                nombre="Estudiante",
                atributos=[
                    AtributoReconocidoIa(nombre="id", es_pk=True),
                    AtributoReconocidoIa(nombre="persona_id", es_fk=True),
                    AtributoReconocidoIa(nombre="matricula", tipo_detectado="varchar"),
                ],
            ),
        ],
        relaciones=[
            RelacionReconocidaIa(
                origen_ref="ref_estudiante",
                destino_ref="ref_persona",
                tipo="herencia",
                cardinalidad_origen="1",
                cardinalidad_destino="1",
            ),
        ],
    )

    plan = PlanificadorImportacionImagen.construir_plan(
        diagrama_reconocido=diag_rec,
        diagrama_existente=None,
        posiciones_layout={"ref_persona": (100, 100), "ref_estudiante": (500, 100)},
    )

    attrs = [a for a in plan.acciones if isinstance(a, AccionCrearAtributoSchema)]
    rels = [a for a in plan.acciones if isinstance(a, AccionCrearRelacionSchema)]

    nombres = [a.nombre for a in attrs]
    assert "persona_id" not in nombres
    assert "matricula" in nombres

    assert len(rels) == 1
    assert rels[0].tipo_relacion == "herencia"
    assert rels[0].nombre_fk == "persona_id"
    assert rels[0].clase_fk_referencia == "ref_estudiante"


def test_planificador_estructura_ya_existente_omite_relaciones():
    diag_id = uuid4()
    c1_id = uuid4()
    c2_id = uuid4()
    r_id = uuid4()

    from app.modules.diagramas.application.queries.dtos import (
        RelacionDetalleDTO,
    )

    diag_existente = DiagramaDetalleDTO(
        id=diag_id,
        id_proyecto=uuid4(),
        nombre="Diag",
        numero=1,
        clases=(
            ClaseDetalleDTO(id=c1_id, id_diagrama=diag_id, nombre="Cliente", posicion_x=100.0, posicion_y=100.0, ancho=250.0, atributos=()),
            ClaseDetalleDTO(id=c2_id, id_diagrama=diag_id, nombre="Pedido", posicion_x=450.0, posicion_y=100.0, ancho=250.0, atributos=()),
        ),
        relaciones=(
            RelacionDetalleDTO(
                id=r_id,
                id_diagrama=diag_id,
                id_clase_origen=c1_id,
                id_clase_destino=c2_id,
                tipo_relacion="asociacion",
                cardinalidad_origen="1",
                cardinalidad_destino="0..*",
                conector_origen="right",
                conector_destino="left",
            ),
        ),
        estructuras_nm=(),
    )

    diag_rec = DiagramaReconocidoIa(
        clases=[
            ClaseReconocidaIa(referencia_semantica="ref_cli", nombre="Cliente", atributos=[AtributoReconocidoIa(nombre="id", es_pk=True)]),
            ClaseReconocidaIa(referencia_semantica="ref_ped", nombre="Pedido", atributos=[AtributoReconocidoIa(nombre="id", es_pk=True)]),
        ],
        relaciones=[
            RelacionReconocidaIa(
                origen_ref="ref_cli",
                destino_ref="ref_ped",
                tipo="asociacion",
                cardinalidad_origen="1",
                cardinalidad_destino="0..*",
            )
        ],
    )

    plan = PlanificadorImportacionImagen.construir_plan(
        diagrama_reconocido=diag_rec,
        diagrama_existente=diag_existente,
        posiciones_layout={},
    )

    # Ambas clases reutilizadas
    assert len(plan.clases_reutilizadas) == 2
    # Cero clases nuevas, cero atributos nuevos, cero relaciones nuevas
    assert len(plan.acciones) == 0
    assert any("ya existe en el diagrama" in w for w in plan.advertencias)


def test_planificador_nm_intermedia_visible_con_atributo_extra_sin_segunda_clase():
    diag_rec = DiagramaReconocidoIa(
        clases=[
            ClaseReconocidaIa(
                referencia_semantica="ref_prod",
                nombre="Producto",
                atributos=[AtributoReconocidoIa(nombre="id", tipo_detectado="integer", es_pk=True)],
                posicion_relativa_x=0.1,
                posicion_relativa_y=0.2,
            ),
            ClaseReconocidaIa(
                referencia_semantica="ref_venta",
                nombre="Venta",
                atributos=[AtributoReconocidoIa(nombre="id", tipo_detectado="integer", es_pk=True)],
                posicion_relativa_x=0.9,
                posicion_relativa_y=0.2,
            ),
            ClaseReconocidaIa(
                referencia_semantica="ref_pv",
                nombre="ProductoVenta",
                atributos=[
                    AtributoReconocidoIa(nombre="id", tipo_detectado="integer", es_pk=True),
                    AtributoReconocidoIa(nombre="id-producto", tipo_detectado="integer", es_fk=True, fk_destino_ref="ref_prod"),
                    AtributoReconocidoIa(nombre="id-venta", tipo_detectado="integer", es_fk=True, fk_destino_ref="ref_venta"),
                    AtributoReconocidoIa(nombre="cantidad", tipo_detectado="integer", es_pk=False, es_fk=False),
                ],
                posicion_relativa_x=0.5,
                posicion_relativa_y=0.5,
            ),
        ],
        relaciones=[
            RelacionReconocidaIa(
                origen_ref="ref_prod",
                destino_ref="ref_venta",
                tipo="asociacion",
                cardinalidad_origen="0..*",
                cardinalidad_destino="0..*",
                nombre="contiene",
                es_nm=True,
            )
        ],
    )

    posiciones = {
        "ref_prod": (100, 100),
        "ref_venta": (700, 100),
        "ref_pv": (400, 300),
    }

    plan = PlanificadorImportacionImagen.construir_plan(
        diagrama_reconocido=diag_rec,
        diagrama_existente=None,
        posiciones_layout=posiciones,
    )

    # 1. Clases creadas en plan.acciones: SOLO Producto y Venta (ProductoVenta se crea vía CrearEstructuraRelacionNmUseCase)
    clases_creadas = [a for a in plan.acciones if isinstance(a, AccionCrearClaseSchema)]
    assert len(clases_creadas) == 2
    nombres_clases = [c.nombre for c in clases_creadas]
    assert "Producto" in nombres_clases
    assert "Venta" in nombres_clases
    assert "ProductoVenta" not in nombres_clases  # CERO segunda clase regular

    # 2. AccionCrearEstructuraNmSchema lleva el nombre de la intermedia explícita y su referencia
    acciones_nm = [a for a in plan.acciones if isinstance(a, AccionCrearEstructuraNmSchema)]
    assert len(acciones_nm) == 1
    assert acciones_nm[0].nombre_intermedia == "ProductoVenta"
    assert acciones_nm[0].referencia_intermedia == "ref_pv"
    assert acciones_nm[0].clase_origen_referencia == "ref_prod"
    assert acciones_nm[0].clase_destino_referencia == "ref_venta"
    assert acciones_nm[0].posicion.x == 400.0
    assert acciones_nm[0].posicion.y == 300.0

    # 3. Atributos: Solo 'cantidad' para la intermedia; 'id-producto' e 'id-venta' NO se crean como atributos manuales
    atributos_creados = [a for a in plan.acciones if isinstance(a, AccionCrearAtributoSchema)]
    assert len(atributos_creados) == 1
    assert atributos_creados[0].clase_referencia == "ref_pv"
    assert atributos_creados[0].nombre == "cantidad"
    assert atributos_creados[0].tipo_dato == "integer"

    # 4. Orden estricto: Clases -> NM -> Atributos
    assert isinstance(plan.acciones[0], AccionCrearClaseSchema)
    assert isinstance(plan.acciones[1], AccionCrearClaseSchema)
    assert isinstance(plan.acciones[2], AccionCrearEstructuraNmSchema)
    assert isinstance(plan.acciones[3], AccionCrearAtributoSchema)


def test_planificador_nm_nombre_distinto_de_intermedia():
    diag_rec = DiagramaReconocidoIa(
        clases=[
            ClaseReconocidaIa(
                referencia_semantica="ref_est",
                nombre="Estudiante",
                atributos=[AtributoReconocidoIa(nombre="id", es_pk=True)],
            ),
            ClaseReconocidaIa(
                referencia_semantica="ref_cur",
                nombre="Curso",
                atributos=[AtributoReconocidoIa(nombre="id", es_pk=True)],
            ),
            ClaseReconocidaIa(
                referencia_semantica="ref_ins",
                nombre="Inscripcion",  # Nombre totalmente distinto del patrón A_B
                atributos=[
                    AtributoReconocidoIa(nombre="id", es_pk=True),
                    AtributoReconocidoIa(nombre="estudiante_id", es_fk=True, fk_destino_ref="ref_est"),
                    AtributoReconocidoIa(nombre="curso_id", es_fk=True, fk_destino_ref="ref_cur"),
                    AtributoReconocidoIa(nombre="fecha_inscripcion", tipo_detectado="date"),
                    AtributoReconocidoIa(nombre="nota_final", tipo_detectado="decimal"),
                ],
            ),
        ],
        relaciones=[
            RelacionReconocidaIa(
                origen_ref="ref_est",
                destino_ref="ref_cur",
                tipo="asociacion",
                cardinalidad_origen="0..*",
                cardinalidad_destino="0..*",
                nombre="matriculado",
                es_nm=True,
            )
        ],
    )

    plan = PlanificadorImportacionImagen.construir_plan(
        diagrama_reconocido=diag_rec,
        diagrama_existente=None,
        posiciones_layout={"ref_est": (100, 100), "ref_cur": (600, 100), "ref_ins": (350, 250)},
    )

    # Identificación estructural conjunta detecta 'Inscripcion' como intermedia
    clases_creadas = [a for a in plan.acciones if isinstance(a, AccionCrearClaseSchema)]
    assert len(clases_creadas) == 2
    assert "Inscripcion" not in [c.nombre for c in clases_creadas]

    acciones_nm = [a for a in plan.acciones if isinstance(a, AccionCrearEstructuraNmSchema)]
    assert len(acciones_nm) == 1
    assert acciones_nm[0].nombre_intermedia == "Inscripcion"
    assert acciones_nm[0].referencia_intermedia == "ref_ins"

    atributos_creados = [a for a in plan.acciones if isinstance(a, AccionCrearAtributoSchema)]
    nombres_attrs = [a.nombre for a in atributos_creados]
    assert "fecha_inscripcion" in nombres_attrs
    assert "nota_final" in nombres_attrs
    assert "estudiante_id" not in nombres_attrs
    assert "curso_id" not in nombres_attrs


def test_planificador_nm_fks_visibles_no_duplicadas():
    diag_rec = DiagramaReconocidoIa(
        clases=[
            ClaseReconocidaIa(
                referencia_semantica="ref_med",
                nombre="Medico",
                atributos=[AtributoReconocidoIa(nombre="id", es_pk=True)],
            ),
            ClaseReconocidaIa(
                referencia_semantica="ref_pac",
                nombre="Paciente",
                atributos=[AtributoReconocidoIa(nombre="id", es_pk=True)],
            ),
            ClaseReconocidaIa(
                referencia_semantica="ref_con",
                nombre="Consulta",
                atributos=[
                    AtributoReconocidoIa(nombre="id", es_pk=True),
                    AtributoReconocidoIa(nombre="medico_id", es_fk=True),
                    AtributoReconocidoIa(nombre="paciente_id", es_fk=True),
                ],
            ),
        ],
        relaciones=[
            RelacionReconocidaIa(
                origen_ref="ref_med",
                destino_ref="ref_pac",
                tipo="asociacion",
                cardinalidad_origen="0..*",
                cardinalidad_destino="0..*",
                es_nm=True,
            )
        ],
    )

    plan = PlanificadorImportacionImagen.construir_plan(
        diagrama_reconocido=diag_rec,
        diagrama_existente=None,
        posiciones_layout={"ref_med": (100, 100), "ref_pac": (600, 100), "ref_con": (350, 250)},
    )

    # Solo las dos clases de los extremos se crean como clases regulares
    clases = [a for a in plan.acciones if isinstance(a, AccionCrearClaseSchema)]
    assert len(clases) == 2

    # Cero atributos manuales creados para Consulta ya que solo tenía PK y 2 FKs
    attrs = [a for a in plan.acciones if isinstance(a, AccionCrearAtributoSchema)]
    assert len(attrs) == 0

    # Estructura N:M creada con nombre 'Consulta'
    acciones_nm = [a for a in plan.acciones if isinstance(a, AccionCrearEstructuraNmSchema)]
    assert len(acciones_nm) == 1
    assert acciones_nm[0].nombre_intermedia == "Consulta"


def test_planificador_nm_dos_intermedias_ambiguas_no_escoge_arbitrariamente():
    diag_rec = DiagramaReconocidoIa(
        clases=[
            ClaseReconocidaIa(
                referencia_semantica="ref_p",
                nombre="Producto",
                atributos=[AtributoReconocidoIa(nombre="id", es_pk=True)],
                posicion_relativa_x=0.1,
                posicion_relativa_y=0.2,
            ),
            ClaseReconocidaIa(
                referencia_semantica="ref_v",
                nombre="Venta",
                atributos=[AtributoReconocidoIa(nombre="id", es_pk=True)],
                posicion_relativa_x=0.9,
                posicion_relativa_y=0.2,
            ),
            ClaseReconocidaIa(
                referencia_semantica="ref_det_a",
                nombre="DetalleA",
                atributos=[
                    AtributoReconocidoIa(nombre="id", es_pk=True),
                    AtributoReconocidoIa(nombre="id_producto", es_fk=True),
                    AtributoReconocidoIa(nombre="id_venta", es_fk=True),
                ],
                posicion_relativa_x=0.5,
                posicion_relativa_y=0.4,
            ),
            ClaseReconocidaIa(
                referencia_semantica="ref_det_b",
                nombre="DetalleB",
                atributos=[
                    AtributoReconocidoIa(nombre="id", es_pk=True),
                    AtributoReconocidoIa(nombre="id_producto", es_fk=True),
                    AtributoReconocidoIa(nombre="id_venta", es_fk=True),
                ],
                posicion_relativa_x=0.5,
                posicion_relativa_y=0.6,
            ),
        ],
        relaciones=[
            RelacionReconocidaIa(
                origen_ref="ref_p",
                destino_ref="ref_v",
                tipo="asociacion",
                cardinalidad_origen="0..*",
                cardinalidad_destino="0..*",
                nombre="venta_prod",
                es_nm=True,
            )
        ],
    )

    plan = PlanificadorImportacionImagen.construir_plan(
        diagrama_reconocido=diag_rec,
        diagrama_existente=None,
        posiciones_layout={
            "ref_p": (100, 100),
            "ref_v": (700, 100),
            "ref_det_a": (400, 200),
            "ref_det_b": (400, 400),
        },
    )

    # Debe reportar advertencia de ambigüedad
    assert any("Ambigüedad detectada en relación N:M" in w for w in plan.advertencias)
    assert any("DetalleA" in w and "DetalleB" in w for w in plan.advertencias)

    # No debe elegir arbitrariamente una como intermedia de la N:M
    acciones_nm = [a for a in plan.acciones if isinstance(a, AccionCrearEstructuraNmSchema)]
    assert len(acciones_nm) == 1
    # La N:M no vincula referencia_intermedia ni sustituye su nombre por DetalleA/DetalleB
    assert acciones_nm[0].referencia_intermedia is None

    # Ambas clases candidatas se preservan como regulares para evitar pérdida de datos
    clases_creadas = [a for a in plan.acciones if isinstance(a, AccionCrearClaseSchema)]
    assert len(clases_creadas) == 4


def test_planificador_nm_ya_existente_en_diagrama_omite_duplicados():
    diag_id = uuid4()
    c_prod_id = uuid4()
    c_venta_id = uuid4()
    c_inter_id = uuid4()
    nm_id = uuid4()

    from app.modules.diagramas.application.queries.dtos import (
        EstructuraRelacionNmDTO,
    )

    diag_existente = DiagramaDetalleDTO(
        id=diag_id,
        id_proyecto=uuid4(),
        nombre="Diag",
        numero=1,
        clases=(
            ClaseDetalleDTO(id=c_prod_id, id_diagrama=diag_id, nombre="Producto", posicion_x=100.0, posicion_y=100.0, ancho=250.0, atributos=()),
            ClaseDetalleDTO(id=c_venta_id, id_diagrama=diag_id, nombre="Venta", posicion_x=700.0, posicion_y=100.0, ancho=250.0, atributos=()),
            ClaseDetalleDTO(id=c_inter_id, id_diagrama=diag_id, nombre="Producto_Venta", posicion_x=400.0, posicion_y=300.0, ancho=250.0, atributos=()),
        ),
        relaciones=(),
        estructuras_nm=(
            EstructuraRelacionNmDTO(
                id=nm_id,
                id_diagrama=diag_id,
                id_clase_origen=c_prod_id,
                id_clase_destino=c_venta_id,
                id_clase_intermedia=c_inter_id,
                id_relacion_origen=uuid4(),
                id_relacion_destino=uuid4(),
            ),
        ),
    )

    diag_rec = DiagramaReconocidoIa(
        clases=[
            ClaseReconocidaIa(
                referencia_semantica="ref_prod",
                nombre="Producto",
                atributos=[AtributoReconocidoIa(nombre="id", es_pk=True)],
            ),
            ClaseReconocidaIa(
                referencia_semantica="ref_venta",
                nombre="Venta",
                atributos=[AtributoReconocidoIa(nombre="id", es_pk=True)],
            ),
            ClaseReconocidaIa(
                referencia_semantica="ref_pv",
                nombre="ProductoVenta",
                atributos=[
                    AtributoReconocidoIa(nombre="id", es_pk=True),
                    AtributoReconocidoIa(nombre="id_producto", es_fk=True),
                    AtributoReconocidoIa(nombre="id_venta", es_fk=True),
                    AtributoReconocidoIa(nombre="cantidad", tipo_detectado="integer"),
                ],
            ),
        ],
        relaciones=[
            RelacionReconocidaIa(
                origen_ref="ref_prod",
                destino_ref="ref_venta",
                tipo="asociacion",
                cardinalidad_origen="0..*",
                cardinalidad_destino="0..*",
                es_nm=True,
            )
        ],
    )

    plan = PlanificadorImportacionImagen.construir_plan(
        diagrama_reconocido=diag_rec,
        diagrama_existente=diag_existente,
        posiciones_layout={},
    )

    # Estructura N:M omitida
    acciones_nm = [a for a in plan.acciones if isinstance(a, AccionCrearEstructuraNmSchema)]
    assert len(acciones_nm) == 0
    assert any("Estructura N:M entre 'producto' y 'venta' ya existe" in w for w in plan.advertencias)

    # Clase intermedia mapeada a la existente, cero clases nuevas
    clases_creadas = [a for a in plan.acciones if isinstance(a, AccionCrearClaseSchema)]
    assert len(clases_creadas) == 0
    assert plan.clases_existentes_mapeo["ref_pv"] == c_inter_id


def test_planificador_nm_reconocida_como_1_a_n_se_promueve_a_nm():
    """Verifica que si Gemini clasifica la relación como 1:N (cardinalidad '1' y '0..*', es_nm=False),
    pero existe una clase intermedia explícita con FKs a ambos extremos, el planificador la promueva a N:M."""
    diag_rec = DiagramaReconocidoIa(
        clases=[
            ClaseReconocidaIa(
                referencia_semantica="ref_prod",
                nombre="Producto",
                atributos=[AtributoReconocidoIa(nombre="id", es_pk=True)],
            ),
            ClaseReconocidaIa(
                referencia_semantica="ref_venta",
                nombre="Venta",
                atributos=[AtributoReconocidoIa(nombre="id", es_pk=True)],
            ),
            ClaseReconocidaIa(
                referencia_semantica="ref_pv",
                nombre="ProductoVenta",
                atributos=[
                    AtributoReconocidoIa(nombre="id", es_pk=True),
                    AtributoReconocidoIa(nombre="id_producto", es_fk=True),
                    AtributoReconocidoIa(nombre="id_venta", es_fk=True),
                    AtributoReconocidoIa(nombre="cantidad", tipo_detectado="integer"),
                ],
            ),
        ],
        relaciones=[
            RelacionReconocidaIa(
                origen_ref="ref_prod",
                destino_ref="ref_venta",
                tipo="asociacion",
                cardinalidad_origen="1",
                cardinalidad_destino="0..*",
                es_nm=False,
            )
        ],
    )

    plan = PlanificadorImportacionImagen.construir_plan(
        diagrama_reconocido=diag_rec,
        diagrama_existente=None,
        posiciones_layout={"ref_prod": (100, 100), "ref_venta": (700, 100), "ref_pv": (400, 300)},
    )

    # 1. No debe haber creado relación 1:N en acciones_relaciones
    rels_1n = [a for a in plan.acciones if isinstance(a, AccionCrearRelacionSchema)]
    assert len(rels_1n) == 0

    # 2. Debe haber creado una estructura N:M
    acciones_nm = [a for a in plan.acciones if isinstance(a, AccionCrearEstructuraNmSchema)]
    assert len(acciones_nm) == 1
    assert acciones_nm[0].clase_origen_referencia == "ref_prod"
    assert acciones_nm[0].clase_destino_referencia == "ref_venta"
    assert acciones_nm[0].nombre_intermedia == "ProductoVenta"
    assert acciones_nm[0].referencia_intermedia == "ref_pv"

    # 3. Solo Producto y Venta se crean como clases normales
    clases = [a for a in plan.acciones if isinstance(a, AccionCrearClaseSchema)]
    assert len(clases) == 2
    nombres_clases = {c.nombre for c in clases}
    assert nombres_clases == {"Producto", "Venta"}


def test_planificador_nm_detectada_estructuralmente_sin_relacion_directa():
    """Verifica que si Gemini no emite relación directa A-B pero emite relaciones A->C y B->C
    donde C tiene FKs a A y B, el planificador detecte la estructura N:M y no duplique relaciones 1:N hacia C."""
    diag_rec = DiagramaReconocidoIa(
        clases=[
            ClaseReconocidaIa(
                referencia_semantica="ref_est",
                nombre="Estudiante",
                atributos=[AtributoReconocidoIa(nombre="id", es_pk=True)],
            ),
            ClaseReconocidaIa(
                referencia_semantica="ref_cur",
                nombre="Curso",
                atributos=[AtributoReconocidoIa(nombre="id", es_pk=True)],
            ),
            ClaseReconocidaIa(
                referencia_semantica="ref_mat",
                nombre="Matricula",
                atributos=[
                    AtributoReconocidoIa(nombre="id", es_pk=True),
                    AtributoReconocidoIa(nombre="estudiante_id", es_fk=True),
                    AtributoReconocidoIa(nombre="curso_id", es_fk=True),
                    AtributoReconocidoIa(nombre="fecha", tipo_detectado="date"),
                ],
            ),
        ],
        relaciones=[
            RelacionReconocidaIa(
                origen_ref="ref_est",
                destino_ref="ref_mat",
                tipo="asociacion",
                cardinalidad_origen="1",
                cardinalidad_destino="0..*",
            ),
            RelacionReconocidaIa(
                origen_ref="ref_cur",
                destino_ref="ref_mat",
                tipo="asociacion",
                cardinalidad_origen="1",
                cardinalidad_destino="0..*",
            ),
        ],
    )

    plan = PlanificadorImportacionImagen.construir_plan(
        diagrama_reconocido=diag_rec,
        diagrama_existente=None,
        posiciones_layout={"ref_est": (100, 100), "ref_cur": (700, 100), "ref_mat": (400, 300)},
    )

    # 1. No debe haber relaciones 1:N hacia Matricula
    rels_1n = [a for a in plan.acciones if isinstance(a, AccionCrearRelacionSchema)]
    assert len(rels_1n) == 0

    # 2. Debe haber creado una estructura N:M
    acciones_nm = [a for a in plan.acciones if isinstance(a, AccionCrearEstructuraNmSchema)]
    assert len(acciones_nm) == 1
    assert acciones_nm[0].nombre_intermedia == "Matricula"
    assert acciones_nm[0].referencia_intermedia == "ref_mat"

    # 3. Solo Estudiante y Curso como clases normales
    clases = [a for a in plan.acciones if isinstance(a, AccionCrearClaseSchema)]
    assert len(clases) == 2
    nombres_clases = {c.nombre for c in clases}
    assert nombres_clases == {"Estudiante", "Curso"}


def test_planificador_caso_usuario_producto_venta_hola_agregacion_y_nm():
    """
    Verifica el escenario reportado por el usuario:
    - Producto (id, nombre, precio, imagen)
    - Venta (id, fecha)
    - Hola (id)
    - Producto_Venta (id, producto_id, venta_id, cantidad)
    - Relación N:M entre Producto y Venta mediante Producto_Venta
    - Relación de agregación entre Hola y Venta
    - Comportamiento esperado:
      * Todos los IDs/PKs se ignoran (las clases nacen con su 'id' PK por defecto).
      * Las FKs de Producto_Venta se ignoran (se construyen vía CrearEstructuraNm).
      * Solo 'cantidad' se crea como atributo en Producto_Venta.
      * Producto recibe 'nombre', 'precio', 'imagen'.
      * Venta recibe 'fecha'.
      * Hola no recibe atributos extra.
      * Se planifica CrearRelacion (agregación) entre Hola y Venta.
    """
    diag_rec = DiagramaReconocidoIa(
        clases=[
            ClaseReconocidaIa(
                referencia_semantica="ref_prod",
                nombre="Producto",
                atributos=[
                    AtributoReconocidoIa(nombre="id", tipo_detectado="integer", es_pk=True),
                    AtributoReconocidoIa(nombre="nombre", tipo_detectado="varchar", es_pk=False),
                    AtributoReconocidoIa(nombre="precio", tipo_detectado="decimal", es_pk=False),
                    AtributoReconocidoIa(nombre="imagen", tipo_detectado="varchar", es_pk=False),
                ],
                posicion_relativa_x=0.1,
                posicion_relativa_y=0.2,
            ),
            ClaseReconocidaIa(
                referencia_semantica="ref_venta",
                nombre="Venta",
                atributos=[
                    AtributoReconocidoIa(nombre="id", tipo_detectado="integer", es_pk=True),
                    AtributoReconocidoIa(nombre="fecha", tipo_detectado="timestamp", es_pk=False),
                ],
                posicion_relativa_x=0.8,
                posicion_relativa_y=0.2,
            ),
            ClaseReconocidaIa(
                referencia_semantica="ref_hola",
                nombre="Hola",
                atributos=[
                    AtributoReconocidoIa(nombre="id", tipo_detectado="integer", es_pk=True),
                ],
                posicion_relativa_x=0.8,
                posicion_relativa_y=0.7,
            ),
            ClaseReconocidaIa(
                referencia_semantica="ref_pv",
                nombre="Producto_Venta",
                atributos=[
                    AtributoReconocidoIa(nombre="id", tipo_detectado="integer", es_pk=True),
                    AtributoReconocidoIa(nombre="producto_id", tipo_detectado="integer", es_fk=True, fk_destino_ref="ref_prod"),
                    AtributoReconocidoIa(nombre="venta_id", tipo_detectado="integer", es_fk=True, fk_destino_ref="ref_venta"),
                    AtributoReconocidoIa(nombre="cantidad", tipo_detectado="integer", es_pk=False, es_fk=False),
                ],
                posicion_relativa_x=0.45,
                posicion_relativa_y=0.2,
            ),
        ],
        relaciones=[
            RelacionReconocidaIa(
                origen_ref="ref_prod",
                destino_ref="ref_pv",
                tipo="asociacion",
                cardinalidad_origen="1",
                cardinalidad_destino="0..*",
            ),
            RelacionReconocidaIa(
                origen_ref="ref_venta",
                destino_ref="ref_pv",
                tipo="asociacion",
                cardinalidad_origen="1",
                cardinalidad_destino="0..*",
            ),
            RelacionReconocidaIa(
                origen_ref="ref_hola",
                destino_ref="ref_venta",
                tipo="agregacion",
                cardinalidad_origen="0..*",
                cardinalidad_destino="1",
            ),
        ],
    )

    posiciones = {
        "ref_prod": (100, 100),
        "ref_venta": (700, 100),
        "ref_hola": (700, 400),
        "ref_pv": (400, 100),
    }

    plan = PlanificadorImportacionImagen.construir_plan(
        diagrama_reconocido=diag_rec,
        diagrama_existente=None,
        posiciones_layout=posiciones,
    )

    # 1. Clases creadas: Producto, Venta, Hola (Producto_Venta se crea vía CrearEstructuraNm)
    clases_creadas = [a for a in plan.acciones if isinstance(a, AccionCrearClaseSchema)]
    assert len(clases_creadas) == 3
    nombres_clases = {c.nombre for c in clases_creadas}
    assert nombres_clases == {"Producto", "Venta", "Hola"}

    # 2. Estructura NM creada para Producto_Venta
    acciones_nm = [a for a in plan.acciones if isinstance(a, AccionCrearEstructuraNmSchema)]
    assert len(acciones_nm) == 1
    assert acciones_nm[0].nombre_intermedia == "Producto_Venta"
    assert acciones_nm[0].referencia_intermedia == "ref_pv"

    # 3. Atributos de clases base (Producto: nombre, precio, imagen; Venta: fecha; Hola: ninguno)
    attrs_regulares = [
        a for a in plan.acciones
        if isinstance(a, AccionCrearAtributoSchema) and a.clase_referencia != "ref_pv"
    ]
    assert len(attrs_regulares) == 4
    attrs_prod = {a.nombre for a in attrs_regulares if a.clase_referencia == "ref_prod"}
    assert attrs_prod == {"nombre", "precio", "imagen"}
    assert "id" not in attrs_prod

    attrs_venta = {a.nombre for a in attrs_regulares if a.clase_referencia == "ref_venta"}
    assert attrs_venta == {"fecha"}
    assert "id" not in attrs_venta

    attrs_hola = [a for a in attrs_regulares if a.clase_referencia == "ref_hola"]
    assert len(attrs_hola) == 0

    # 4. Atributos de clase intermedia: SOLO 'cantidad' (NO id, NO producto_id, NO venta_id)
    attrs_intermedia = [
        a for a in plan.acciones
        if isinstance(a, AccionCrearAtributoSchema) and a.clase_referencia == "ref_pv"
    ]
    assert len(attrs_intermedia) == 1
    assert attrs_intermedia[0].nombre == "cantidad"

    # 5. Relación de agregación planificada
    rels = [a for a in plan.acciones if isinstance(a, AccionCrearRelacionSchema)]
    assert len(rels) == 1
    assert rels[0].tipo_relacion == "agregacion"
    assert rels[0].clase_origen_referencia == "ref_hola"
    assert rels[0].clase_destino_referencia == "ref_venta"


