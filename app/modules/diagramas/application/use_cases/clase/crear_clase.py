from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.diagramas.application.validaciones import obtener_diagrama_autorizado
from app.modules.diagramas.domain.entities.atributo import Atributo
from app.modules.diagramas.domain.entities.clase import Clase
from app.modules.diagramas.domain.exceptions import (
    AtributoYaExisteException,
    ClaseYaExisteException,
)
from app.modules.diagramas.domain.repositories.atributo_repository import (
    AtributoRepository,
)
from app.modules.diagramas.domain.repositories.clase_repository import ClaseRepository
from app.modules.diagramas.domain.repositories.diagrama_repository import (
    DiagramaRepository,
)
from app.modules.diagramas.domain.value_objects.tipo_dato import TipoDato
from app.modules.diagramas.domain.value_objects.procedencia_atributo import ProcedenciaAtributo
from app.modules.gestion_colaboradores.domain.repositories.colaborador_proyecto_repository import (
    ColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)
from app.shared.application.ports import UnitOfWork


@dataclass(slots=True)
class CrearClaseCommand:
    propietario_id: str
    diagrama_id: UUID
    posicion_x: float
    posicion_y: float
    ancho: float = 280.0
    nombre: str = "Tabla"
    id_clase: UUID | None = None
    id_atributo_inicial: UUID | None = None


class CrearClaseUseCase:
    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        diagrama_repository: DiagramaRepository,
        clase_repository: ClaseRepository,
        atributo_repository: AtributoRepository,
        uow: UnitOfWork,
        colaborador_repository: ColaboradorProyectoRepository | None = None,
    ) -> None:
        self.proyecto_repository = proyecto_repository
        self.diagrama_repository = diagrama_repository
        self.clase_repository = clase_repository
        self.atributo_repository = atributo_repository
        self.uow = uow
        self.colaborador_repository = colaborador_repository

    def execute(self, command: CrearClaseCommand) -> tuple[Clase, list[Atributo]]:
        obtener_diagrama_autorizado(
            propietario_id=command.propietario_id,
            diagrama_id=command.diagrama_id,
            proyecto_repository=self.proyecto_repository,
            diagrama_repository=self.diagrama_repository,
            colaborador_repository=self.colaborador_repository,
            exigir_edicion=True,
        )
        if command.id_clase is not None:
            if self.clase_repository.obtener_por_id(command.id_clase) is not None:
                raise ClaseYaExisteException()
        if command.id_atributo_inicial is not None:
            if self.atributo_repository.obtener_por_id(command.id_atributo_inicial) is not None:
                raise AtributoYaExisteException()

        clase = Clase.crear(
            id=command.id_clase,
            id_diagrama=command.diagrama_id,
            nombre=command.nombre or "Tabla",
            posicion_x=command.posicion_x,
            posicion_y=command.posicion_y,
            ancho=command.ancho or 280.0,
        )
        self.clase_repository.guardar(clase)

        atributo_inicial = Atributo.crear(
            id=command.id_atributo_inicial,
            id_clase=clase.id,
            nombre="id",
            tipo_dato=TipoDato.INTEGER,
            orden_de_posicion=1,
            es_llave_primaria=True,
            permite_nulo=False,
            es_unico=False,
            procedencia=ProcedenciaAtributo.SISTEMA_CLASE,
        )
        self.atributo_repository.guardar(atributo_inicial)
        self.uow.commit()
        return clase, [atributo_inicial]
