from uuid import UUID

from app.modules.diagramas.domain.entities.diagrama import Diagrama
from app.modules.diagramas.domain.exceptions import DiagramaNoEncontradoException
from app.modules.diagramas.domain.repositories.diagrama_repository import (
    DiagramaRepository,
)
from app.modules.gestion_proyectos.domain.exceptions import (
    ProyectoNoEncontradoException,
    UsuarioBloqueadoException,
)
from app.modules.gestion_proyectos.domain.repositories.colaborador_proyecto_repository import (
    ColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)


def obtener_diagrama_autorizado(
    *,
    propietario_id: str,
    diagrama_id: UUID,
    proyecto_repository: ProyectoRepository,
    diagrama_repository: DiagramaRepository,
    colaborador_repository: ColaboradorProyectoRepository | None = None,
    exigir_edicion: bool = False,
) -> Diagrama:
    """Verifica el acceso Proyecto → Diagrama para el usuario autenticado (propietario o colaborador activo)."""
    diagrama = diagrama_repository.obtener_por_id(diagrama_id)
    if diagrama is None:
        raise DiagramaNoEncontradoException()
    proyecto = proyecto_repository.obtener_por_id(diagrama.id_proyecto)
    if proyecto is None:
        raise ProyectoNoEncontradoException()

    if proyecto.propietario_id != propietario_id:
        if colaborador_repository is not None:
            colaborador = colaborador_repository.obtener_por_proyecto_y_usuario(
                proyecto.id, propietario_id
            )
            if colaborador is None:
                raise ProyectoNoEncontradoException()
            if colaborador.esta_bloqueado():
                raise UsuarioBloqueadoException()
            if not colaborador.esta_activo():
                raise ProyectoNoEncontradoException()
            if exigir_edicion and not colaborador.rol.puede_editar():
                raise NoAutorizadoProyectoException(
                    "No tienes permisos de edición en este proyecto."
                )
        else:
            raise ProyectoNoEncontradoException()

    return diagrama

