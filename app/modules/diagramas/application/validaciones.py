from uuid import UUID

from app.modules.diagramas.domain.entities.diagrama import Diagrama
from app.modules.diagramas.domain.exceptions import DiagramaNoEncontradoException
from app.modules.diagramas.domain.repositories.diagrama_repository import (
    DiagramaRepository,
)
from app.modules.gestion_proyectos.domain.exceptions import ProyectoNoEncontradoException
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)


def obtener_diagrama_autorizado(
    *,
    propietario_id: str,
    diagrama_id: UUID,
    proyecto_repository: ProyectoRepository,
    diagrama_repository: DiagramaRepository,
) -> Diagrama:
    """Verifica el acceso Proyecto → Diagrama para rutas de clases."""
    diagrama = diagrama_repository.obtener_por_id(diagrama_id)
    if diagrama is None:
        raise DiagramaNoEncontradoException()
    proyecto = proyecto_repository.obtener_por_id(diagrama.id_proyecto)
    if proyecto is None or proyecto.propietario_id != propietario_id:
        raise ProyectoNoEncontradoException()
    return diagrama
