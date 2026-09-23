from uuid import UUID, uuid4
import pytest

from app.modules.gestion_colaboradores.application.ports.readers.miembros_proyecto_reader import (
    MiembroProyectoDTO,
    MiembrosProyectoReader,
)
from app.modules.gestion_colaboradores.application.queries.listar_miembros_proyecto import (
    ListarMiembrosProyectoQuery,
    ListarMiembrosProyectoQueryHandler,
)
from app.modules.gestion_colaboradores.application.use_cases.bloquear_colaborador import (
    BloquearColaboradorCommand,
    BloquearColaboradorUseCase,
)
from app.modules.gestion_colaboradores.application.use_cases.cambiar_rol_colaborador import (
    CambiarRolColaboradorCommand,
    CambiarRolColaboradorUseCase,
)
from app.modules.gestion_colaboradores.application.use_cases.desbloquear_colaborador import (
    DesbloquearColaboradorCommand,
    DesbloquearColaboradorUseCase,
)
from app.modules.gestion_colaboradores.application.use_cases.remover_colaborador import (
    RemoverColaboradorCommand,
    RemoverColaboradorUseCase,
)
from app.modules.gestion_colaboradores.domain.entities.colaborador_proyecto import ColaboradorProyecto
from app.modules.gestion_colaboradores.domain.exceptions import (
    ColaboradorNoEncontradoException,
    NoAutorizadoProyectoException,
    OperacionNoPermitidaPropietarioException,
)
from app.modules.gestion_colaboradores.domain.repositories.colaborador_proyecto_repository import (
    ColaboradorProyectoRepository,
)
from app.modules.gestion_colaboradores.domain.value_objects.estado_colaborador import EstadoColaborador
from app.modules.gestion_colaboradores.domain.value_objects.rol_colaborador import RolColaborador
from app.modules.gestion_proyectos.domain.entities.proyecto import Proyecto
from app.modules.gestion_proyectos.domain.exceptions import (
    ProyectoNoEncontradoException,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)
from app.shared.application.ports import UnitOfWork


class FakeUnitOfWork(UnitOfWork):
    def __init__(self):
        self.committed = False

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


class FakeProyectoRepository(ProyectoRepository):
    def __init__(self, proyectos: list[Proyecto] = None):
        self.proyectos = {p.id: p for p in (proyectos or [])}

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
        return False

    def guardar(self, proyecto: Proyecto) -> None:
        self.proyectos[proyecto.id] = proyecto

    def eliminar(self, proyecto_id: UUID) -> None:
        if proyecto_id in self.proyectos:
            del self.proyectos[proyecto_id]

    def actualizar_fecha_actividad(self, proyecto_id: UUID) -> None:
        pass



class FakeColaboradorProyectoRepository(ColaboradorProyectoRepository):
    def __init__(self, colaboradores: list[ColaboradorProyecto] = None):
        self.colaboradores = {c.id: c for c in (colaboradores or [])}

    def obtener_por_id(self, colaborador_id: UUID) -> ColaboradorProyecto | None:
        return self.colaboradores.get(colaborador_id)

    def obtener_por_proyecto_y_usuario(
        self, id_proyecto: UUID, id_usuario: str
    ) -> ColaboradorProyecto | None:
        for c in self.colaboradores.values():
            if c.id_proyecto == id_proyecto and c.id_usuario == id_usuario:
                return c
        return None

    def listar_por_proyecto(self, id_proyecto: UUID) -> list[ColaboradorProyecto]:
        return [c for c in self.colaboradores.values() if c.id_proyecto == id_proyecto]

    def guardar(self, colaborador: ColaboradorProyecto) -> None:
        self.colaboradores[colaborador.id] = colaborador

    def eliminar(self, colaborador_id: UUID) -> None:
        if colaborador_id in self.colaboradores:
            del self.colaboradores[colaborador_id]


class FakeMiembrosProyectoReader(MiembrosProyectoReader):
    def __init__(self, miembros: list[MiembroProyectoDTO] = None):
        self.miembros = miembros or []

    def listar_miembros_proyecto(self, id_proyecto: UUID) -> list[MiembroProyectoDTO]:
        return self.miembros


def test_entidad_colaborador_mutaciones():
    id_proy = uuid4()
    colab = ColaboradorProyecto.crear(
        id_proyecto=id_proy,
        id_usuario="usr-1",
        rol=RolColaborador.VER,
        estado=EstadoColaborador.ACTIVO,
    )
    assert colab.esta_activo()
    assert not colab.esta_bloqueado()

    colab.cambiar_rol(RolColaborador.EDITOR)
    assert colab.rol == RolColaborador.EDITOR

    colab.bloquear()
    assert colab.esta_bloqueado()
    assert colab.rol == RolColaborador.EDITOR  # Preserva el rol base

    colab.desbloquear()
    assert colab.esta_activo()
    assert colab.rol == RolColaborador.EDITOR


