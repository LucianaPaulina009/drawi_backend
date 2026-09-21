from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.diagramas.application.use_cases.referencia_fk.crear_referencia_fk import CrearReferenciaFKCommand, CrearReferenciaFKUseCase
from app.modules.diagramas.application.use_cases.relacion.materializacion import asegurar_materializacion_valida
from app.modules.diagramas.application.validaciones import obtener_diagrama_autorizado
from app.modules.diagramas.domain.entities.atributo import Atributo
from app.modules.diagramas.domain.entities.relacion import Relacion
from app.modules.diagramas.domain.exceptions import AtributoYaExisteException, ClaseNoEncontradaException, ConectorOcupadoException, RelacionYaExisteException
from app.modules.diagramas.domain.repositories.atributo_repository import AtributoRepository
from app.modules.diagramas.domain.repositories.clase_repository import ClaseRepository
from app.modules.diagramas.domain.repositories.diagrama_repository import DiagramaRepository
from app.modules.diagramas.domain.repositories.referencia_fk_repository import ReferenciaFKRepository
from app.modules.diagramas.domain.repositories.relacion_repository import RelacionRepository
from app.modules.diagramas.domain.value_objects.procedencia_atributo import ProcedenciaAtributo
from app.modules.diagramas.domain.value_objects.conector import Conector
from app.modules.gestion_colaboradores.domain.repositories.colaborador_proyecto_repository import ColaboradorProyectoRepository
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import ProyectoRepository
from app.shared.application.ports import UnitOfWork


@dataclass(slots=True)
class AtributoFkNuevoCommand:
    id_atributo: UUID
    nombre: str
    tipo_dato: str
    longitud: int | None = None
    precision: int | None = None
    escala: int | None = None
    permite_nulo: bool = True
    es_unico: bool = False
    valor_por_defecto: str | None = None


@dataclass(slots=True)
class MaterializacionFKCommand:
    id_referencia_fk: UUID
    id_atributo_referenciado: UUID
    id_atributo_fk: UUID | None = None
    id_clase_fk: UUID | None = None
    atributo_fk_nuevo: AtributoFkNuevoCommand | None = None
    on_delete: str = "NO_ACTION"
    on_update: str = "NO_ACTION"


@dataclass(slots=True)
class CrearRelacionCommand:
    propietario_id: str
    diagrama_id: UUID
    id_relacion: UUID
    id_clase_origen: UUID
    id_clase_destino: UUID
    tipo_relacion: str
    cardinalidad_origen: str
    cardinalidad_destino: str
    conector_origen: str
    conector_destino: str
    nombre: str | None = None
    materializacion_fk: list[MaterializacionFKCommand] | None = None


