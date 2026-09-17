from dataclasses import dataclass
from uuid import UUID
from app.modules.diagramas.application.queries.atributo.atributo_handlers import AtributoQuery,AtributoQueryHandler
from app.modules.diagramas.domain.entities.atributo import Atributo,NO_DEFINIDO
from app.modules.diagramas.domain.exceptions import (
    ActualizacionAtributoVaciaException,
    AtributoYaExisteException,
    OrdenAtributoFueraDeSecuenciaException,
    MaterializacionRelacionRequeridaException,
)
from app.modules.diagramas.domain.repositories.atributo_repository import AtributoRepository
from app.modules.diagramas.domain.repositories.clase_repository import ClaseRepository
from app.modules.diagramas.domain.repositories.diagrama_repository import DiagramaRepository
from app.modules.diagramas.domain.repositories.referencia_fk_repository import (
    ReferenciaFKRepository,
)
from app.modules.diagramas.domain.repositories.relacion_repository import RelacionRepository
from app.modules.diagramas.application.use_cases.relacion.materializacion import asegurar_materializacion_valida
from app.modules.gestion_colaboradores.domain.repositories.colaborador_proyecto_repository import (
    ColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import ProyectoRepository
from app.shared.application.ports import UnitOfWork

@dataclass(slots=True)
class AtributoCommand:
    propietario_id: str
    clase_id: UUID
    datos: dict
    atributo_id: UUID | None = None

class AtributoUseCase:
    def __init__(
        self,
        p: ProyectoRepository,
        d: DiagramaRepository,
        c: ClaseRepository,
        a: AtributoRepository,
        u: UnitOfWork,
        col: ColaboradorProyectoRepository | None = None,
        rfk: ReferenciaFKRepository | None = None,
        relacion_repository: RelacionRepository | None = None,
    ):
        self.q = AtributoQueryHandler(p, d, c, a, col)
        self.a = a
        self.u = u
        self.rfk = rfk
        self.relaciones = relacion_repository

    def crear(self, cmd: AtributoCommand) -> Atributo:
        self.q.clase_autorizada(AtributoQuery(cmd.propietario_id, cmd.clase_id), exigir_edicion=True)
        datos = dict(cmd.datos)
        id_atributo = datos.pop("id_atributo", None) or cmd.atributo_id
        if id_atributo is not None and self.a.obtener_por_id(id_atributo) is not None:
            raise AtributoYaExisteException()
        orden = datos.pop("orden_de_posicion", None)
        atributos = self.a.listar_por_clase(cmd.clase_id)
        if orden is None:
            orden = (atributos[-1].orden_de_posicion + 1) if atributos else 1
        if orden > len(atributos) + 1:
            raise OrdenAtributoFueraDeSecuenciaException()
        if orden <= len(atributos):
            for x in atributos:
                if x.orden_de_posicion >= orden:
                    x.orden_de_posicion += 1
            self.a.guardar_varios(atributos)
        nuevo = Atributo.crear(id=id_atributo, id_clase=cmd.clase_id, orden_de_posicion=orden, **datos)
        self.a.guardar(nuevo)
        self.u.commit()
        return nuevo

    def actualizar(self, cmd: AtributoCommand) -> Atributo:
        if not cmd.datos:
            raise ActualizacionAtributoVaciaException()
        actual = self.q.obtener_entidad(AtributoQuery(cmd.propietario_id, cmd.clase_id, cmd.atributo_id), exigir_edicion=True)
        orden = cmd.datos.get("orden_de_posicion", NO_DEFINIDO)
        actual.actualizar(**cmd.datos)
        if orden is not NO_DEFINIDO:
            otros = [x for x in self.a.listar_por_clase(cmd.clase_id) if x.id != actual.id]
            if actual.orden_de_posicion > len(otros) + 1:
                raise OrdenAtributoFueraDeSecuenciaException()
            posicion = actual.orden_de_posicion
            otros.insert(posicion - 1, actual)
            for i, x in enumerate(otros, 1):
                x.orden_de_posicion = i
            self.a.guardar_varios(otros)
        else:
            self.a.guardar(actual)
        self.u.commit()
        return actual

    def eliminar(self, cmd: AtributoCommand) -> None:
        self.q.obtener_entidad(AtributoQuery(cmd.propietario_id, cmd.clase_id, cmd.atributo_id), exigir_edicion=True)
        if self.rfk is not None and cmd.atributo_id is not None:
            referencias = self.rfk.listar_por_atributo(cmd.atributo_id)
            self.rfk.eliminar_por_atributo(cmd.atributo_id)
            if self.relaciones is not None:
                for referencia in referencias:
                    relacion = self.relaciones.obtener_por_id(referencia.id_relacion)
                    if relacion is None:
                        continue
                    try:
                        asegurar_materializacion_valida(
                            relacion,
                            self.rfk.listar_por_relacion(relacion.id),
                            self.a.obtener_por_id,
                        )
                    except MaterializacionRelacionRequeridaException:
                        self.rfk.eliminar_por_relacion(relacion.id)
                        self.relaciones.eliminar(relacion.id)
        self.a.eliminar(cmd.atributo_id)
        restantes = self.a.listar_por_clase(cmd.clase_id)
        for i, x in enumerate(restantes, 1):
            x.orden_de_posicion = i
        if restantes:
            self.a.guardar_varios(restantes)
        self.u.commit()
