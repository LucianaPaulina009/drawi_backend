from __future__ import annotations

from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, Response, status

from app.core.dependencies import CurrentUser, DBSession, UoWDep
from app.modules.diagramas.application.queries.relacion.listar_relaciones import (
    ListarRelacionesQuery,
    ListarRelacionesQueryHandler,
)
from app.modules.diagramas.application.queries.relacion.obtener_relacion import (
    ObtenerRelacionQuery,
    ObtenerRelacionQueryHandler,
)
from app.modules.diagramas.application.use_cases.relacion.actualizar_relacion import (
    ActualizarRelacionCommand,
    ActualizarRelacionUseCase,
)
from app.modules.diagramas.application.use_cases.relacion.crear_relacion import (
    AtributoFkNuevoCommand,
    CrearRelacionCommand,
    CrearRelacionUseCase,
    MaterializacionFKCommand,
)
from app.modules.diagramas.application.use_cases.relacion.eliminar_relacion import (
    EliminarRelacionCommand,
    EliminarRelacionUseCase,
)
from app.modules.diagramas.infrastructure.api.schemas.referencia_fk_schemas import (
    ReferenciaFKRead,
)
from app.modules.diagramas.infrastructure.api.schemas.relacion_schemas import (
    ActualizarRelacionRequest,
    CrearRelacionRequest,
    ListaRelacionesRead,
    RelacionDetalleRead,
    RelacionRead,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_atributo_repository import (
    SQLModelAtributoRepository,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_clase_repository import (
    SQLModelClaseRepository,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_diagrama_repository import (
    SQLModelDiagramaRepository,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_estructura_relacion_nm_repository import (
    SQLModelEstructuraRelacionNmRepository,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_referencia_fk_repository import (
    SQLModelReferenciaFKRepository,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_relacion_repository import (
    SQLModelRelacionRepository,
)
from app.modules.gestion_colaboradores.infrastructure.persistence.repositories.sqlmodel_colaborador_proyecto_repository import (
    SQLModelColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.infrastructure.persistence.repositories.sqlmodel_proyecto_repository import (
    SQLModelProyectoRepository,
)

router = APIRouter(prefix="/diagramas", tags=["Relaciones"])


def _a_relacion_read(relacion) -> RelacionRead:
    return RelacionRead(
        id=relacion.id,
        id_diagrama=relacion.id_diagrama,
        id_clase_origen=relacion.id_clase_origen,
        id_clase_destino=relacion.id_clase_destino,
        tipo_relacion=relacion.tipo_relacion,
        cardinalidad_origen=relacion.cardinalidad_origen,
        cardinalidad_destino=relacion.cardinalidad_destino,
        conector_origen=relacion.conector_origen,
        conector_destino=relacion.conector_destino,
        nombre=getattr(relacion, "nombre", None),
    )


def _a_relacion_detalle_read(relacion, referencias=None) -> RelacionDetalleRead:
    read_base = _a_relacion_read(relacion)
    refs_list = []
    if referencias:
        refs_list = [
            ReferenciaFKRead(
                id=r.id,
                id_relacion=r.id_relacion,
                id_atributo_fk=r.id_atributo_fk,
                id_atributo_referenciado=r.id_atributo_referenciado,
                on_delete=r.on_delete,
                on_update=r.on_update,
            )
            for r in referencias
        ]
    elif hasattr(relacion, "referencias_fk") and relacion.referencias_fk:
        refs_list = [
            ReferenciaFKRead(
                id=r.id,
                id_relacion=r.id_relacion,
                id_atributo_fk=r.id_atributo_fk,
                id_atributo_referenciado=r.id_atributo_referenciado,
                on_delete=r.on_delete,
                on_update=r.on_update,
            )
            for r in relacion.referencias_fk
        ]
    return RelacionDetalleRead(
        **read_base.model_dump(),
        referencias_fk=refs_list,
    )


@router.get(
    "/{id_diagrama}/relaciones",
    response_model=ListaRelacionesRead,
    status_code=status.HTTP_200_OK,
    summary="Listar relaciones de un diagrama autorizado",
)
def listar_relaciones(
    id_diagrama: UUID,
    usuario: CurrentUser,
    session: DBSession,
) -> ListaRelacionesRead:
    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    relacion_repo = SQLModelRelacionRepository(session)
    referencia_fk_repo = SQLModelReferenciaFKRepository(session)
    colaborador_repo = SQLModelColaboradorProyectoRepository(session)

    relaciones = ListarRelacionesQueryHandler(
        proyecto_repo,
        diagrama_repo,
        relacion_repo,
        referencia_fk_repo,
        colaborador_repo,
    ).execute(
        ListarRelacionesQuery(
            propietario_id=usuario.user_id,
            diagrama_id=id_diagrama,
        )
    )
    return ListaRelacionesRead(
        items=[_a_relacion_detalle_read(rel) for rel in relaciones]
    )


@router.get(
    "/{id_diagrama}/relaciones/{id_relacion}",
    response_model=RelacionDetalleRead,
    status_code=status.HTTP_200_OK,
    summary="Consultar una relación de un diagrama autorizado",
)
def obtener_relacion(
    id_diagrama: UUID,
    id_relacion: UUID,
    usuario: CurrentUser,
    session: DBSession,
) -> RelacionDetalleRead:
    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    relacion_repo = SQLModelRelacionRepository(session)
    referencia_fk_repo = SQLModelReferenciaFKRepository(session)
    colaborador_repo = SQLModelColaboradorProyectoRepository(session)

    resultado = ObtenerRelacionQueryHandler(
        proyecto_repo,
        diagrama_repo,
        relacion_repo,
        referencia_fk_repo,
        colaborador_repo,
    ).execute(
        ObtenerRelacionQuery(
            propietario_id=usuario.user_id,
            diagrama_id=id_diagrama,
            relacion_id=id_relacion,
        )
    )
    return _a_relacion_detalle_read(resultado)


from app.modules.diagramas.application.services.notificador_colaboracion import (
    construir_efectos,
    emitir_evento_mutacion_confirmada,
    proyectar_clase,
    proyectar_relacion,
)


@router.post(
    "/{id_diagrama}/relaciones",
    response_model=RelacionDetalleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una relación en un diagrama autorizado",
)
def crear_relacion(
    id_diagrama: UUID,
    datos: CrearRelacionRequest,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
) -> RelacionDetalleRead:
    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    clase_repo = SQLModelClaseRepository(session)
    relacion_repo = SQLModelRelacionRepository(session)
    atributo_repo = SQLModelAtributoRepository(session)
    referencia_fk_repo = SQLModelReferenciaFKRepository(session)
    colaborador_repo = SQLModelColaboradorProyectoRepository(session)

    relacion = CrearRelacionUseCase(
        proyecto_repo,
        diagrama_repo,
        clase_repo,
        relacion_repo,
        uow,
        colaborador_repo,
        atributo_repo,
        referencia_fk_repo,
    ).execute(
        CrearRelacionCommand(
            propietario_id=usuario.user_id,
            diagrama_id=id_diagrama,
            id_relacion=datos.id_relacion,
            id_clase_origen=datos.id_clase_origen,
            id_clase_destino=datos.id_clase_destino,
            tipo_relacion=datos.tipo_relacion,
            cardinalidad_origen=datos.cardinalidad_origen,
            cardinalidad_destino=datos.cardinalidad_destino,
            conector_origen=datos.conector_origen,
            conector_destino=datos.conector_destino,
            nombre=datos.nombre,
            materializacion_fk=[
                MaterializacionFKCommand(
                    id_referencia_fk=item.id_referencia_fk,
                    id_atributo_referenciado=item.id_atributo_referenciado,
                    id_atributo_fk=item.id_atributo_fk,
                    id_clase_fk=item.id_clase_fk,
                    atributo_fk_nuevo=(
                        AtributoFkNuevoCommand(**item.atributo_fk_nuevo.model_dump())
                        if item.atributo_fk_nuevo else None
                    ),
                    on_delete=item.on_delete,
                    on_update=item.on_update,
                ) for item in datos.materializacion_fk
            ],
        )
    )

    clases_act = []
    for item in datos.materializacion_fk:
        if item.id_clase_fk:
            c = proyectar_clase(clase_repo, atributo_repo, item.id_clase_fk)
            if c:
                clases_act.append(c)

    efectos = construir_efectos(
        clases_actualizadas=clases_act,
        relaciones_actualizadas=[proyectar_relacion(relacion_repo, referencia_fk_repo, relacion.id)],
    )
    emitir_evento_mutacion_confirmada(
        diagrama_id=id_diagrama,
        action_id=None,
        tipo_operacion="CREAR_RELACION",
        emisor_id=usuario.user_id,
        efectos=efectos,
    )

    return _a_relacion_detalle_read(
        relacion,
        referencias=referencia_fk_repo.listar_por_relacion(relacion.id),
    )


@router.patch(
    "/{id_diagrama}/relaciones/{id_relacion}",
    response_model=RelacionRead,
    status_code=status.HTTP_200_OK,
    summary="Actualizar parcialmente una relación autorizada",
)
def actualizar_relacion(
    id_diagrama: UUID,
    id_relacion: UUID,
    datos: ActualizarRelacionRequest,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
) -> RelacionRead:
    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    clase_repo = SQLModelClaseRepository(session)
    relacion_repo = SQLModelRelacionRepository(session)
    atributo_repo = SQLModelAtributoRepository(session)
    referencia_fk_repo = SQLModelReferenciaFKRepository(session)
    colaborador_repo = SQLModelColaboradorProyectoRepository(session)

    relacion = ActualizarRelacionUseCase(
        proyecto_repo,
        diagrama_repo,
        clase_repo,
        relacion_repo,
        atributo_repo,
        referencia_fk_repo,
        uow,
        colaborador_repo,
    ).execute(
        ActualizarRelacionCommand(
            propietario_id=usuario.user_id,
            diagrama_id=id_diagrama,
            relacion_id=id_relacion,
            nombre=datos.nombre,
            id_clase_origen=datos.id_clase_origen,
            id_clase_destino=datos.id_clase_destino,
            tipo_relacion=datos.tipo_relacion,
            cardinalidad_origen=datos.cardinalidad_origen,
            cardinalidad_destino=datos.cardinalidad_destino,
            conector_origen=datos.conector_origen,
            conector_destino=datos.conector_destino,
            materializacion_fk=(
                [
                    MaterializacionFKCommand(
                        id_referencia_fk=item.id_referencia_fk,
                        id_atributo_referenciado=item.id_atributo_referenciado,
                        id_atributo_fk=item.id_atributo_fk,
                        id_clase_fk=item.id_clase_fk,
                        atributo_fk_nuevo=(
                            AtributoFkNuevoCommand(**item.atributo_fk_nuevo.model_dump())
                            if item.atributo_fk_nuevo else None
                        ),
                        on_delete=item.on_delete,
                        on_update=item.on_update,
                    ) for item in datos.materializacion_fk
                ] if datos.materializacion_fk is not None else None
            ),
        )
    )

    efectos = construir_efectos(
        relaciones_actualizadas=[proyectar_relacion(relacion_repo, referencia_fk_repo, relacion.id)]
    )
    emitir_evento_mutacion_confirmada(
        diagrama_id=id_diagrama,
        action_id=None,
        tipo_operacion="RENOMBRAR_RELACION",
        emisor_id=usuario.user_id,
        efectos=efectos,
    )

    return _a_relacion_read(relacion)


@router.delete(
    "/{id_diagrama}/relaciones/{id_relacion}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar lógicamente una relación autorizada",
)
def eliminar_relacion(
    id_diagrama: UUID,
    id_relacion: UUID,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
) -> Response:
    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    relacion_repo = SQLModelRelacionRepository(session)
    referencia_fk_repo = SQLModelReferenciaFKRepository(session)
    atributo_repo = SQLModelAtributoRepository(session)
    clase_repo = SQLModelClaseRepository(session)
    estructura_nm_repo = SQLModelEstructuraRelacionNmRepository(session)
    colaborador_repo = SQLModelColaboradorProyectoRepository(session)

    resultado = EliminarRelacionUseCase(
        proyecto_repo,
        diagrama_repo,
        relacion_repo,
        referencia_fk_repo,
        uow,
        colaborador_repo,
        atributo_repo,
        clase_repo,
        estructura_nm_repo,
    ).execute(
        EliminarRelacionCommand(
            propietario_id=usuario.user_id,
            diagrama_id=id_diagrama,
            relacion_id=id_relacion,
        )
    )

    clases_act = [
        proyectar_clase(clase_repo, atributo_repo, cid)
        for cid in (resultado.clases_modificadas - resultado.clases_eliminadas)
    ]
    efectos = construir_efectos(
        clases_actualizadas=[c for c in clases_act if c is not None],
        clases_eliminadas=list(resultado.clases_eliminadas),
        relaciones_eliminadas=list(resultado.relaciones_eliminadas),
        estructuras_nm_eliminadas=list(resultado.estructuras_nm_eliminadas),
    )
    emitir_evento_mutacion_confirmada(
        diagrama_id=id_diagrama,
        action_id=None,
        tipo_operacion="ELIMINAR_RELACION",
        emisor_id=usuario.user_id,
        efectos=efectos,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
