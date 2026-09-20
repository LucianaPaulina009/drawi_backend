from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Response, status

from app.core.dependencies import CurrentUser, DBSession, UoWDep
from app.modules.diagramas.application.queries.atributo.atributo_handlers import (
    AtributoQuery,
    AtributoQueryHandler,
)
from app.modules.diagramas.application.use_cases.atributo.atributo_use_cases import (
    AtributoCommand,
    AtributoUseCase,
)
from app.modules.diagramas.infrastructure.api.schemas.atributo_schemas import (
    ActualizarAtributoRequest,
    AtributoRead,
    AtributoRequest,
    ListaAtributosRead,
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

router = APIRouter(prefix="/clases", tags=["Atributos"])


def _a_read(atributo) -> AtributoRead:
    """Proyecta una entidad de dominio al contrato HTTP de atributos."""

    return AtributoRead(
        id=atributo.id,
        id_clase=atributo.id_clase,
        tipo_dato=atributo.tipo_dato,
        nombre=atributo.nombre,
        longitud=atributo.longitud,
        precision=atributo.precision,
        escala=atributo.escala,
        es_llave_primaria=atributo.es_llave_primaria,
        permite_nulo=atributo.permite_nulo,
        es_unico=atributo.es_unico,
        valor_por_defecto=atributo.valor_por_defecto,
        orden_de_posicion=atributo.orden_de_posicion,
        procedencia=atributo.procedencia,
    )


def _repositorios(session: DBSession):
    """Construye los adaptadores de persistencia usados por la aplicación."""

    return (
        SQLModelProyectoRepository(session),
        SQLModelDiagramaRepository(session),
        SQLModelClaseRepository(session),
        SQLModelAtributoRepository(session),
        SQLModelColaboradorProyectoRepository(session),
        SQLModelReferenciaFKRepository(session),
        SQLModelRelacionRepository(session),
    )



@router.get(
    "/{id_clase}/atributos",
    response_model=ListaAtributosRead,
    status_code=status.HTTP_200_OK,
    summary="Listar atributos de una clase autorizada",
)
def listar_atributos(
    id_clase: UUID,
    usuario: CurrentUser,
    session: DBSession,
) -> ListaAtributosRead:
    proyecto_repo, diagrama_repo, clase_repo, atributo_repo, colaborador_repo, _, _ = _repositorios(session)
    atributos = AtributoQueryHandler(
        proyecto_repo, diagrama_repo, clase_repo, atributo_repo, colaborador_repo
    ).listar(AtributoQuery(usuario.user_id, id_clase))
    return ListaAtributosRead(items=[_a_read(atributo) for atributo in atributos])


@router.get(
    "/{id_clase}/atributos/{id_atributo}",
    response_model=AtributoRead,
    status_code=status.HTTP_200_OK,
    summary="Consultar un atributo de una clase autorizada",
)
def obtener_atributo(
    id_clase: UUID,
    id_atributo: UUID,
    usuario: CurrentUser,
    session: DBSession,
) -> AtributoRead:
    proyecto_repo, diagrama_repo, clase_repo, atributo_repo, colaborador_repo, _, _ = _repositorios(session)
    atributo = AtributoQueryHandler(
        proyecto_repo, diagrama_repo, clase_repo, atributo_repo, colaborador_repo
    ).obtener(AtributoQuery(usuario.user_id, id_clase, id_atributo))
    return _a_read(atributo)



from app.modules.diagramas.application.services.notificador_colaboracion import (
    construir_efectos,
    emitir_evento_mutacion_confirmada,
    proyectar_clase,
)


@router.post(
    "/{id_clase}/atributos",
    response_model=AtributoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un atributo en una clase autorizada",
)
def crear_atributo(
    id_clase: UUID,
    datos: AtributoRequest,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
) -> AtributoRead:
    proyecto_repo, diagrama_repo, clase_repo, atributo_repo, colaborador_repo, referencia_fk_repo, relacion_repo = _repositorios(session)
    atributo = AtributoUseCase(
        proyecto_repo, diagrama_repo, clase_repo, atributo_repo, uow, colaborador_repo, referencia_fk_repo, relacion_repo
    ).crear(
        AtributoCommand(
            usuario.user_id,
            id_clase,
            datos.model_dump(exclude={"id_atributo"}),
            atributo_id=datos.id_atributo,
        )
    )

    clase = clase_repo.obtener_por_id(id_clase)
    if clase:
        efectos = construir_efectos(
            clases_actualizadas=[proyectar_clase(clase_repo, atributo_repo, id_clase)]
        )
        emitir_evento_mutacion_confirmada(
            diagrama_id=clase.id_diagrama,
            action_id=None,
            tipo_operacion="CREAR_ATRIBUTO",
            emisor_id=usuario.user_id,
            efectos=efectos,
        )

    return _a_read(atributo)


@router.patch(
    "/{id_clase}/atributos/{id_atributo}",
    response_model=AtributoRead,
    status_code=status.HTTP_200_OK,
    summary="Actualizar parcialmente un atributo autorizado",
)
def actualizar_atributo(
    id_clase: UUID,
    id_atributo: UUID,
    datos: ActualizarAtributoRequest,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
) -> AtributoRead:
    proyecto_repo, diagrama_repo, clase_repo, atributo_repo, colaborador_repo, referencia_fk_repo, relacion_repo = _repositorios(session)
    atributo = AtributoUseCase(
        proyecto_repo, diagrama_repo, clase_repo, atributo_repo, uow, colaborador_repo, referencia_fk_repo, relacion_repo
    ).actualizar(
        AtributoCommand(
            usuario.user_id,
            id_clase,
            datos.model_dump(exclude_unset=True),
            id_atributo,
        )
    )

    clase = clase_repo.obtener_por_id(id_clase)
    if clase:
        efectos = construir_efectos(
            clases_actualizadas=[proyectar_clase(clase_repo, atributo_repo, id_clase)]
        )
        emitir_evento_mutacion_confirmada(
            diagrama_id=clase.id_diagrama,
            action_id=None,
            tipo_operacion="ACTUALIZAR_ATRIBUTO",
            emisor_id=usuario.user_id,
            efectos=efectos,
        )

    return _a_read(atributo)


@router.delete(
    "/{id_clase}/atributos/{id_atributo}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar lógicamente un atributo autorizado",
)
def eliminar_atributo(
    id_clase: UUID,
    id_atributo: UUID,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
) -> Response:
    proyecto_repo, diagrama_repo, clase_repo, atributo_repo, colaborador_repo, referencia_fk_repo, relacion_repo = _repositorios(session)
    clase = clase_repo.obtener_por_id(id_clase)
    diagrama_id = clase.id_diagrama if clase else None

    resultado = AtributoUseCase(
        proyecto_repo, diagrama_repo, clase_repo, atributo_repo, uow, colaborador_repo, referencia_fk_repo, relacion_repo
    ).eliminar(AtributoCommand(usuario.user_id, id_clase, {}, id_atributo))

    if diagrama_id:
        clases_act = (
            [proyectar_clase(clase_repo, atributo_repo, id_clase)]
            if (id_clase not in resultado.clases_eliminadas and clase_repo.obtener_por_id(id_clase))
            else []
        )
        efectos = construir_efectos(
            clases_actualizadas=clases_act,
            clases_eliminadas=list(resultado.clases_eliminadas),
            relaciones_eliminadas=list(resultado.relaciones_eliminadas),
            estructuras_nm_eliminadas=list(resultado.estructuras_nm_eliminadas),
        )
        emitir_evento_mutacion_confirmada(
            diagrama_id=diagrama_id,
            action_id=None,
            tipo_operacion="ELIMINAR_ATRIBUTO",
            emisor_id=usuario.user_id,
            efectos=efectos,
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
