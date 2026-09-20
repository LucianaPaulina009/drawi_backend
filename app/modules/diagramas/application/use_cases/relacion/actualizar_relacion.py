from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.modules.diagramas.application.validaciones import obtener_diagrama_autorizado
from app.modules.diagramas.domain.entities.relacion import NO_DEFINIDO, Relacion
from app.modules.diagramas.domain.exceptions import (
    ActualizacionRelacionVaciaException,
    ClaseNoEncontradaException,
    RelacionEstructuralInmutableException,
    RelacionNoEncontradaException,
)
from app.modules.diagramas.domain.repositories.atributo_repository import (
    AtributoRepository,
)
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
from app.modules.diagramas.application.use_cases.relacion.crear_relacion import MaterializacionFKCommand
from app.modules.diagramas.domain.entities.atributo import Atributo
from app.modules.diagramas.domain.exceptions import AtributoYaExisteException
from app.modules.diagramas.domain.value_objects.procedencia_atributo import ProcedenciaAtributo
from app.modules.diagramas.application.use_cases.referencia_fk.crear_referencia_fk import CrearReferenciaFKCommand, CrearReferenciaFKUseCase
from app.modules.diagramas.application.use_cases.relacion.materializacion import asegurar_materializacion_valida
from app.modules.gestion_colaboradores.domain.repositories.colaborador_proyecto_repository import (
    ColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)
from app.shared.application.ports import UnitOfWork


@dataclass(slots=True)
class ActualizarRelacionCommand:
    propietario_id: str
    diagrama_id: UUID
    relacion_id: UUID
    nombre: str | None = None
    id_clase_origen: UUID | None = None
    id_clase_destino: UUID | None = None
    tipo_relacion: str | None = None
    cardinalidad_origen: str | None = None
    cardinalidad_destino: str | None = None
    conector_origen: str | None = None
    conector_destino: str | None = None
    materializacion_fk: list[MaterializacionFKCommand] | None = None


class ActualizarRelacionUseCase:
    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        diagrama_repository: DiagramaRepository,
        clase_repository: ClaseRepository,
        relacion_repository: RelacionRepository,
        atributo_repository: AtributoRepository,
        referencia_fk_repository: ReferenciaFKRepository,
        uow: UnitOfWork,
        colaborador_repository: ColaboradorProyectoRepository | None = None,
    ) -> None:
        self.proyecto_repository = proyecto_repository
        self.diagrama_repository = diagrama_repository
        self.clase_repository = clase_repository
        self.relacion_repository = relacion_repository
        self.atributo_repository = atributo_repository
        self.referencia_fk_repository = referencia_fk_repository
        self.uow = uow
        self.colaborador_repository = colaborador_repository

    def execute(self, command: ActualizarRelacionCommand) -> Relacion:
        obtener_diagrama_autorizado(
            propietario_id=command.propietario_id,
            diagrama_id=command.diagrama_id,
            proyecto_repository=self.proyecto_repository,
            diagrama_repository=self.diagrama_repository,
            colaborador_repository=self.colaborador_repository,
            exigir_edicion=True,
        )

        relacion = self.relacion_repository.obtener_por_id(command.relacion_id)
        if relacion is None or relacion.id_diagrama != command.diagrama_id:
            raise RelacionNoEncontradaException()

        campos_estructurales = (
            command.id_clase_origen,
            command.id_clase_destino,
            command.tipo_relacion,
            command.cardinalidad_origen,
            command.cardinalidad_destino,
            command.conector_origen,
            command.conector_destino,
            command.materializacion_fk,
        )
        if any(c is not None for c in campos_estructurales):
            raise RelacionEstructuralInmutableException(
                "Las relaciones son inmutables estructuralmente una vez creadas."
            )

        if command.nombre is None:
            raise ActualizacionRelacionVaciaException(
                "Debe proporcionar el nombre a actualizar para la relación."
            )

        relacion.actualizar_nombre(command.nombre)
        self.relacion_repository.guardar(relacion)
        self.uow.commit()
        return relacion

