from uuid import UUID
import pytest
from sqlmodel import Session, select

from app.core.security.auth import AuthUser, get_current_user
from app.main import app
from app.modules.diagramas.infrastructure.persistence.models.diagrama_model import DiagramaModel
from app.modules.gestion_proyectos.infrastructure.persistence.models.colaborador_proyecto_model import (
    ColaboradorProyectoModel,
)
from app.modules.gestion_proyectos.infrastructure.persistence.models.invitacion_model import (
    InvitacionModel,
)
from app.modules.gestion_proyectos.infrastructure.persistence.models.proyecto_model import (
    ProyectoModel,
)
from app.shared.infrastructure.db.better_auth import BetterAuthUser


@pytest.fixture
def setup_proyectos_y_usuarios(session: Session, usuario_autenticado: AuthUser, usuario_secundario: AuthUser):
    # Crear usuarios Better Auth en base de datos de test
    user1 = BetterAuthUser(
        id=usuario_autenticado.user_id,
        name="Propietario Demo",
        email=usuario_autenticado.email,
        emailVerified=True,
    )
    user2 = BetterAuthUser(
        id=usuario_secundario.user_id,
        name="Colaborador Demo",
        email=usuario_secundario.email,
        emailVerified=True,
    )
    session.add(user1)
    session.add(user2)

    # Crear proyecto del usuario 1 con diagrama
    proyecto = ProyectoModel(
        propietario_id=usuario_autenticado.user_id,
        nombre="Proyecto Colaborativo",
        slug="proyecto-colaborativo",
        color="azul",
        icono="caja",
    )
    session.add(proyecto)
    session.commit()
    session.refresh(proyecto)

    diagrama = DiagramaModel(
        id_proyecto=proyecto.id,
        numero=1,
        nombre="Página 1",
    )
    session.add(diagrama)
    session.commit()
    session.refresh(diagrama)

    return {"proyecto": proyecto, "diagrama": diagrama, "owner": user1, "colab": user2}


def test_flujo_completo_invitaciones_y_colaboradores(
    client, session: Session, usuario_autenticado: AuthUser, usuario_secundario: AuthUser, setup_proyectos_y_usuarios
):
    proyecto = setup_proyectos_y_usuarios["proyecto"]
    diagrama = setup_proyectos_y_usuarios["diagrama"]

    # 1. Propietario genera invitación
    res_inv = client.post(f"/api/proyectos/{proyecto.id}/invitacion")
    assert res_inv.status_code == 200
    inv_data = res_inv.json()
    codigo = inv_data["codigo_acceso"]
    assert len(codigo) > 10

    # 2. Idempotencia: obtener invitación nuevamente
    res_inv_repeat = client.post(f"/api/proyectos/{proyecto.id}/invitacion")
    assert res_inv_repeat.status_code == 200
    assert res_inv_repeat.json()["codigo_acceso"] == codigo

    # 3. No propietario no puede generar invitación
    app.dependency_overrides[get_current_user] = lambda: usuario_secundario
    res_inv_forbidden = client.post(f"/api/proyectos/{proyecto.id}/invitacion")
    assert res_inv_forbidden.status_code == 403

    # 4. Validar código de invitación (GET)
    res_val = client.get(f"/api/invitaciones/{codigo}")
    assert res_val.status_code == 200
    assert res_val.json()["proyecto_nombre"] == "Proyecto Colaborativo"
    assert res_val.json()["propietario_nombre"] == "Propietario Demo"

    # 5. Usuario secundario se une al proyecto
    res_join = client.post(f"/api/invitaciones/{codigo}/unirse")
    assert res_join.status_code == 200
    join_data = res_join.json()
    assert join_data["proyecto_slug"] == "proyecto-colaborativo"
    assert join_data["diagrama_id"] == str(diagrama.id)
    assert join_data["rol"] == "ver"

    # 6. Propietario consulta listado de miembros
    app.dependency_overrides[get_current_user] = lambda: usuario_autenticado
    res_miembros = client.get(f"/api/proyectos/{proyecto.id}/miembros")
    assert res_miembros.status_code == 200
    miembros = res_miembros.json()["items"]
    assert len(miembros) == 2
    owner_entry = next(m for m in miembros if m["es_propietario"])
    colab_entry = next(m for m in miembros if not m["es_propietario"])
    assert owner_entry["nombre"] == "Propietario Demo"
    assert colab_entry["nombre"] == "Colaborador Demo"
    assert colab_entry["rol"] == "ver"

    colaborador_id = colab_entry["id"]

    # 7. Cambiar rol a 'editor'
    res_rol = client.patch(
        f"/api/proyectos/{proyecto.id}/miembros/{colaborador_id}/rol",
        json={"rol": "editor"},
    )
    assert res_rol.status_code == 204

    # Verificar que el rol cambió a editor
    res_miembros2 = client.get(f"/api/proyectos/{proyecto.id}/miembros")
    colab_updated = next(m for m in res_miembros2.json()["items"] if not m["es_propietario"])
    assert colab_updated["rol"] == "editor"

    # 8. Bloquear colaborador
    res_bloq = client.post(f"/api/proyectos/{proyecto.id}/miembros/{colaborador_id}/bloquear")
    assert res_bloq.status_code == 204

    # Verificar que colaborador bloqueado no puede acceder/unirse
    app.dependency_overrides[get_current_user] = lambda: usuario_secundario
    res_join_blocked = client.post(f"/api/invitaciones/{codigo}/unirse")
    assert res_join_blocked.status_code == 403

    # 9. Desbloquear colaborador
    app.dependency_overrides[get_current_user] = lambda: usuario_autenticado
    res_desbloq = client.post(f"/api/proyectos/{proyecto.id}/miembros/{colaborador_id}/desbloquear")
    assert res_desbloq.status_code == 204

    # Verificar que el rol se mantuvo como 'editor'
    res_miembros3 = client.get(f"/api/proyectos/{proyecto.id}/miembros")
    colab_desbloq = next(m for m in res_miembros3.json()["items"] if not m["es_propietario"])
    assert colab_desbloq["estado"] == "activo"
    assert colab_desbloq["rol"] == "editor"

    # 10. Remover colaborador
    res_rem = client.delete(f"/api/proyectos/{proyecto.id}/miembros/{colaborador_id}")
    assert res_rem.status_code == 204

    # Verificar que ya no aparece en el listado de miembros activos
    res_miembros4 = client.get(f"/api/proyectos/{proyecto.id}/miembros")
    assert len(res_miembros4.json()["items"]) == 1

    # 11. Colaborador removido puede volverse a unir con el enlace (recupera rol inicial 'ver')
    app.dependency_overrides[get_current_user] = lambda: usuario_secundario
    res_rejoin = client.post(f"/api/invitaciones/{codigo}/unirse")
    assert res_rejoin.status_code == 200
    assert res_rejoin.json()["rol"] == "ver"

    # 12. Blindaje del Propietario: intentar cambiar rol o remover al propietario es rechazado
    app.dependency_overrides[get_current_user] = lambda: usuario_autenticado
    res_owner_rol = client.patch(
        f"/api/proyectos/{proyecto.id}/miembros/{proyecto.id}/rol",
        json={"rol": "editor"},
    )
    assert res_owner_rol.status_code == 422 or res_owner_rol.status_code == 400

    res_owner_del = client.delete(f"/api/proyectos/{proyecto.id}/miembros/{proyecto.id}")
    assert res_owner_del.status_code == 422 or res_owner_del.status_code == 400


