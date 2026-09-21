from __future__ import annotations

from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, Response, status

from app.core.dependencies import CurrentUser, DBSession, UoWDep
from app.modules.diagramas.application.queries.clase.listar_clases import (
    ListarClasesQuery,
    ListarClasesQueryHandler,
)
from app.modules.diagramas.application.queries.clase.obtener_clase import (
    ObtenerClaseQuery,
    ObtenerClaseQueryHandler,
)
from app.modules.diagramas.application.use_cases.clase.actualizar_clase import (
    ActualizarClaseCommand,
    ActualizarClaseUseCase,
)
from app.modules.diagramas.application.use_cases.clase.crear_clase import (
    CrearClaseCommand,
    CrearClaseUseCase,
)
from app.modules.diagramas.application.use_cases.clase.eliminar_clase import (
    EliminarClaseCommand,
    EliminarClaseUseCase,
)
from app.modules.diagramas.infrastructure.api.schemas.clase_schemas import (
    ActualizarClaseRequest,
    ClaseDetalleRead,
    ClaseRead,
    CrearClaseRequest,
    ListaClasesRead,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_clase_repository import (
    SQLModelClaseRepository,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_diagrama_repository import (
    SQLModelDiagramaRepository,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_atributo_repository import (
    SQLModelAtributoRepository,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_estructura_relacion_nm_repository import (
    SQLModelEstructuraRelacionNmRepository,
)
from app.modules.gestion_colaboradores.infrastructure.persistence.repositories.sqlmodel_colaborador_proyecto_repository import (
    SQLModelColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.infrastructure.persistence.repositories.sqlmodel_proyecto_repository import (
    SQLModelProyectoRepository,
)

router = APIRouter(prefix="/diagramas", tags=["Clases"])


def _a_read(clase) -> ClaseRead:
    return ClaseRead(
        id=clase.id,
        id_diagrama=clase.id_diagrama,
        nombre=clase.nombre,
        posicion_x=clase.posicion_x,
        posicion_y=clase.posicion_y,
        ancho=clase.ancho,
    )


@router.get(
    "/{id_diagrama}/clases",
    response_model=ListaClasesRead,
    status_code=status.HTTP_200_OK,
    summary="Listar clases de un diagrama autorizado",
)
def listar_clases(
    id_diagrama: UUID,
    usuario: CurrentUser,
    session: DBSession,
) -> ListaClasesRead:
    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    clase_repo = SQLModelClaseRepository(session)
    colaborador_repo = SQLModelColaboradorProyectoRepository(session)
    clases = ListarClasesQueryHandler(
        proyecto_repo, diagrama_repo, clase_repo, colaborador_repo
    ).execute(
        ListarClasesQuery(
            propietario_id=usuario.user_id,
            diagrama_id=id_diagrama,
        )
    )
    return ListaClasesRead(items=[_a_read(clase) for clase in clases])


@router.get(
    "/{id_diagrama}/clases/{id_clase}",
    response_model=ClaseDetalleRead,
    status_code=status.HTTP_200_OK,
    summary="Consultar una clase de un diagrama autorizado",
)
def obtener_clase(
    id_diagrama: UUID,
    id_clase: UUID,
    usuario: CurrentUser,
    session: DBSession,
) -> ClaseDetalleRead:
    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    clase_repo = SQLModelClaseRepository(session)
    atributo_repo = SQLModelAtributoRepository(session)
    colaborador_repo = SQLModelColaboradorProyectoRepository(session)
    resultado = ObtenerClaseQueryHandler(
        proyecto_repo,
        diagrama_repo,
        clase_repo,
        atributo_repo,
        colaborador_repo,
    ).execute(
        ObtenerClaseQuery(
            propietario_id=usuario.user_id,
            diagrama_id=id_diagrama,
            clase_id=id_clase,
        )
    )
    return ClaseDetalleRead(
        **_a_read(resultado).model_dump(),
        atributos=[
            asdict(atributo)
            for atributo in resultado.atributos
        ],
    )


from app.modules.diagramas.application.services.notificador_colaboracion import (
    construir_efectos,
    emitir_evento_mutacion_confirmada,
    proyectar_clase,
)
from app.modules.diagramas.infrastructure.api.schemas.atributo_schemas import AtributoRead


@router.post(
    "/{id_diagrama}/clases",
    response_model=ClaseDetalleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una clase en un diagrama autorizado",
)
def crear_clase(
    id_diagrama: UUID,
    datos: CrearClaseRequest,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
) -> ClaseDetalleRead:
    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    clase_repo = SQLModelClaseRepository(session)
    atributo_repo = SQLModelAtributoRepository(session)
    colaborador_repo = SQLModelColaboradorProyectoRepository(session)
    clase, atributos = CrearClaseUseCase(
        proyecto_repo,
        diagrama_repo,
        clase_repo,
        atributo_repo,
        uow,
        colaborador_repo,
    ).execute(
        CrearClaseCommand(
            propietario_id=usuario.user_id,
            diagrama_id=id_diagrama,
            nombre=datos.nombre,
            posicion_x=datos.posicion_x,
            posicion_y=datos.posicion_y,
            ancho=datos.ancho,
            id_clase=datos.id_clase,
            id_atributo_inicial=datos.id_atributo_inicial,
        )
    )

    efectos = construir_efectos(
        clases_actualizadas=[proyectar_clase(clase_repo, atributo_repo, clase.id)]
    )
    emitir_evento_mutacion_confirmada(
        diagrama_id=id_diagrama,
        action_id=None,
        tipo_operacion="CREAR_CLASE",
        emisor_id=usuario.user_id,
        efectos=efectos,
    )

    return ClaseDetalleRead(
        **_a_read(clase).model_dump(),
        atributos=[
            AtributoRead(
                id=a.id,
                id_clase=a.id_clase,
                tipo_dato=a.tipo_dato,
                nombre=a.nombre,
                longitud=a.longitud,
                precision=a.precision,
                escala=a.escala,
                es_llave_primaria=a.es_llave_primaria,
                permite_nulo=a.permite_nulo,
                es_unico=a.es_unico,
                valor_por_defecto=a.valor_por_defecto,
                orden_de_posicion=a.orden_de_posicion,
                procedencia=a.procedencia,
            )
            for a in atributos
        ],
    )


@router.patch(
    "/{id_diagrama}/clases/{id_clase}",
    response_model=ClaseRead,
    status_code=status.HTTP_200_OK,
    summary="Actualizar parcialmente una clase autorizada",
)
def actualizar_clase(
    id_diagrama: UUID,
    id_clase: UUID,
    datos: ActualizarClaseRequest,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
) -> ClaseRead:
    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    clase_repo = SQLModelClaseRepository(session)
    atributo_repo = SQLModelAtributoRepository(session)
    colaborador_repo = SQLModelColaboradorProyectoRepository(session)
    clase = ActualizarClaseUseCase(
        proyecto_repo, diagrama_repo, clase_repo, uow, colaborador_repo
    ).execute(
        ActualizarClaseCommand(
            propietario_id=usuario.user_id,
            diagrama_id=id_diagrama,
            clase_id=id_clase,
            nombre=datos.nombre,
            posicion_x=datos.posicion_x,
            posicion_y=datos.posicion_y,
            ancho=datos.ancho,
        )
    )

    efectos = construir_efectos(
        clases_actualizadas=[proyectar_clase(clase_repo, atributo_repo, clase.id)]
    )
    emitir_evento_mutacion_confirmada(
        diagrama_id=id_diagrama,
        action_id=None,
        tipo_operacion="ACTUALIZAR_CLASE",
        emisor_id=usuario.user_id,
        efectos=efectos,
    )

    return _a_read(clase)


from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_relacion_repository import (
    SQLModelRelacionRepository,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_referencia_fk_repository import (
    SQLModelReferenciaFKRepository,
)


@router.delete(
    "/{id_diagrama}/clases/{id_clase}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar lógicamente una clase autorizada",
)
def eliminar_clase(
    id_diagrama: UUID,
    id_clase: UUID,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
) -> Response:
    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    clase_repo = SQLModelClaseRepository(session)
    atributo_repo = SQLModelAtributoRepository(session)
    colaborador_repo = SQLModelColaboradorProyectoRepository(session)
    relacion_repo = SQLModelRelacionRepository(session)
    referencia_fk_repo = SQLModelReferenciaFKRepository(session)
    estructura_nm_repo = SQLModelEstructuraRelacionNmRepository(session)

    resultado = EliminarClaseUseCase(
        proyecto_repo,
        diagrama_repo,
        clase_repo,
        atributo_repo,
        uow,
        colaborador_repo,
        relacion_repo,
        referencia_fk_repo,
        estructura_nm_repo,
    ).execute(
        EliminarClaseCommand(
            propietario_id=usuario.user_id,
            diagrama_id=id_diagrama,
            clase_id=id_clase,
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
        tipo_operacion="ELIMINAR_CLASE",
        emisor_id=usuario.user_id,
        efectos=efectos,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