def test_cambiar_rol_exitoso():
    proy = Proyecto.crear(propietario_id="usr-owner", numero=0)
    colab = ColaboradorProyecto.crear(
        id_proyecto=proy.id,
        id_usuario="usr-member",
        rol=RolColaborador.VER,
    )
    repo_proy = FakeProyectoRepository([proy])
    repo_colab = FakeColaboradorProyectoRepository([colab])
    uow = FakeUnitOfWork()

    use_case = CambiarRolColaboradorUseCase(repo_proy, repo_colab, uow)
    use_case.execute(
        CambiarRolColaboradorCommand(
            propietario_id="usr-owner",
            proyecto_id=proy.id,
            colaborador_id=colab.id,
            nuevo_rol=RolColaborador.EDITOR,
        )
    )

    actualizado = repo_colab.obtener_por_id(colab.id)
    assert actualizado.rol == RolColaborador.EDITOR
    assert uow.committed is True


def test_blindaje_propietario_al_cambiar_rol():
    proy = Proyecto.crear(propietario_id="usr-owner", numero=0)
    repo_proy = FakeProyectoRepository([proy])
    repo_colab = FakeColaboradorProyectoRepository([])
    uow = FakeUnitOfWork()

    use_case = CambiarRolColaboradorUseCase(repo_proy, repo_colab, uow)
    with pytest.raises(OperacionNoPermitidaPropietarioException):
        use_case.execute(
            CambiarRolColaboradorCommand(
                propietario_id="usr-owner",
                proyecto_id=proy.id,
                colaborador_id=proy.id,  # Referencia al propietario
                nuevo_rol=RolColaborador.EDITOR,
            )
        )


def test_remover_colaborador_exitoso():
    proy = Proyecto.crear(propietario_id="usr-owner", numero=0)
    colab = ColaboradorProyecto.crear(
        id_proyecto=proy.id,
        id_usuario="usr-member",
    )
    repo_proy = FakeProyectoRepository([proy])
    repo_colab = FakeColaboradorProyectoRepository([colab])
    uow = FakeUnitOfWork()

    use_case = RemoverColaboradorUseCase(repo_proy, repo_colab, uow)
    use_case.execute(
        RemoverColaboradorCommand(
            propietario_id="usr-owner",
            proyecto_id=proy.id,
            colaborador_id=colab.id,
        )
    )

    assert repo_colab.obtener_por_id(colab.id) is None
    assert uow.committed is True


def test_bloquear_y_desbloquear_colaborador():
    proy = Proyecto.crear(propietario_id="usr-owner", numero=0)
    colab = ColaboradorProyecto.crear(
        id_proyecto=proy.id,
        id_usuario="usr-member",
        rol=RolColaborador.EDITOR,
    )
    repo_proy = FakeProyectoRepository([proy])
    repo_colab = FakeColaboradorProyectoRepository([colab])
    uow = FakeUnitOfWork()

    bloquear_uc = BloquearColaboradorUseCase(repo_proy, repo_colab, uow)
    bloquear_uc.execute(
        BloquearColaboradorCommand(
            propietario_id="usr-owner",
            proyecto_id=proy.id,
            colaborador_id=colab.id,
        )
    )

    colab_bloq = repo_colab.obtener_por_id(colab.id)
    assert colab_bloq.esta_bloqueado()
    assert colab_bloq.rol == RolColaborador.EDITOR

    desbloquear_uc = DesbloquearColaboradorUseCase(repo_proy, repo_colab, uow)
    desbloquear_uc.execute(
        DesbloquearColaboradorCommand(
            propietario_id="usr-owner",
            proyecto_id=proy.id,
            colaborador_id=colab.id,
        )
    )

    colab_desbloq = repo_colab.obtener_por_id(colab.id)
    assert colab_desbloq.esta_activo()
    assert colab_desbloq.rol == RolColaborador.EDITOR


def test_no_propietario_no_puede_gestionar_miembros():
    proy = Proyecto.crear(propietario_id="usr-owner", numero=0)
    colab = ColaboradorProyecto.crear(id_proyecto=proy.id, id_usuario="usr-member")
    repo_proy = FakeProyectoRepository([proy])
    repo_colab = FakeColaboradorProyectoRepository([colab])
    uow = FakeUnitOfWork()

    use_case = CambiarRolColaboradorUseCase(repo_proy, repo_colab, uow)
    with pytest.raises(NoAutorizadoProyectoException):
        use_case.execute(
            CambiarRolColaboradorCommand(
                propietario_id="usr-intruso",
                proyecto_id=proy.id,
                colaborador_id=colab.id,
                nuevo_rol=RolColaborador.COMENTARISTA,
            )
        )


def test_better_auth_user_sin_columnas_rol_ni_baneo():
    """Verifica que el modelo BetterAuthUser no defina columnas inexistentes como role o banned."""
    from app.shared.infrastructure.db.better_auth import BetterAuthUser

    campos = BetterAuthUser.model_fields.keys()
    assert "role" not in campos
    assert "banned" not in campos
    assert "banReason" not in campos
    assert "banExpires" not in campos
    assert "id" in campos
    assert "name" in campos
    assert "email" in campos
    assert "image" in campos
