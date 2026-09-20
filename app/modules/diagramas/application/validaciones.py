from uuid import UUID

from app.modules.diagramas.domain.entities.diagrama import Diagrama
from app.modules.diagramas.domain.exceptions import DiagramaNoEncontradoException
from app.modules.diagramas.domain.repositories.diagrama_repository import (
    DiagramaRepository,
)
from app.modules.gestion_colaboradores.domain.exceptions import (
    NoAutorizadoProyectoException,
    UsuarioBloqueadoException,
)
from app.modules.gestion_colaboradores.domain.repositories.colaborador_proyecto_repository import (
    ColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.domain.exceptions import (
    ProyectoNoEncontradoException,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)


def obtener_diagrama_autorizado(
    *,
    propietario_id: str,
    diagrama_id: UUID,
    proyecto_repository: ProyectoRepository,
    diagrama_repository: DiagramaRepository,
    colaborador_repository: ColaboradorProyectoRepository | None = None,
    exigir_edicion: bool = False,
) -> Diagrama:
    """Verifica el acceso Proyecto → Diagrama para el usuario autenticado (propietario o colaborador activo)."""
    diagrama = diagrama_repository.obtener_por_id(diagrama_id)
    if diagrama is None:
        raise DiagramaNoEncontradoException()
    proyecto = proyecto_repository.obtener_por_id(diagrama.id_proyecto)
    if proyecto is None:
        raise ProyectoNoEncontradoException()

    if proyecto.propietario_id != propietario_id:
        if colaborador_repository is not None:
            colaborador = colaborador_repository.obtener_por_proyecto_y_usuario(
                proyecto.id, propietario_id
            )
            if colaborador is None:
                raise ProyectoNoEncontradoException()
            if colaborador.esta_bloqueado():
                raise UsuarioBloqueadoException()
            if not colaborador.esta_activo():
                raise ProyectoNoEncontradoException()
            if exigir_edicion and not colaborador.rol.puede_editar():
                raise NoAutorizadoProyectoException(
                    "No tienes permisos de edición en este proyecto."
                )
        else:
            raise ProyectoNoEncontradoException()

    return diagrama


def validar_creacion_atributo(
    *,
    datos: dict,
    atributos_existentes: list,
) -> None:
    """Asegura que no se cree una segunda PK ni se promueva procedencia indebida."""
    from app.modules.diagramas.domain.exceptions import LlavePrimariaDuplicadaException
    from app.modules.diagramas.domain.value_objects.procedencia_atributo import ProcedenciaAtributo

    if datos.get("es_llave_primaria") is True:
        raise LlavePrimariaDuplicadaException(
            "No se permite crear una llave primaria adicional en una clase."
        )
    if "procedencia" in datos and datos["procedencia"] == ProcedenciaAtributo.SISTEMA_CLASE.value:
        raise LlavePrimariaDuplicadaException(
            "No se permite crear manualmente un atributo con procedencia sistema_clase."
        )


def validar_actualizacion_atributo(
    *,
    atributo,
    datos: dict,
    tiene_referencia_fk: bool = False,
) -> None:
    """Verifica qué campos están permitidos actualizar según el rol del atributo."""
    from app.modules.diagramas.domain.exceptions import (
        AtributoEstructuralInmutableException,
        LlavePrimariaDuplicadaException,
        LlavePrimariaProtegidaException,
    )
    from app.modules.diagramas.domain.value_objects.procedencia_atributo import ProcedenciaAtributo

    if atributo.procedencia == ProcedenciaAtributo.SISTEMA_CLASE.value or atributo.es_llave_primaria:
        campos_modificados = {k for k, v in datos.items() if v is not None and k != "nombre"}
        if campos_modificados:
            raise LlavePrimariaProtegidaException(
                "La llave primaria de la clase solo permite modificar su nombre."
            )

    if atributo.procedencia == ProcedenciaAtributo.SISTEMA_FK.value or tiene_referencia_fk:
        campos_modificados = {
            k for k, v in datos.items() if v is not None and k not in ("nombre", "orden_de_posicion")
        }
        if campos_modificados:
            raise AtributoEstructuralInmutableException(
                "Los atributos FK o con referencias activas solo permiten modificar su nombre u orden."
            )

    if datos.get("es_llave_primaria") is True and not atributo.es_llave_primaria:
        raise LlavePrimariaDuplicadaException(
            "No se permite convertir un atributo existente en llave primaria."
        )


def validar_eliminacion_atributo(atributo) -> None:
    """Impide la eliminación directa de llaves estructurales de una clase."""
    from app.modules.diagramas.domain.exceptions import (
        LlaveForaneaProtegidaException,
        LlavePrimariaProtegidaException,
    )
    from app.modules.diagramas.domain.value_objects.procedencia_atributo import ProcedenciaAtributo

    if atributo.procedencia == ProcedenciaAtributo.SISTEMA_CLASE.value or atributo.es_llave_primaria:
        raise LlavePrimariaProtegidaException(
            "No se puede eliminar la llave primaria del sistema de una clase."
        )
    if atributo.procedencia == ProcedenciaAtributo.SISTEMA_FK.value:
        raise LlaveForaneaProtegidaException()

