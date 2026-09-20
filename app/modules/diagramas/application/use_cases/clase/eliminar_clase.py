from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.diagramas.application.validaciones import obtener_diagrama_autorizado
from app.modules.diagramas.domain.exceptions import ClaseNoEncontradaException
from app.modules.diagramas.domain.repositories.atributo_repository import AtributoRepository
from app.modules.diagramas.domain.repositories.clase_repository import ClaseRepository
from app.modules.diagramas.domain.repositories.diagrama_repository import (
    DiagramaRepository,
)
from app.modules.diagramas.domain.repositories.referencia_fk_repository import (
    ReferenciaFKRepository,
)
from app.modules.diagramas.domain.repositories.relacion_repository import (
    RelacionRepository,
)
from app.modules.gestion_colaboradores.domain.repositories.colaborador_proyecto_repository import (
    ColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)
from app.shared.application.ports import UnitOfWork


from app.modules.diagramas.application.services.cascadas_diagrama import (
    CascadasDiagramaService,
    CierreCascadaResultado,
)
from app.modules.diagramas.domain.repositories.estructura_relacion_nm_repository import (
    EstructuraRelacionNmRepository,
)


@dataclass(slots=True)
class EliminarClaseCommand:
    propietario_id: str
    diagrama_id: UUID
    clase_id: UUID


class EliminarClaseUseCase:
    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        diagrama_repository: DiagramaRepository,
        clase_repository: ClaseRepository,
        atributo_repository: AtributoRepository,
        uow: UnitOfWork,
        colaborador_repository: ColaboradorProyectoRepository | None = None,
        relacion_repository: RelacionRepository | None = None,
        referencia_fk_repository: ReferenciaFKRepository | None = None,
        estructura_repository: EstructuraRelacionNmRepository | None = None,
    ) -> None:
        self.proyecto_repository = proyecto_repository
        self.diagrama_repository = diagrama_repository
        self.clase_repository = clase_repository
        self.atributo_repository = atributo_repository
        self.uow = uow
        self.colaborador_repository = colaborador_repository
        self.relacion_repository = relacion_repository
        self.referencia_fk_repository = referencia_fk_repository
        self.estructura_repository = estructura_repository

    def execute(
        self, command: EliminarClaseCommand, confirmar: bool = True
    ) -> CierreCascadaResultado:
        obtener_diagrama_autorizado(
            propietario_id=command.propietario_id,
            diagrama_id=command.diagrama_id,
            proyecto_repository=self.proyecto_repository,
            diagrama_repository=self.diagrama_repository,
            colaborador_repository=self.colaborador_repository,
            exigir_edicion=True,
        )
        clase = self.clase_repository.obtener_por_id(command.clase_id)
        if clase is None or clase.id_diagrama != command.diagrama_id:
            raise ClaseNoEncontradaException()

        if self.relacion_repository is not None and self.referencia_fk_repository is not None:
            servicio = CascadasDiagramaService(
                clase_repository=self.clase_repository,
                atributo_repository=self.atributo_repository,
                relacion_repository=self.relacion_repository,
                referencia_fk_repository=self.referencia_fk_repository,
                estructura_nm_repository=self.estructura_repository,
            )
            resultado = servicio.cerrar_por_clase(command.clase_id, command.diagrama_id)
        else:
            if self.referencia_fk_repository is not None:
                self.referencia_fk_repository.eliminar_por_clase(command.clase_id)
            if self.relacion_repository is not None:
                self.relacion_repository.eliminar_por_clase(command.clase_id)
            self.atributo_repository.eliminar_por_clase(command.clase_id)
            self.clase_repository.eliminar(command.clase_id)
            resultado = CierreCascadaResultado(clases_eliminadas={command.clase_id})

        if confirmar:
            self.uow.commit()
        return resultado

