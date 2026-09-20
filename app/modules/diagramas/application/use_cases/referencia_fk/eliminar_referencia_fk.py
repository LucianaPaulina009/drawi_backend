from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.diagramas.application.validaciones import obtener_diagrama_autorizado
from app.modules.diagramas.domain.exceptions import (
    MaterializacionRelacionRequeridaException,
    ReferenciaFKNoEncontradaException,
    RelacionNoEncontradaException,
)
from app.modules.diagramas.domain.repositories.diagrama_repository import (
    DiagramaRepository,
)
from app.modules.diagramas.domain.repositories.atributo_repository import AtributoRepository
from app.modules.diagramas.application.use_cases.relacion.materializacion import asegurar_materializacion_valida
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
from app.modules.diagramas.domain.repositories.clase_repository import ClaseRepository
from app.modules.diagramas.domain.repositories.estructura_relacion_nm_repository import (
    EstructuraRelacionNmRepository,
)


@dataclass(slots=True)
class EliminarReferenciaFKCommand:
    propietario_id: str
    relacion_id: UUID
    referencia_id: UUID


class EliminarReferenciaFKUseCase:
    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        diagrama_repository: DiagramaRepository,
        relacion_repository: RelacionRepository,
        referencia_fk_repository: ReferenciaFKRepository,
        uow: UnitOfWork,
        colaborador_repository: ColaboradorProyectoRepository | None = None,
        atributo_repository: AtributoRepository | None = None,
        clase_repository: ClaseRepository | None = None,
        estructura_repository: EstructuraRelacionNmRepository | None = None,
    ) -> None:
        self.proyecto_repository = proyecto_repository
        self.diagrama_repository = diagrama_repository
        self.relacion_repository = relacion_repository
        self.referencia_fk_repository = referencia_fk_repository
        self.uow = uow
        self.colaborador_repository = colaborador_repository
        self.atributo_repository = atributo_repository
        self.clase_repository = clase_repository
        self.estructura_repository = estructura_repository

    def execute(
        self, command: EliminarReferenciaFKCommand, confirmar: bool = True
    ) -> CierreCascadaResultado:
        referencia = self.referencia_fk_repository.obtener_por_id(command.referencia_id)
        if referencia is None or referencia.id_relacion != command.relacion_id:
            raise ReferenciaFKNoEncontradaException()

        relacion = self.relacion_repository.obtener_por_id(command.relacion_id)
        if relacion is None:
            raise RelacionNoEncontradaException()

        obtener_diagrama_autorizado(
            propietario_id=command.propietario_id,
            diagrama_id=relacion.id_diagrama,
            proyecto_repository=self.proyecto_repository,
            diagrama_repository=self.diagrama_repository,
            colaborador_repository=self.colaborador_repository,
            exigir_edicion=True,
        )

        if self.clase_repository is not None and self.atributo_repository is not None:
            servicio = CascadasDiagramaService(
                clase_repository=self.clase_repository,
                atributo_repository=self.atributo_repository,
                relacion_repository=self.relacion_repository,
                referencia_fk_repository=self.referencia_fk_repository,
                estructura_nm_repository=self.estructura_repository,
            )
            resultado = servicio.cerrar_por_referencia_fk(
                referencia_id=command.referencia_id,
                relacion_id=command.relacion_id,
                diagrama_id=relacion.id_diagrama,
            )
        else:
            self.referencia_fk_repository.eliminar(command.referencia_id)
            if self.atributo_repository is not None:
                atributo = self.atributo_repository.obtener_por_id(referencia.id_atributo_fk)
                if atributo and atributo.procedencia == "sistema_fk" and not self.referencia_fk_repository.listar_por_atributo(atributo.id):
                    self.atributo_repository.eliminar(atributo.id)
                try:
                    asegurar_materializacion_valida(
                        relacion,
                        self.referencia_fk_repository.listar_por_relacion(relacion.id),
                        self.atributo_repository.obtener_por_id,
                    )
                except MaterializacionRelacionRequeridaException:
                    referencias_restantes = self.referencia_fk_repository.listar_por_relacion(
                        relacion.id
                    )
                    self.referencia_fk_repository.eliminar_por_relacion(relacion.id)
                    for referencia_restante in referencias_restantes:
                        atributo_fk = self.atributo_repository.obtener_por_id(
                            referencia_restante.id_atributo_fk
                        )
                        if (
                            atributo_fk
                            and atributo_fk.procedencia == "sistema_fk"
                            and not self.referencia_fk_repository.listar_por_atributo(
                                atributo_fk.id
                            )
                        ):
                            self.atributo_repository.eliminar(atributo_fk.id)
                    self.relacion_repository.eliminar(relacion.id)
            resultado = CierreCascadaResultado(referencias_eliminadas={command.referencia_id})

        if confirmar:
            self.uow.commit()
        return resultado
