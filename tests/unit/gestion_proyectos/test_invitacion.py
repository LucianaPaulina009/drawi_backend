from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
import pytest

from app.modules.diagramas.domain.entities.diagrama import Diagrama
from app.modules.diagramas.domain.repositories.diagrama_repository import DiagramaRepository
from app.modules.gestion_proyectos.application.queries.validar_invitacion import (
    ValidarInvitacionQuery,
    ValidarInvitacionQueryHandler,
)
from app.modules.gestion_proyectos.application.use_cases.obtener_o_crear_invitacion import (
    ObtenerOCrearInvitacionCommand,
    ObtenerOCrearInvitacionUseCase,
)
from app.modules.gestion_proyectos.application.use_cases.unirse_con_invitacion import (
    UnirseConInvitacionCommand,
    UnirseConInvitacionUseCase,
)
from app.modules.gestion_proyectos.domain.entities.colaborador_proyecto import ColaboradorProyecto
from app.modules.gestion_proyectos.domain.entities.invitacion import Invitacion
from app.modules.gestion_proyectos.domain.entities.proyecto import Proyecto
from app.modules.gestion_proyectos.domain.exceptions import (
    InvitacionExpiradaException,
    InvitacionNoEncontradaException,
    NoAutorizadoProyectoException,
    ProyectoNoEncontradoException,
    UsuarioBloqueadoException,
)
from app.modules.gestion_proyectos.domain.repositories.colaborador_proyecto_repository import (
    ColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.domain.repositories.invitacion_repository import (
    InvitacionRepository,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)
from app.modules.gestion_proyectos.domain.value_objects.estado_colaborador import EstadoColaborador
from app.modules.gestion_proyectos.domain.value_objects.rol_colaborador import RolColaborador
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


class FakeInvitacionRepository(InvitacionRepository):
    def __init__(self, invitaciones: list[Invitacion] = None):
        self.invitaciones = {i.id: i for i in (invitaciones or [])}

    def obtener_por_id(self, invitacion_id: UUID) -> Invitacion | None:
        return self.invitaciones.get(invitacion_id)

    def obtener_por_proyecto(self, id_proyecto: UUID) -> Invitacion | None:
        for inv in self.invitaciones.values():
            if inv.id_proyecto == id_proyecto:
                return inv
        return None

    def obtener_por_codigo(self, codigo_acceso: str) -> Invitacion | None:
        for inv in self.invitaciones.values():
            if inv.codigo_acceso == codigo_acceso:
                return inv
        return None

    def guardar(self, invitacion: Invitacion) -> None:
        self.invitaciones[invitacion.id] = invitacion

    def eliminar(self, invitacion_id: UUID) -> None:
        if invitacion_id in self.invitaciones:
            del self.invitaciones[invitacion_id]


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


class FakeDiagramaRepository(DiagramaRepository):
    def __init__(self, diagramas: list[Diagrama] = None):
        self.diagramas = {d.id: d for d in (diagramas or [])}

    def obtener_por_id(self, diagrama_id: UUID) -> Diagrama | None:
        return self.diagramas.get(diagrama_id)

    def listar_por_proyecto(self, proyecto_id: UUID) -> list[Diagrama]:
        return sorted(
            [d for d in self.diagramas.values() if d.id_proyecto == proyecto_id],
            key=lambda x: x.numero,
        )

    def obtener_numeros_activos_por_proyecto(self, proyecto_id: UUID) -> list[int]:
        return [d.numero for d in self.listar_por_proyecto(proyecto_id)]

    def contar_activos_por_proyecto(self, proyecto_id: UUID) -> int:
        return len(self.listar_por_proyecto(proyecto_id))

    def guardar(self, diagrama: Diagrama) -> None:
        self.diagramas[diagrama.id] = diagrama

    def eliminar(self, diagrama_id: UUID) -> None:
        if diagrama_id in self.diagramas:
            del self.diagramas[diagrama_id]


def test_invitacion_entidad_crear_y_expiracion():
    id_proy = uuid4()
    inv = Invitacion.crear(id_proyecto=id_proy, duracion_dias=7)
    assert inv.id_proyecto == id_proy
    assert len(inv.codigo_acceso) > 20
    assert not inv.ha_expirado()

    # Expirada
    inv.fecha_expiracion = datetime.now(timezone.utc) - timedelta(days=1)
    assert inv.ha_expirado()

    # Renovar
    viejo_codigo = inv.codigo_acceso
    inv.renovar(duracion_dias=7)
    assert inv.codigo_acceso != viejo_codigo
    assert not inv.ha_expirado()


def test_obtener_o_crear_invitacion_nueva():
    proy = Proyecto.crear(propietario_id="usr-1", numero=0)
    repo_proy = FakeProyectoRepository([proy])
    repo_inv = FakeInvitacionRepository([])
    uow = FakeUnitOfWork()

    use_case = ObtenerOCrearInvitacionUseCase(repo_proy, repo_inv, uow, duracion_dias=7)
    inv = use_case.execute(
        ObtenerOCrearInvitacionCommand(
            propietario_id="usr-1",
            proyecto_id=proy.id,
        )
    )

    assert inv is not None
    assert inv.id_proyecto == proy.id
    assert uow.committed is True
    assert repo_inv.obtener_por_proyecto(proy.id) is not None


def test_obtener_o_crear_invitacion_idempotente():
    proy = Proyecto.crear(propietario_id="usr-1", numero=0)
    inv_existente = Invitacion.crear(id_proyecto=proy.id, duracion_dias=7)
    repo_proy = FakeProyectoRepository([proy])
    repo_inv = FakeInvitacionRepository([inv_existente])
    uow = FakeUnitOfWork()

    use_case = ObtenerOCrearInvitacionUseCase(repo_proy, repo_inv, uow, duracion_dias=7)
    inv = use_case.execute(
        ObtenerOCrearInvitacionCommand(
            propietario_id="usr-1",
            proyecto_id=proy.id,
        )
    )

    assert inv.codigo_acceso == inv_existente.codigo_acceso


def test_obtener_o_crear_invitacion_renueva_si_expirada():
    proy = Proyecto.crear(propietario_id="usr-1", numero=0)
    inv_vencida = Invitacion(
        id=uuid4(),
        id_proyecto=proy.id,
        codigo_acceso="antiguo-codigo",
        fecha_expiracion=datetime.now(timezone.utc) - timedelta(days=1),
    )
    repo_proy = FakeProyectoRepository([proy])
    repo_inv = FakeInvitacionRepository([inv_vencida])
    uow = FakeUnitOfWork()

    use_case = ObtenerOCrearInvitacionUseCase(repo_proy, repo_inv, uow, duracion_dias=7)
    inv = use_case.execute(
        ObtenerOCrearInvitacionCommand(
            propietario_id="usr-1",
            proyecto_id=proy.id,
        )
    )

    assert inv.codigo_acceso != "antiguo-codigo"
    assert not inv.ha_expirado()
    assert uow.committed is True


def test_obtener_o_crear_invitacion_no_propietario_rechazado():
    proy = Proyecto.crear(propietario_id="usr-1", numero=0)
    repo_proy = FakeProyectoRepository([proy])
    repo_inv = FakeInvitacionRepository([])
    uow = FakeUnitOfWork()

    use_case = ObtenerOCrearInvitacionUseCase(repo_proy, repo_inv, uow)
    with pytest.raises(NoAutorizadoProyectoException):
        use_case.execute(
            ObtenerOCrearInvitacionCommand(
                propietario_id="usr-intruso",
                proyecto_id=proy.id,
            )
        )


def test_unirse_con_invitacion_exitoso():
    proy = Proyecto.crear(propietario_id="usr-1", numero=0)
    diag = Diagrama.crear(id_proyecto=proy.id, numero=1, nombre="Página 1")
    inv = Invitacion.crear(id_proyecto=proy.id, duracion_dias=7)

    repo_proy = FakeProyectoRepository([proy])
    repo_inv = FakeInvitacionRepository([inv])
    repo_colab = FakeColaboradorProyectoRepository([])
    repo_diag = FakeDiagramaRepository([diag])
    uow = FakeUnitOfWork()

    use_case = UnirseConInvitacionUseCase(
        invitacion_repository=repo_inv,
        proyecto_repository=repo_proy,
        colaborador_repository=repo_colab,
        diagrama_repository=repo_diag,
        uow=uow,
    )

    res = use_case.execute(
        UnirseConInvitacionCommand(
            codigo=inv.codigo_acceso,
            usuario_id="usr-colaborador-1",
        )
    )

    assert res.proyecto_id == proy.id
    assert res.proyecto_slug == proy.slug
    assert res.diagrama_id == diag.id
    assert res.rol == "ver"
    assert uow.committed is True

    # Verificar que se creó el colaborador
    colab = repo_colab.obtener_por_proyecto_y_usuario(proy.id, "usr-colaborador-1")
    assert colab is not None
    assert colab.rol == RolColaborador.VER
    assert colab.estado == EstadoColaborador.ACTIVO


def test_unirse_con_invitacion_usuario_bloqueado_rechazado():
    proy = Proyecto.crear(propietario_id="usr-1", numero=0)
    inv = Invitacion.crear(id_proyecto=proy.id, duracion_dias=7)
    colab_bloqueado = ColaboradorProyecto.crear(
        id_proyecto=proy.id,
        id_usuario="usr-bloqueado",
        rol=RolColaborador.VER,
        estado=EstadoColaborador.BLOQUEADO,
    )

    repo_proy = FakeProyectoRepository([proy])
    repo_inv = FakeInvitacionRepository([inv])
    repo_colab = FakeColaboradorProyectoRepository([colab_bloqueado])
    repo_diag = FakeDiagramaRepository([])
    uow = FakeUnitOfWork()

    use_case = UnirseConInvitacionUseCase(
        invitacion_repository=repo_inv,
        proyecto_repository=repo_proy,
        colaborador_repository=repo_colab,
        diagrama_repository=repo_diag,
        uow=uow,
    )

    with pytest.raises(UsuarioBloqueadoException):
        use_case.execute(
            UnirseConInvitacionCommand(
                codigo=inv.codigo_acceso,
                usuario_id="usr-bloqueado",
            )
        )


def test_unirse_con_invitacion_expirada_rechazado():
    proy = Proyecto.crear(propietario_id="usr-1", numero=0)
    inv_expirada = Invitacion(
        id=uuid4(),
        id_proyecto=proy.id,
        codigo_acceso="codigo-expirado",
        fecha_expiracion=datetime.now(timezone.utc) - timedelta(days=1),
    )

    repo_proy = FakeProyectoRepository([proy])
    repo_inv = FakeInvitacionRepository([inv_expirada])
    repo_colab = FakeColaboradorProyectoRepository([])
    repo_diag = FakeDiagramaRepository([])
    uow = FakeUnitOfWork()

    use_case = UnirseConInvitacionUseCase(
        invitacion_repository=repo_inv,
        proyecto_repository=repo_proy,
        colaborador_repository=repo_colab,
        diagrama_repository=repo_diag,
        uow=uow,
    )

    with pytest.raises(InvitacionExpiradaException):
        use_case.execute(
            UnirseConInvitacionCommand(
                codigo="codigo-expirado",
                usuario_id="usr-2",
            )
        )
