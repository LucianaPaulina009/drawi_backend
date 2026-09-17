from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.diagramas.application.validaciones import obtener_diagrama_autorizado
from app.modules.diagramas.domain.entities.referencia_fk import ReferenciaFK
from app.modules.diagramas.domain.exceptions import (
    AtributoNoEncontradoException,
    AtributoNoPerteneceAClaseRelacionException,
    AtributoNoReferenciableException,
    ConfiguracionReferenciaFKInvalidaException,
    ReferenciaFKYaExisteException,
    RelacionNoEncontradaException,
    TipoAtributoIncompatibleException,
    VinculoReferenciaFKDuplicadoException,
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
from app.modules.diagramas.domain.value_objects.accion_referencial import (
    AccionReferencial,
)
from app.modules.gestion_colaboradores.domain.repositories.colaborador_proyecto_repository import (
    ColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)
from app.shared.application.ports import UnitOfWork


@dataclass(slots=True)
class CrearReferenciaFKCommand:
    propietario_id: str
    relacion_id: UUID
    id_referencia_fk: UUID
    id_atributo_fk: UUID
    id_atributo_referenciado: UUID
    on_delete: str = "NO_ACTION"
    on_update: str = "NO_ACTION"


class CrearReferenciaFKUseCase:
    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        diagrama_repository: DiagramaRepository,
        relacion_repository: RelacionRepository,
        clase_repository: ClaseRepository,
        atributo_repository: AtributoRepository,
        referencia_fk_repository: ReferenciaFKRepository,
        uow: UnitOfWork,
        colaborador_repository: ColaboradorProyectoRepository | None = None,
    ) -> None:
        self.proyecto_repository = proyecto_repository
        self.diagrama_repository = diagrama_repository
        self.relacion_repository = relacion_repository
        self.clase_repository = clase_repository
        self.atributo_repository = atributo_repository
        self.referencia_fk_repository = referencia_fk_repository
        self.uow = uow
        self.colaborador_repository = colaborador_repository

    def execute(self, command: CrearReferenciaFKCommand, *, confirmar: bool = True) -> ReferenciaFK:
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

        if self.referencia_fk_repository.obtener_por_id(command.id_referencia_fk) is not None:
            raise ReferenciaFKYaExisteException()

        if self.referencia_fk_repository.obtener_por_par(
            command.relacion_id, command.id_atributo_fk, command.id_atributo_referenciado
        ) is not None:
            raise VinculoReferenciaFKDuplicadoException()

        attr_fk = self.atributo_repository.obtener_por_id(command.id_atributo_fk)
        attr_ref = self.atributo_repository.obtener_por_id(command.id_atributo_referenciado)
        if attr_fk is None or attr_ref is None:
            raise AtributoNoEncontradoException()

        clases_participantes = {relacion.id_clase_origen, relacion.id_clase_destino}
        if (
            attr_fk.id_clase not in clases_participantes
            or attr_ref.id_clase not in clases_participantes
        ):
            raise AtributoNoPerteneceAClaseRelacionException()

        if attr_fk.tipo_dato != attr_ref.tipo_dato:
            raise TipoAtributoIncompatibleException()

        if not (attr_ref.es_llave_primaria or attr_ref.es_unico):
            raise AtributoNoReferenciableException()

        on_delete_val = AccionReferencial.validar(command.on_delete).value
        on_update_val = AccionReferencial.validar(command.on_update).value

        if (
            on_delete_val == AccionReferencial.SET_NULL.value
            or on_update_val == AccionReferencial.SET_NULL.value
        ) and not attr_fk.permite_nulo:
            raise ConfiguracionReferenciaFKInvalidaException(
                "La acción SET_NULL requiere que el atributo FK permita valores nulos."
            )

        if (
            on_delete_val == AccionReferencial.SET_DEFAULT.value
            or on_update_val == AccionReferencial.SET_DEFAULT.value
        ) and attr_fk.valor_por_defecto is None:
            raise ConfiguracionReferenciaFKInvalidaException(
                "La acción SET_DEFAULT requiere que el atributo FK tenga un valor por defecto configurado."
            )

        referencia = ReferenciaFK.crear(
            id=command.id_referencia_fk,
            id_relacion=command.relacion_id,
            id_atributo_fk=command.id_atributo_fk,
            id_atributo_referenciado=command.id_atributo_referenciado,
            on_delete=on_delete_val,
            on_update=on_update_val,
        )

        self.referencia_fk_repository.guardar(referencia)
        if confirmar:
            self.uow.commit()
        return referencia
