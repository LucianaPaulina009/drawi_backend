from __future__ import annotations

from dataclasses import asdict, dataclass
from uuid import UUID

from app.modules.diagramas.application.services.geometria_conectores import (
    calcular_mejores_conectores,
)
from app.modules.diagramas.application.services.idempotencia_diagrama import IdempotenciaDiagramaService
from app.modules.diagramas.application.validaciones import obtener_diagrama_autorizado
from app.modules.diagramas.domain.entities.atributo import Atributo
from app.modules.diagramas.domain.entities.clase import Clase
from app.modules.diagramas.domain.entities.estructura_relacion_nm import EstructuraRelacionNm
from app.modules.diagramas.domain.entities.relacion import Relacion
from app.modules.diagramas.domain.entities.referencia_fk import ReferenciaFK
from app.modules.diagramas.domain.exceptions import AtributoNoReferenciableException, ClaseNoEncontradaException, ClaseYaExisteException
from app.modules.diagramas.domain.repositories.atributo_repository import AtributoRepository
from app.modules.diagramas.domain.repositories.clase_repository import ClaseRepository
from app.modules.diagramas.domain.repositories.diagrama_repository import DiagramaRepository
from app.modules.diagramas.domain.repositories.estructura_relacion_nm_repository import EstructuraRelacionNmRepository
from app.modules.diagramas.domain.repositories.relacion_repository import RelacionRepository
from app.modules.diagramas.domain.repositories.referencia_fk_repository import ReferenciaFKRepository
from app.modules.diagramas.domain.value_objects.procedencia_atributo import ProcedenciaAtributo
from app.modules.gestion_colaboradores.domain.repositories.colaborador_proyecto_repository import ColaboradorProyectoRepository
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import ProyectoRepository
from app.shared.application.ports import UnitOfWork


@dataclass(slots=True)
class CrearEstructuraRelacionNmCommand:
    propietario_id: str
    diagrama_id: UUID
    action_id: UUID
    id_estructura: UUID
    id_clase_origen: UUID
    id_clase_destino: UUID
    id_clase_intermedia: UUID
    id_atributo_inicial: UUID
    id_atributo_fk_origen: UUID
    id_atributo_fk_destino: UUID
    id_relacion_origen: UUID
    id_relacion_destino: UUID
    id_referencia_fk_origen: UUID
    id_referencia_fk_destino: UUID
    id_atributo_referenciado_origen: UUID
    id_atributo_referenciado_destino: UUID
    nombre_intermedia: str
    posicion_x: float
    posicion_y: float
    ancho: float = 280.0
    conector_origen: str | None = None
    conector_destino: str | None = None


