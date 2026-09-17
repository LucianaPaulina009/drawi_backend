from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.modules.diagramas.application.validaciones import obtener_diagrama_autorizado
from app.modules.diagramas.domain.entities.relacion import NO_DEFINIDO, Relacion
from app.modules.diagramas.domain.exceptions import (
    ActualizacionRelacionVaciaException,
    ClaseNoEncontradaException,
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

        nueva_origen = command.id_clase_origen or relacion.id_clase_origen
        nueva_destino = command.id_clase_destino or relacion.id_clase_destino

        if command.id_clase_origen is not None:
            clase_o = self.clase_repository.obtener_por_id(command.id_clase_origen)
            if clase_o is None or clase_o.id_diagrama != command.diagrama_id:
                raise ClaseNoEncontradaException()

        if command.id_clase_destino is not None:
            clase_d = self.clase_repository.obtener_por_id(command.id_clase_destino)
            if clase_d is None or clase_d.id_diagrama != command.diagrama_id:
                raise ClaseNoEncontradaException()

        # Las referencias que dejan de pertenecer a los extremos finales no pueden sobrevivir.
        if (
            nueva_origen != relacion.id_clase_origen
            or nueva_destino != relacion.id_clase_destino
        ):
            attrs_origen = {
                a.id for a in self.atributo_repository.listar_por_clase(nueva_origen)
            }
            attrs_destino = {
                a.id for a in self.atributo_repository.listar_por_clase(nueva_destino)
            }
            attrs_validos = attrs_origen | attrs_destino

            for ref in self.referencia_fk_repository.listar_por_relacion(relacion.id):
                if (
                    ref.id_atributo_fk not in attrs_validos
                    or ref.id_atributo_referenciado not in attrs_validos
                ):
                    self.referencia_fk_repository.eliminar(ref.id)

        relacion.actualizar(
            id_clase_origen=command.id_clase_origen or NO_DEFINIDO,
            id_clase_destino=command.id_clase_destino or NO_DEFINIDO,
            tipo_relacion=command.tipo_relacion or NO_DEFINIDO,
            cardinalidad_origen=command.cardinalidad_origen or NO_DEFINIDO,
            cardinalidad_destino=command.cardinalidad_destino or NO_DEFINIDO,
            conector_origen=command.conector_origen or NO_DEFINIDO,
            conector_destino=command.conector_destino or NO_DEFINIDO,
        )

        self.relacion_repository.guardar(relacion)
        referencias = self.referencia_fk_repository.listar_por_relacion(relacion.id)
        if command.materializacion_fk:
            for materializacion in command.materializacion_fk:
                atributo_fk_id = materializacion.id_atributo_fk
                if materializacion.atributo_fk_nuevo is not None:
                    if materializacion.id_clase_fk not in {
                        relacion.id_clase_origen,
                        relacion.id_clase_destino,
                    }:
                        raise ClaseNoEncontradaException()
                    nuevo = materializacion.atributo_fk_nuevo
                    if self.atributo_repository.obtener_por_id(nuevo.id_atributo):
                        raise AtributoYaExisteException()
                    existentes = self.atributo_repository.listar_por_clase(materializacion.id_clase_fk)
                    self.atributo_repository.guardar(Atributo.crear(
                        id=nuevo.id_atributo, id_clase=materializacion.id_clase_fk,
                        nombre=nuevo.nombre, tipo_dato=nuevo.tipo_dato, longitud=nuevo.longitud,
                        precision=nuevo.precision, escala=nuevo.escala, permite_nulo=nuevo.permite_nulo,
                        es_unico=nuevo.es_unico, valor_por_defecto=nuevo.valor_por_defecto,
                        orden_de_posicion=(existentes[-1].orden_de_posicion + 1) if existentes else 1,
                        procedencia=ProcedenciaAtributo.SISTEMA_FK,
                    ))
                    atributo_fk_id = nuevo.id_atributo
                if atributo_fk_id is None:
                    raise ActualizacionRelacionVaciaException("La actualización requiere un atributo FK.")
                referencias.append(CrearReferenciaFKUseCase(
                    self.proyecto_repository, self.diagrama_repository, self.relacion_repository,
                    self.clase_repository, self.atributo_repository, self.referencia_fk_repository,
                    self.uow, self.colaborador_repository,
                ).execute(CrearReferenciaFKCommand(
                    propietario_id=command.propietario_id, relacion_id=relacion.id,
                    id_referencia_fk=materializacion.id_referencia_fk,
                    id_atributo_fk=atributo_fk_id,
                    id_atributo_referenciado=materializacion.id_atributo_referenciado,
                    on_delete=materializacion.on_delete, on_update=materializacion.on_update,
                ), confirmar=False))
        asegurar_materializacion_valida(relacion, referencias, self.atributo_repository.obtener_por_id)
        self.uow.commit()
        return relacion
