from uuid import UUID, uuid4
import pytest

from app.modules.gestion_proyectos.application.use_cases.proyecto.agregar_proyecto_favorito import (
    AgregarProyectoFavoritoCommand,
    AgregarProyectoFavoritoUseCase,
)
from app.modules.gestion_proyectos.application.use_cases.proyecto.desmarcar_proyecto_favorito import (
    DesmarcarProyectoFavoritoCommand,
    DesmarcarProyectoFavoritoUseCase,
)
from app.modules.gestion_proyectos.domain.entities.proyecto import Proyecto
from app.modules.gestion_proyectos.domain.entities.proyecto_favorito import (
    ProyectoFavorito,
)
from app.modules.gestion_proyectos.domain.exceptions import ProyectoNoEncontradoException
from app.modules.gestion_proyectos.domain.repositories.proyecto_favorito_repository import (
    ProyectoFavoritoRepository,
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
        self.proyectos = proyectos or []

    def contar_historicos_por_propietario(self, propietario_id: str) -> int:
        return len([p for p in self.proyectos if p.propietario_id == propietario_id])

    def obtener_por_id(self, proyecto_id: UUID) -> Proyecto | None:
        for p in self.proyectos:
            if p.id == proyecto_id:
                return p
        return None

    def obtener_por_propietario_y_slug(self, propietario_id: str, slug: str) -> Proyecto | None:
        for p in self.proyectos:
            if p.propietario_id == propietario_id and p.slug == slug:
                return p
        return None

    def existe_slug_en_historico(self, propietario_id: str, slug: str, excluir_id: UUID | None = None) -> bool:
        return any(p.propietario_id == propietario_id and p.slug == slug and p.id != excluir_id for p in self.proyectos)

    def guardar(self, proyecto: Proyecto) -> None:
        self.proyectos.append(proyecto)

    def eliminar(self, proyecto_id: UUID) -> None:
        self.proyectos = [p for p in self.proyectos if p.id != proyecto_id]

    def actualizar_fecha_actividad(self, proyecto_id: UUID) -> None:
        pass



class FakeProyectoFavoritoRepository(ProyectoFavoritoRepository):
    def __init__(self):
        self.favoritos_activos: dict[tuple[str, UUID], ProyectoFavorito] = {}
        self.favoritos_eliminados: dict[tuple[str, UUID], ProyectoFavorito] = {}

    def obtener_activo(self, usuario_id: str, proyecto_id: UUID) -> ProyectoFavorito | None:
        return self.favoritos_activos.get((usuario_id, proyecto_id))

    def obtener_eliminado(self, usuario_id: str, proyecto_id: UUID) -> ProyectoFavorito | None:
        return self.favoritos_eliminados.get((usuario_id, proyecto_id))

    def guardar(self, favorito: ProyectoFavorito) -> None:
        self.favoritos_activos[(favorito.usuario_id, favorito.proyecto_id)] = favorito

    def restaurar(self, favorito_id: UUID) -> None:
        for clave, fav in list(self.favoritos_eliminados.items()):
            if fav.id == favorito_id:
                del self.favoritos_eliminados[clave]
                self.favoritos_activos[clave] = fav

    def eliminar(self, usuario_id: str, proyecto_id: UUID) -> None:
        clave = (usuario_id, proyecto_id)
        if clave in self.favoritos_activos:
            fav = self.favoritos_activos.pop(clave)
            self.favoritos_eliminados[clave] = fav


def test_entidad_proyecto_favorito_crear():
    proj_id = uuid4()
    fav = ProyectoFavorito.crear(usuario_id="usr-1", proyecto_id=proj_id)

    assert isinstance(fav.id, UUID)
    assert fav.usuario_id == "usr-1"
    assert fav.proyecto_id == proj_id


def test_agregar_favorito_nuevo():
    proyecto = Proyecto.crear(propietario_id="usr-1", numero=0)
    repo_proy = FakeProyectoRepository([proyecto])
    repo_fav = FakeProyectoFavoritoRepository()
    uow = FakeUnitOfWork()

    use_case = AgregarProyectoFavoritoUseCase(repo_proy, repo_fav, uow)
    use_case.execute(AgregarProyectoFavoritoCommand(propietario_id="usr-1", proyecto_id=proyecto.id))

    assert repo_fav.obtener_activo("usr-1", proyecto.id) is not None
    assert uow.committed is True


def test_agregar_favorito_idempotente():
    proyecto = Proyecto.crear(propietario_id="usr-1", numero=0)
    repo_proy = FakeProyectoRepository([proyecto])
    repo_fav = FakeProyectoFavoritoRepository()
    uow = FakeUnitOfWork()

    fav = ProyectoFavorito.crear(usuario_id="usr-1", proyecto_id=proyecto.id)
    repo_fav.guardar(fav)

    use_case = AgregarProyectoFavoritoUseCase(repo_proy, repo_fav, uow)
    use_case.execute(AgregarProyectoFavoritoCommand(propietario_id="usr-1", proyecto_id=proyecto.id))

    # Sigue existiendo sin duplicarse
    assert repo_fav.obtener_activo("usr-1", proyecto.id).id == fav.id
    assert uow.committed is True


def test_agregar_favorito_restaura_eliminado():
    proyecto = Proyecto.crear(propietario_id="usr-1", numero=0)
    repo_proy = FakeProyectoRepository([proyecto])
    repo_fav = FakeProyectoFavoritoRepository()
    uow = FakeUnitOfWork()

    fav = ProyectoFavorito.crear(usuario_id="usr-1", proyecto_id=proyecto.id)
    repo_fav.guardar(fav)
    repo_fav.eliminar("usr-1", proyecto.id)

    assert repo_fav.obtener_activo("usr-1", proyecto.id) is None
    assert repo_fav.obtener_eliminado("usr-1", proyecto.id) is not None

    use_case = AgregarProyectoFavoritoUseCase(repo_proy, repo_fav, uow)
    use_case.execute(AgregarProyectoFavoritoCommand(propietario_id="usr-1", proyecto_id=proyecto.id))

    assert repo_fav.obtener_activo("usr-1", proyecto.id) is not None
    assert repo_fav.obtener_eliminado("usr-1", proyecto.id) is None


def test_agregar_favorito_proyecto_ajeno_lanza_excepcion():
    proyecto = Proyecto.crear(propietario_id="usr-ajeno", numero=0)
    repo_proy = FakeProyectoRepository([proyecto])
    repo_fav = FakeProyectoFavoritoRepository()
    uow = FakeUnitOfWork()

    use_case = AgregarProyectoFavoritoUseCase(repo_proy, repo_fav, uow)
    with pytest.raises(ProyectoNoEncontradoException):
        use_case.execute(AgregarProyectoFavoritoCommand(propietario_id="usr-1", proyecto_id=proyecto.id))


def test_desmarcar_favorito_exitoso():
    proyecto = Proyecto.crear(propietario_id="usr-1", numero=0)
    repo_proy = FakeProyectoRepository([proyecto])
    repo_fav = FakeProyectoFavoritoRepository()
    uow = FakeUnitOfWork()

    fav = ProyectoFavorito.crear(usuario_id="usr-1", proyecto_id=proyecto.id)
    repo_fav.guardar(fav)

    use_case = DesmarcarProyectoFavoritoUseCase(repo_proy, repo_fav, uow)
    use_case.execute(DesmarcarProyectoFavoritoCommand(propietario_id="usr-1", proyecto_id=proyecto.id))

    assert repo_fav.obtener_activo("usr-1", proyecto.id) is None
    assert repo_fav.obtener_eliminado("usr-1", proyecto.id) is not None
    assert uow.committed is True