class CrearEstructuraRelacionNmUseCase:
    def __init__(self, proyecto_repository: ProyectoRepository, diagrama_repository: DiagramaRepository,
                 clase_repository: ClaseRepository, atributo_repository: AtributoRepository,
                 relacion_repository: RelacionRepository, referencia_fk_repository: ReferenciaFKRepository,
                 estructura_repository: EstructuraRelacionNmRepository, idempotencia: IdempotenciaDiagramaService,
                 uow: UnitOfWork, colaborador_repository: ColaboradorProyectoRepository | None = None) -> None:
        self.proyecto_repository = proyecto_repository
        self.diagrama_repository = diagrama_repository
        self.clase_repository = clase_repository
        self.atributo_repository = atributo_repository
        self.relacion_repository = relacion_repository
        self.referencia_fk_repository = referencia_fk_repository
        self.estructura_repository = estructura_repository
        self.idempotencia = idempotencia
        self.uow = uow
        self.colaborador_repository = colaborador_repository

    def execute(
        self, command: CrearEstructuraRelacionNmCommand, confirmar: bool = True
    ) -> dict:
        payload = {nombre: str(valor) for nombre, valor in asdict(command).items() if nombre != "propietario_id"}
        anterior = self.idempotencia.confirmar_o_recuperar(action_id=command.action_id, usuario_id=command.propietario_id, diagrama_id=command.diagrama_id, payload=payload)
        if anterior is not None:
            return anterior
        obtener_diagrama_autorizado(propietario_id=command.propietario_id, diagrama_id=command.diagrama_id,
            proyecto_repository=self.proyecto_repository, diagrama_repository=self.diagrama_repository,
            colaborador_repository=self.colaborador_repository, exigir_edicion=True)
        origen = self.clase_repository.obtener_por_id(command.id_clase_origen)
        destino = self.clase_repository.obtener_por_id(command.id_clase_destino)
        if origen is None or destino is None or origen.id_diagrama != command.diagrama_id or destino.id_diagrama != command.diagrama_id:
            raise ClaseNoEncontradaException()
        if self.clase_repository.obtener_por_id(command.id_clase_intermedia):
            raise ClaseYaExisteException()
        attr_origen = self.atributo_repository.obtener_por_id(command.id_atributo_referenciado_origen)
        attr_destino = self.atributo_repository.obtener_por_id(command.id_atributo_referenciado_destino)
        if not attr_origen or not attr_destino or attr_origen.id_clase != origen.id or attr_destino.id_clase != destino.id:
            raise AtributoNoReferenciableException()
        if not (attr_origen.es_llave_primaria or attr_origen.es_unico) or not (attr_destino.es_llave_primaria or attr_destino.es_unico):
            raise AtributoNoReferenciableException()
        if origen.id == destino.id or origen.nombre.lower() == destino.nombre.lower():
            nombre_fk_origen = f"{origen.nombre.lower()}_origen_id"
            nombre_fk_destino = f"{destino.nombre.lower()}_destino_id"
        else:
            nombre_fk_origen = f"{origen.nombre.lower()}_id"
            nombre_fk_destino = f"{destino.nombre.lower()}_id"

        intermedia = Clase.crear(
            id=command.id_clase_intermedia,
            id_diagrama=command.diagrama_id,
            nombre=command.nombre_intermedia,
            posicion_x=command.posicion_x,
            posicion_y=command.posicion_y,
            ancho=command.ancho,
        )
        self.clase_repository.guardar(intermedia)
        self.atributo_repository.guardar(
            Atributo.crear(
                id=command.id_atributo_inicial,
                id_clase=intermedia.id,
                nombre="id",
                tipo_dato="integer",
                orden_de_posicion=1,
                es_llave_primaria=True,
                permite_nulo=False,
                procedencia=ProcedenciaAtributo.SISTEMA_CLASE,
            )
        )
        fk_origen = Atributo.crear(
            id=command.id_atributo_fk_origen,
            id_clase=intermedia.id,
            nombre=nombre_fk_origen,
            tipo_dato=attr_origen.tipo_dato,
            longitud=attr_origen.longitud,
            precision=attr_origen.precision,
            escala=attr_origen.escala,
            orden_de_posicion=2,
            permite_nulo=False,
            procedencia=ProcedenciaAtributo.SISTEMA_FK,
        )
        fk_destino = Atributo.crear(
            id=command.id_atributo_fk_destino,
            id_clase=intermedia.id,
            nombre=nombre_fk_destino,
            tipo_dato=attr_destino.tipo_dato,
            longitud=attr_destino.longitud,
            precision=attr_destino.precision,
            escala=attr_destino.escala,
            orden_de_posicion=3,
            permite_nulo=False,
            procedencia=ProcedenciaAtributo.SISTEMA_FK,
        )
        self.atributo_repository.guardar(fk_origen)
        self.atributo_repository.guardar(fk_destino)

        conector_orig = command.conector_origen
        conector_dest = command.conector_destino
        if not conector_orig or not conector_dest:
            relaciones_existentes = self.relacion_repository.listar_por_diagrama(command.diagrama_id)
            calc_orig, calc_dest = calcular_mejores_conectores(
                origen, destino, relaciones_existentes
            )
            conector_orig = conector_orig or calc_orig
            conector_dest = conector_dest or calc_dest

        rel_origen = Relacion.crear(
            id=command.id_relacion_origen,
            id_diagrama=command.diagrama_id,
            id_clase_origen=origen.id,
            id_clase_destino=intermedia.id,
            tipo_relacion="asociacion",
            cardinalidad_origen="1",
            cardinalidad_destino="0..*",
            conector_origen=conector_orig,
            conector_destino="left",
            nombre="Asociación",
        )
        rel_destino = Relacion.crear(
            id=command.id_relacion_destino,
            id_diagrama=command.diagrama_id,
            id_clase_origen=destino.id,
            id_clase_destino=intermedia.id,
            tipo_relacion="asociacion",
            cardinalidad_origen="1",
            cardinalidad_destino="0..*",
            conector_origen=conector_dest,
            conector_destino="left",
            nombre="Asociación",
        )
        self.relacion_repository.guardar(rel_origen)
        self.relacion_repository.guardar(rel_destino)

        self.referencia_fk_repository.guardar(
            ReferenciaFK.crear(
                id=command.id_referencia_fk_origen,
                id_relacion=rel_origen.id,
                id_atributo_fk=fk_origen.id,
                id_atributo_referenciado=attr_origen.id,
            )
        )
        self.referencia_fk_repository.guardar(
            ReferenciaFK.crear(
                id=command.id_referencia_fk_destino,
                id_relacion=rel_destino.id,
                id_atributo_fk=fk_destino.id,
                id_atributo_referenciado=attr_destino.id,
            )
        )
        estructura = EstructuraRelacionNm(
            id=command.id_estructura,
            id_diagrama=command.diagrama_id,
            id_clase_origen=origen.id,
            id_clase_destino=destino.id,
            id_clase_intermedia=intermedia.id,
            id_relacion_origen=rel_origen.id,
            id_relacion_destino=rel_destino.id,
        )
        self.estructura_repository.guardar(estructura)
        respuesta = {
            "id": str(estructura.id),
            "id_clase_intermedia": str(intermedia.id),
            "id_relacion_origen": str(rel_origen.id),
            "id_relacion_destino": str(rel_destino.id),
        }
        if confirmar:
            self.idempotencia.registrar_confirmacion(
                action_id=command.action_id,
                usuario_id=command.propietario_id,
                diagrama_id=command.diagrama_id,
                payload=payload,
                respuesta=respuesta,
            )
            self.uow.commit()
        return respuesta
