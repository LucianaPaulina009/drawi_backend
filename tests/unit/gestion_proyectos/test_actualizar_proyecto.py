from uuid import UUID, uuid4
import pytest

from app.modules.gestion_proyectos.application.use_cases.proyecto.actualizar_proyecto import (
    ActualizarProyectoCommand,
    ActualizarProyectoUseCase,
)
from app.modules.gestion_proyectos.domain.entities.proyecto import (
    ColorProyecto,
    IconoProyecto,
    Proyecto,
)
from app.modules.gestion_proyectos.domain.exceptions import (
    ActualizacionProyectoVaciaException,
    NombreProyectoInvalidoException,
    ProyectoNoEncontradoException,
    SlugProyectoEnConflictoException,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)
from app.shared.application.ports import UnitOfWork


class FakeUnitOfWork(UnitOfWork):
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


class FakeProyectoRepository(ProyectoRepository):
    def __init__(self, proyectos: list[Proyecto] = None):
        self.proyectos = {p.id: p for p in (proyectos or [])}
        self.historico_slugs: set[tuple[str, str, UUID]] = {
            (p.propietario_id, p.slug, p.id) for p in (proyectos or [])
        }

    def contar_historicos_por_propietario(self, propietario_id: str) -> int:
        return len([p for p in self.proyectos.values() if p.propietario_id == propietario_id])

    def obtener_por_id(self, proyecto_id: UUID) -> Proyecto | None:
        return self.proyectos.get(proyecto_id)

    def obtener_por_propietario_y_slug(self, propietario_id: str, slug: str) -> Proyecto | None:
        for p in self.proyectos.values():
            if p.propietario_id == propietario_id and p.slug == slug:
                return p
        return None

    def existe_slug_en_historico(self, propietario_id: str, slug: str, excluir_id: UUID | None = None) -> bool:
        return any(
            prop == propietario_id and s == slug and pid != excluir_id
            for prop, s, pid in self.historico_slugs
        )

    def guardar(self, proyecto: Proyecto) -> None:
        self.proyectos[proyecto.id] = proyecto
        self.historico_slugs.add((proyecto.propietario_id, proyecto.slug, proyecto.id))

    def eliminar(self, proyecto_id: UUID) -> None:
        if proyecto_id in self.proyectos:
            del self.proyectos[proyecto_id]

    def actualizar_fecha_actividad(self, proyecto_id: UUID) -> None:
        pass



def test_actualizar_solo_color_e_icono():
    proyecto = Proyecto.crear(propietario_id="usr-1", numero=0)
    repo = FakeProyectoRepository([proyecto])
    uow = FakeUnitOfWork()

    use_case = ActualizarProyectoUseCase(repo, uow)
    use_case.execute(
        ActualizarProyectoCommand(
            propietario_id="usr-1",
            proyecto_id=proyecto.id,
            color=ColorProyecto.rojo,
            icono=IconoProyecto.dinero,
        )
    )

    actualizado = repo.obtener_por_id(proyecto.id)
    assert actualizado.color == ColorProyecto.rojo
    assert actualizado.icono == IconoProyecto.dinero
    assert actualizado.nombre == "Nuevo Proyecto 0"
    assert actualizado.slug == "nuevo-proyecto-0"
    assert uow.committed is True


def test_actualizar_renombrar_regenera_slug():
    proyecto = Proyecto.crear(propietario_id="usr-1", numero=0)
    repo = FakeProyectoRepository([proyecto])
    uow = FakeUnitOfWork()

    use_case = ActualizarProyectoUseCase(repo, uow)
    use_case.execute(
        ActualizarProyectoCommand(
            propietario_id="usr-1",
            proyecto_id=proyecto.id,
            nombre="Diagrama de Arquitectura",
        )
    )

    actualizado = repo.obtener_por_id(proyecto.id)
    assert actualizado.nombre == "Diagrama de Arquitectura"
    assert actualizado.slug == "diagrama-de-arquitectura"


def test_actualizar_desambiguacion_slug():
    p1 = Proyecto(
        id=uuid4(),
        propietario_id="usr-1",
        nombre="Diagrama",
        color=ColorProyecto.celeste,
        icono=IconoProyecto.caja,
        slug="diagrama",
    )
    p2 = Proyecto(
        id=uuid4(),
        propietario_id="usr-1",
        nombre="Otro",
        color=ColorProyecto.celeste,
        icono=IconoProyecto.caja,
        slug="otro",
    )
    repo = FakeProyectoRepository([p1, p2])
    uow = FakeUnitOfWork()

    use_case = ActualizarProyectoUseCase(repo, uow)
    use_case.execute(
        ActualizarProyectoCommand(
            propietario_id="usr-1",
            proyecto_id=p2.id,
            nombre="Diagrama",
        )
    )

    actualizado = repo.obtener_por_id(p2.id)
    assert actualizado.slug == "diagrama-1"


def test_actualizar_vacio_lanza_excepcion():
    proyecto = Proyecto.crear(propietario_id="usr-1", numero=0)
    repo = FakeProyectoRepository([proyecto])
    uow = FakeUnitOfWork()

    use_case = ActualizarProyectoUseCase(repo, uow)
    with pytest.raises(ActualizacionProyectoVaciaException):
        use_case.execute(
            ActualizarProyectoCommand(
                propietario_id="usr-1",
                proyecto_id=proyecto.id,
            )
        )


def test_actualizar_nombre_invalido_lanza_excepcion():
    proyecto = Proyecto.crear(propietario_id="usr-1", numero=0)
    repo = FakeProyectoRepository([proyecto])
    uow = FakeUnitOfWork()

    use_case = ActualizarProyectoUseCase(repo, uow)
    with pytest.raises(NombreProyectoInvalidoException):
        use_case.execute(
            ActualizarProyectoCommand(
                propietario_id="usr-1",
                proyecto_id=proyecto.id,
                nombre="   ",
            )
        )


def test_actualizar_proyecto_ajeno_lanza_404():
    proyecto = Proyecto.crear(propietario_id="usr-ajeno", numero=0)
    repo = FakeProyectoRepository([proyecto])
    uow = FakeUnitOfWork()

    use_case = ActualizarProyectoUseCase(repo, uow)
    with pytest.raises(ProyectoNoEncontradoException):
        use_case.execute(
            ActualizarProyectoCommand(
                propietario_id="usr-1",
                proyecto_id=proyecto.id,
                nombre="Nuevo Nombre",
            )
        )
