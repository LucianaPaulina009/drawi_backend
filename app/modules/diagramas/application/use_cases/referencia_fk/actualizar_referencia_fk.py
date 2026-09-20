from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.modules.diagramas.application.validaciones import obtener_diagrama_autorizado
from app.modules.diagramas.application.use_cases.relacion.materializacion import (
    asegurar_materializacion_valida,
)
from app.modules.diagramas.domain.entities.referencia_fk import (
    NO_DEFINIDO,
    ReferenciaFK,
)
from app.modules.diagramas.domain.exceptions import (
    AtributoNoEncontradoException,
    AtributoNoPerteneceAClaseRelacionException,
    AtributoNoReferenciableException,
    ConfiguracionReferenciaFKInvalidaException,
    ReferenciaFKEstructuralInmutableException,
    ReferenciaFKNoEncontradaException,
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
class ActualizarReferenciaFKCommand:
    propietario_id: str
    relacion_id: UUID
    referencia_id: UUID
    id_atributo_fk: UUID | None = None
    id_atributo_referenciado: UUID | None = None
    on_delete: str | None = None
    on_update: str | None = None


class ActualizarReferenciaFKUseCase:
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

    def execute(self, command: ActualizarReferenciaFKCommand) -> ReferenciaFK:
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

        raise ReferenciaFKEstructuralInmutableException(
            "Las referencias FK son inmutables estructuralmente una vez creadas."
        )


        nuevo_fk = command.id_atributo_fk or referencia.id_atributo_fk
        nuevo_ref = command.id_atributo_referenciado or referencia.id_atributo_referenciado
        nuevo_on_delete = (
            AccionReferencial.validar(command.on_delete).value
            if command.on_delete is not None
            else referencia.on_delete
        )
        nuevo_on_update = (
            AccionReferencial.validar(command.on_update).value
            if command.on_update is not None
            else referencia.on_update
        )

        # Validación de unicidad de par activo sin auto-conflicto
        existente = self.referencia_fk_repository.obtener_por_par(
            command.relacion_id, nuevo_fk, nuevo_ref
        )
        if existente is not None and existente.id != command.referencia_id:
            raise VinculoReferenciaFKDuplicadoException()

        attr_fk = self.atributo_repository.obtener_por_id(nuevo_fk)
        attr_ref = self.atributo_repository.obtener_por_id(nuevo_ref)
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

        if (
            nuevo_on_delete == AccionReferencial.SET_NULL.value
            or nuevo_on_update == AccionReferencial.SET_NULL.value
        ) and not attr_fk.permite_nulo:
            raise ConfiguracionReferenciaFKInvalidaException(
                "La acción SET_NULL requiere que el atributo FK permita valores nulos."
            )

        if (
            nuevo_on_delete == AccionReferencial.SET_DEFAULT.value
            or nuevo_on_update == AccionReferencial.SET_DEFAULT.value
        ) and attr_fk.valor_por_defecto is None:
            raise ConfiguracionReferenciaFKInvalidaException(
                "La acción SET_DEFAULT requiere que el atributo FK tenga un valor por defecto configurado."
            )

        referencia.actualizar(
            id_atributo_fk=command.id_atributo_fk or NO_DEFINIDO,
            id_atributo_referenciado=command.id_atributo_referenciado or NO_DEFINIDO,
            on_delete=command.on_delete or NO_DEFINIDO,
            on_update=command.on_update or NO_DEFINIDO,
        )

        referencias_finales = [
            item
            for item in self.referencia_fk_repository.listar_por_relacion(relacion.id)
            if item.id != referencia.id
        ] + [referencia]
        asegurar_materializacion_valida(
            relacion,
            referencias_finales,
            self.atributo_repository.obtener_por_id,
        )
        self.referencia_fk_repository.guardar(referencia)
        self.uow.commit()
        return referencia