class CrearRelacionUseCase:
    def __init__(self, proyecto_repository: ProyectoRepository, diagrama_repository: DiagramaRepository,
                 clase_repository: ClaseRepository, relacion_repository: RelacionRepository, uow: UnitOfWork,
                 colaborador_repository: ColaboradorProyectoRepository | None = None,
                 atributo_repository: AtributoRepository | None = None,
                 referencia_fk_repository: ReferenciaFKRepository | None = None) -> None:
        self.proyecto_repository = proyecto_repository
        self.diagrama_repository = diagrama_repository
        self.clase_repository = clase_repository
        self.relacion_repository = relacion_repository
        self.uow = uow
        self.colaborador_repository = colaborador_repository
        self.atributo_repository = atributo_repository
        self.referencia_fk_repository = referencia_fk_repository

    def execute(
        self, command: CrearRelacionCommand, confirmar: bool = True
    ) -> Relacion:
        obtener_diagrama_autorizado(propietario_id=command.propietario_id, diagrama_id=command.diagrama_id,
            proyecto_repository=self.proyecto_repository, diagrama_repository=self.diagrama_repository,
            colaborador_repository=self.colaborador_repository, exigir_edicion=True)
        if self.relacion_repository.obtener_por_id(command.id_relacion):
            raise RelacionYaExisteException()
        for clase_id in (command.id_clase_origen, command.id_clase_destino):
            clase = self.clase_repository.obtener_por_id(clase_id)
            if clase is None or clase.id_diagrama != command.diagrama_id:
                raise ClaseNoEncontradaException()
        relaciones_existentes = self.relacion_repository.listar_por_diagrama(command.diagrama_id)
        ocupaciones = {
            (rel.id_clase_origen, Conector.a_handle_canonico(rel.conector_origen))
            for rel in relaciones_existentes
        }
        ocupaciones.update(
            (rel.id_clase_destino, Conector.a_handle_canonico(rel.conector_destino))
            for rel in relaciones_existentes
        )
        extremos_nuevos = {
            (command.id_clase_origen, Conector.a_handle_canonico(command.conector_origen)),
            (command.id_clase_destino, Conector.a_handle_canonico(command.conector_destino)),
        }
        if len(extremos_nuevos) != 2 or ocupaciones.intersection(extremos_nuevos):
            raise ConectorOcupadoException()
        relacion = Relacion.crear(id=command.id_relacion, id_diagrama=command.diagrama_id,
            id_clase_origen=command.id_clase_origen, id_clase_destino=command.id_clase_destino,
            tipo_relacion=command.tipo_relacion, cardinalidad_origen=command.cardinalidad_origen,
            cardinalidad_destino=command.cardinalidad_destino, conector_origen=command.conector_origen,
            conector_destino=command.conector_destino, nombre=command.nombre)
        self.relacion_repository.guardar(relacion)
        if self.atributo_repository is None or self.referencia_fk_repository is None:
            asegurar_materializacion_valida(relacion, [], lambda _: None)
            if confirmar:
                self.uow.commit()
            return relacion
        referencias = []
        for materializacion in command.materializacion_fk or []:
            atributo_fk_id = materializacion.id_atributo_fk
            if materializacion.atributo_fk_nuevo:
                if materializacion.id_clase_fk not in {
                    relacion.id_clase_origen,
                    relacion.id_clase_destino,
                }:
                    raise ClaseNoEncontradaException()
                nuevo = materializacion.atributo_fk_nuevo
                if self.atributo_repository.obtener_por_id(nuevo.id_atributo):
                    raise AtributoYaExisteException()
                attr_ref = self.atributo_repository.obtener_por_id(materializacion.id_atributo_referenciado)
                tipo_dato = nuevo.tipo_dato or (attr_ref.tipo_dato if attr_ref else "integer")
                longitud = nuevo.longitud if nuevo.longitud is not None else (attr_ref.longitud if attr_ref else None)
                precision = nuevo.precision if nuevo.precision is not None else (attr_ref.precision if attr_ref else None)
                escala = nuevo.escala if nuevo.escala is not None else (attr_ref.escala if attr_ref else None)
                existentes = self.atributo_repository.listar_por_clase(materializacion.id_clase_fk)
                self.atributo_repository.guardar(Atributo.crear(
                    id=nuevo.id_atributo, id_clase=materializacion.id_clase_fk, nombre=nuevo.nombre, tipo_dato=tipo_dato,
                    longitud=longitud, precision=precision, escala=escala,
                    permite_nulo=nuevo.permite_nulo, es_unico=nuevo.es_unico,
                    valor_por_defecto=nuevo.valor_por_defecto,
                    orden_de_posicion=(existentes[-1].orden_de_posicion + 1) if existentes else 1,
                    procedencia=ProcedenciaAtributo.SISTEMA_FK))
                atributo_fk_id = nuevo.id_atributo
            referencias.append(CrearReferenciaFKUseCase(
                self.proyecto_repository, self.diagrama_repository, self.relacion_repository,
                self.clase_repository, self.atributo_repository, self.referencia_fk_repository,
                self.uow, self.colaborador_repository).execute(CrearReferenciaFKCommand(
                    propietario_id=command.propietario_id, relacion_id=relacion.id,
                    id_referencia_fk=materializacion.id_referencia_fk, id_atributo_fk=atributo_fk_id,
                    id_atributo_referenciado=materializacion.id_atributo_referenciado,
                    on_delete=materializacion.on_delete, on_update=materializacion.on_update), confirmar=False))
        asegurar_materializacion_valida(relacion, referencias, self.atributo_repository.obtener_por_id)
        if confirmar:
            self.uow.commit()
        return relacion
