from uuid import uuid4
import pytest
from sqlmodel import Session

from app.modules.diagramas.infrastructure.persistence.models.diagrama_model import DiagramaModel
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_diagrama_repository import (
    SQLModelDiagramaRepository,
)
from app.modules.gestion_colaboradores.infrastructure.persistence.models.colaborador_proyecto_model import (
    ColaboradorProyectoModel,
)
from app.modules.gestion_colaboradores.infrastructure.persistence.repositories.sqlmodel_colaborador_proyecto_repository import (
    SQLModelColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.domain.exceptions import ProyectoNoEncontradoException
from app.modules.gestion_proyectos.infrastructure.persistence.models.proyecto_model import ProyectoModel
from app.modules.gestion_proyectos.infrastructure.persistence.repositories.sqlmodel_proyecto_repository import (
    SQLModelProyectoRepository,
)
from app.modules.inteligencia_artificial.application.queries.listar_interacciones_ia import (
    ListarInteraccionesIaQuery,
    ListarInteraccionesIaQueryHandler,
)
from app.modules.inteligencia_artificial.domain.entities.interaccion_ia import InteraccionIa
from app.modules.inteligencia_artificial.infrastructure.persistence.repositories.sqlmodel_interaccion_ia_repository import (
    SQLModelInteraccionIaRepository,
)
from app.shared.infrastructure.db.better_auth import BetterAuthUser


def test_listar_interacciones_ia_multi_usuario_mismo_diagrama(session: Session):
    u1 = BetterAuthUser(id="user-luciana", name="Luciana", email="luciana@drawi.com", email_verified=True)
    u2 = BetterAuthUser(id="user-pedro", name="Pedro", email="pedro@drawi.com", email_verified=True)
    u_ajeno = BetterAuthUser(id="user-ajeno", name="Ajeno", email="ajeno@drawi.com", email_verified=True)
    session.add_all([u1, u2, u_ajeno])
    session.commit()

    proyecto = ProyectoModel(propietario_id=u1.id, nombre="Proy Compartido", color="azul", icono="caja", slug="proy-comp")
    session.add(proyecto)
    session.commit()

    colab = ColaboradorProyectoModel(id_proyecto=proyecto.id, id_usuario=u2.id, rol="editor", estado="activo")
    session.add(colab)
    session.commit()

    diagrama_a = DiagramaModel(id_proyecto=proyecto.id, nombre="Página A", numero=1)
    diagrama_b = DiagramaModel(id_proyecto=proyecto.id, nombre="Página B", numero=2)
    session.add_all([diagrama_a, diagrama_b])
    session.commit()

    p_repo = SQLModelProyectoRepository(session)
    d_repo = SQLModelDiagramaRepository(session)
    i_repo = SQLModelInteraccionIaRepository(session)
    col_repo = SQLModelColaboradorProyectoRepository(session)

    # Luciana escribe en Página A
    i1 = InteraccionIa.crear(id_usuario=u1.id, id_diagrama=diagrama_a.id, clave_idempotencia=uuid4(), entrada_usuario="Mensaje 1 Luciana")
    i_repo.guardar(i1)
    # Pedro escribe en Página A
    i2 = InteraccionIa.crear(id_usuario=u2.id, id_diagrama=diagrama_a.id, clave_idempotencia=uuid4(), entrada_usuario="Mensaje 2 Pedro")
    i_repo.guardar(i2)
    # Luciana escribe en Página B
    i3 = InteraccionIa.crear(id_usuario=u1.id, id_diagrama=diagrama_b.id, clave_idempotencia=uuid4(), entrada_usuario="Mensaje Página B")
    i_repo.guardar(i3)
    session.commit()

    handler = ListarInteraccionesIaQueryHandler(p_repo, d_repo, i_repo, col_repo)

    # Pedro autorizado consulta Página A y ve ambos mensajes
    res_a = handler.execute(ListarInteraccionesIaQuery(usuario_id=u2.id, diagrama_id=diagrama_a.id))
    assert len(res_a) == 2
    assert res_a[0].id_usuario == u1.id
    assert res_a[1].id_usuario == u2.id

    # Consultar Página B solo devuelve el de Página B
    res_b = handler.execute(ListarInteraccionesIaQuery(usuario_id=u1.id, diagrama_id=diagrama_b.id))
    assert len(res_b) == 1
    assert res_b[0].id_diagrama == diagrama_b.id

    # Usuario ajeno sin permisos en el proyecto no puede listar
    with pytest.raises(ProyectoNoEncontradoException):
        handler.execute(ListarInteraccionesIaQuery(usuario_id=u_ajeno.id, diagrama_id=diagrama_a.id))