def test_acceso_colaborador_proyecto_y_diagramas(
    client, session: Session, usuario_autenticado: AuthUser, usuario_secundario: AuthUser, setup_proyectos_y_usuarios
):
    proyecto = setup_proyectos_y_usuarios["proyecto"]
    diagrama = setup_proyectos_y_usuarios["diagrama"]

    # Generar invitación y unirse como colaborador (rol 'ver')
    res_inv = client.post(f"/api/proyectos/{proyecto.id}/invitacion")
    codigo = res_inv.json()["codigo_acceso"]

    app.dependency_overrides[get_current_user] = lambda: usuario_secundario
    res_join = client.post(f"/api/invitaciones/{codigo}/unirse")
    assert res_join.status_code == 200

    # 1. Colaborador con rol 'ver' lista proyectos: debe ver el proyecto colaborativo
    res_listado = client.get("/api/proyectos/listado")
    assert res_listado.status_code == 200
    items = res_listado.json()["items"]
    p_colab = next((p for p in items if p["id"] == str(proyecto.id)), None)
    assert p_colab is not None
    assert p_colab["slug"] == proyecto.slug
    assert p_colab["propietario_id"] == usuario_autenticado.user_id

    # 2. Colaborador con rol 'ver' lista diagramas del proyecto
    res_diag_list = client.get(f"/api/proyectos/{proyecto.id}/diagramas")
    assert res_diag_list.status_code == 200
    diags = res_diag_list.json()["items"]
    assert len(diags) == 1
    assert diags[0]["id"] == str(diagrama.id)

    # 3. Colaborador con rol 'ver' obtiene detalle del diagrama
    res_diag_det = client.get(f"/api/proyectos/{proyecto.id}/diagramas/{diagrama.id}")
    assert res_diag_det.status_code == 200
    assert res_diag_det.json()["id"] == str(diagrama.id)

    # 4. Colaborador con rol 'ver' lista clases del diagrama
    res_clases = client.get(f"/api/diagramas/{diagrama.id}/clases")
    assert res_clases.status_code == 200

    # 5. Colaborador bloqueado
    app.dependency_overrides[get_current_user] = lambda: usuario_autenticado
    res_miembros = client.get(f"/api/proyectos/{proyecto.id}/miembros")
    colab_id = next(m["id"] for m in res_miembros.json()["items"] if not m["es_propietario"])
    client.post(f"/api/proyectos/{proyecto.id}/miembros/{colab_id}/bloquear")

    # Colaborador bloqueado recibe 403 al consultar diagramas
    app.dependency_overrides[get_current_user] = lambda: usuario_secundario
    res_blocked_diags = client.get(f"/api/proyectos/{proyecto.id}/diagramas")
    assert res_blocked_diags.status_code == 403

    res_blocked_diag = client.get(f"/api/proyectos/{proyecto.id}/diagramas/{diagrama.id}")
    assert res_blocked_diag.status_code == 403

    # Colaborador bloqueado no ve el proyecto en su listado
    res_blocked_list = client.get("/api/proyectos/listado")
    assert res_blocked_list.status_code == 200
    assert not any(p["id"] == str(proyecto.id) for p in res_blocked_list.json()["items"])

    # 6. Usuario desconocido (sin relación) recibe 404
    usuario_desconocido = AuthUser(
        user_id="user-unknown-999",
        email="unknown@example.com",
    )
    app.dependency_overrides[get_current_user] = lambda: usuario_desconocido
    res_unknown_diags = client.get(f"/api/proyectos/{proyecto.id}/diagramas")
    assert res_unknown_diags.status_code == 404

    res_unknown_diag = client.get(f"/api/proyectos/{proyecto.id}/diagramas/{diagrama.id}")
    assert res_unknown_diag.status_code == 404
