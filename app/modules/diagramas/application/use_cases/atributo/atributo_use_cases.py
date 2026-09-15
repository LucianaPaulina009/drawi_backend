from dataclasses import dataclass
from uuid import UUID
from app.modules.diagramas.application.queries.atributo.atributo_handlers import AtributoQuery,AtributoQueryHandler
from app.modules.diagramas.domain.entities.atributo import Atributo,NO_DEFINIDO
from app.modules.diagramas.domain.exceptions import ActualizacionAtributoVaciaException, OrdenAtributoFueraDeSecuenciaException
from app.modules.diagramas.domain.repositories.atributo_repository import AtributoRepository
from app.modules.diagramas.domain.repositories.clase_repository import ClaseRepository
from app.modules.diagramas.domain.repositories.diagrama_repository import DiagramaRepository
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import ProyectoRepository
from app.shared.application.ports import UnitOfWork

@dataclass(slots=True)
class AtributoCommand:
    propietario_id:str; clase_id:UUID; datos:dict; atributo_id:UUID|None=None
class AtributoUseCase:
    def __init__(self,p:ProyectoRepository,d:DiagramaRepository,c:ClaseRepository,a:AtributoRepository,u:UnitOfWork): self.q=AtributoQueryHandler(p,d,c,a);self.a=a;self.u=u
    def crear(self,cmd:AtributoCommand)->Atributo:
        self.q.clase_autorizada(AtributoQuery(cmd.propietario_id,cmd.clase_id)); datos=dict(cmd.datos); orden=datos.pop("orden_de_posicion",None)
        if orden is None: orden=(self.a.listar_por_clase(cmd.clase_id)[-1].orden_de_posicion+1) if self.a.listar_por_clase(cmd.clase_id) else 1
        atributos=self.a.listar_por_clase(cmd.clase_id)
        if orden > len(atributos) + 1: raise OrdenAtributoFueraDeSecuenciaException()
        if orden<=len(atributos):
            for x in atributos:
                if x.orden_de_posicion>=orden: x.orden_de_posicion+=1
            self.a.guardar_varios(atributos)
        nuevo=Atributo.crear(id_clase=cmd.clase_id,orden_de_posicion=orden,**datos); self.a.guardar(nuevo);self.u.commit();return nuevo
    def actualizar(self,cmd:AtributoCommand)->Atributo:
        if not cmd.datos: raise ActualizacionAtributoVaciaException()
        actual=self.q.obtener_entidad(AtributoQuery(cmd.propietario_id,cmd.clase_id,cmd.atributo_id)); orden=cmd.datos.get("orden_de_posicion",NO_DEFINIDO); actual.actualizar(**cmd.datos)
        if orden is not NO_DEFINIDO:
            otros=[x for x in self.a.listar_por_clase(cmd.clase_id) if x.id!=actual.id]
            if actual.orden_de_posicion > len(otros) + 1: raise OrdenAtributoFueraDeSecuenciaException()
            posicion=actual.orden_de_posicion; otros.insert(posicion-1,actual)
            for i,x in enumerate(otros,1): x.orden_de_posicion=i
            self.a.guardar_varios(otros)
        else: self.a.guardar(actual)
        self.u.commit();return actual
    def eliminar(self,cmd:AtributoCommand)->None:
        self.q.obtener_entidad(AtributoQuery(cmd.propietario_id,cmd.clase_id,cmd.atributo_id));self.a.eliminar(cmd.atributo_id);self.u.commit()
