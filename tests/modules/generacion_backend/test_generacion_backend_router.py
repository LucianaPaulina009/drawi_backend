import io
import zipfile
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.security.auth import AuthUser
from app.modules.diagramas.infrastructure.persistence.models.atributo_model import AtributoModel
from app.modules.diagramas.infrastructure.persistence.models.clase_model import ClaseModel
from app.modules.diagramas.infrastructure.persistence.models.diagrama_model import DiagramaModel
from app.modules.gestion_proyectos.infrastructure.persistence.models.proyecto_model import ProyectoModel
from app.modules.generacion_backend.infrastructure.persistence.models.generacion_backend_model import (
    GeneracionBackendModel,
)
from app.modules.inteligencia_artificial.infrastructure.persistence.models.interaccion_ia_model import (
    InteraccionIaModel,
)
from app.shared.infrastructure.db.better_auth import BetterAuthUser


def test_generar_backend_router_exito(client: TestClient, session: Session):
    # Setup usuario y proyecto
    usuario = BetterAuthUser(
        id="usuario-propietario-1",
        name="Propietario",
        email="propietario@drawi.com",
        email_verified=True,
    )
    session.add(usuario)
    session.flush()

    proyecto = ProyectoModel(
        propietario_id=usuario.id,
        nombre="Proyecto Tienda Online",
        slug="proyecto-tienda-online",
    )
    session.add(proyecto)
    session.flush()

    diagrama = DiagramaModel(
        id_proyecto=proyecto.id,
        nombre="Diagrama Tienda",
        numero=1,
    )
    session.add(diagrama)
    session.flush()

    clase = ClaseModel(
        id_diagrama=diagrama.id,
        nombre="Producto",
        posicion_x=100.0,
        posicion_y=100.0,
        ancho=220.0,
    )
    session.add(clase)
    session.flush()

    attr_id = AtributoModel(
        id_clase=clase.id,
        nombre="id",
        tipo_dato="bigint",
        es_llave_primaria=True,
        permite_nulo=False,
        es_unico=True,
        orden_de_posicion=1,
        procedencia="manual",
    )
    attr_nombre = AtributoModel(
        id_clase=clase.id,
        nombre="nombre",
        tipo_dato="varchar",
        longitud=100,
        es_llave_primaria=False,
        permite_nulo=False,
        es_unico=False,
        orden_de_posicion=2,
        procedencia="manual",
    )
    attr_precio = AtributoModel(
        id_clase=clase.id,
        nombre="precio",
        tipo_dato="decimal",
        precision=10,
        escala=2,
        es_llave_primaria=False,
        permite_nulo=False,
        es_unico=False,
        orden_de_posicion=3,
        procedencia="manual",
    )
    session.add(attr_id)
    session.add(attr_nombre)
    session.add(attr_precio)
    session.commit()

    # Ejecutar POST al endpoint
    response = client.post(f"/api/diagramas/{diagrama.id}/generaciones-backend")
    assert response.status_code == 200, response.text
    assert response.headers["Content-Type"] == "application/zip"
    assert "drawi-backend-diagrama-tienda.zip" in response.headers.get("Content-Disposition", "")
    assert "X-Generacion-Backend-Id" in response.headers
    assert "X-Mensaje-Chat" in response.headers
    assert "X-Interaccion-Id" in response.headers

    # Verificar contenido del ZIP recibido
    zip_bytes = response.content
    assert len(zip_bytes) > 0
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z:
        archivos = z.namelist()
        assert "pom.xml" in archivos
        assert "Dockerfile" in archivos
        assert "docker-compose.yml" in archivos
        assert "README.md" in archivos
        assert "src/main/resources/application.yml" in archivos
        assert "src/main/java/com/drawi/app/Application.java" in archivos
        assert "src/main/java/com/drawi/app/entity/Producto.java" in archivos
        assert "src/main/java/com/drawi/app/controller/ProductoController.java" in archivos

    # Verificar que GENERACION_BACKEND quedó persistida como completado
    stmt = select(GeneracionBackendModel).where(GeneracionBackendModel.id_diagrama == diagrama.id)
    generaciones = session.exec(stmt).all()
    assert len(generaciones) == 1
    gen = generaciones[0]
    assert gen.estado == "completado"
    assert gen.detalle_error is None
    assert gen.version_plantilla == "1.0.0"
    assert gen.id_usuario == "usuario-propietario-1"

    # Verificar que la interacción de IA quedó persistida como completada con mensaje seguro sin ZIP ni blobs
    stmt_ia = select(InteraccionIaModel).where(InteraccionIaModel.id_diagrama == diagrama.id)
    interacciones = session.exec(stmt_ia).all()
    assert len(interacciones) == 1
    ia = interacciones[0]
    assert ia.tipo_interaccion == "generacion_backend"
    assert ia.entrada_usuario is None
    assert ia.respuesta_ia == "Backend generado correctamente."
    assert ia.estado == "completado"
    assert ia.url_imagen is None

    # Verificar que el endpoint GET /api/diagramas/{id}/interacciones-ia expone la interacción
    res_get = client.get(f"/api/diagramas/{diagrama.id}/interacciones-ia")
    assert res_get.status_code == 200
    data_get = res_get.json()
    assert len(data_get["items"]) == 1
    item = data_get["items"][0]
    assert item["tipoInteraccion"] == "generacion_backend"
    assert item["entradaUsuario"] is None
    assert item["respuestaIa"] == "Backend generado correctamente."
    assert item["estado"] == "completado"


def test_generar_backend_router_error_validacion_persiste_error(client: TestClient, session: Session):
    usuario = BetterAuthUser(
        id="usuario-propietario-1",
        name="Propietario",
        email="propietario@drawi.com",
        email_verified=True,
    )
    session.add(usuario)
    session.flush()

    proyecto = ProyectoModel(
        propietario_id=usuario.id,
        nombre="Proyecto Invalido",
        slug="proyecto-invalido",
    )
    session.add(proyecto)
    session.flush()

    # Diagrama sin clases (vacío)
    diagrama = DiagramaModel(
        id_proyecto=proyecto.id,
        nombre="Diagrama Vacio",
        numero=1,
    )
    session.add(diagrama)
    session.commit()

    response = client.post(f"/api/diagramas/{diagrama.id}/generaciones-backend")
    assert response.status_code == 422, response.text
    assert "X-Mensaje-Chat" in response.headers
    assert "X-Interaccion-Id" in response.headers
    data = response.json()
    assert data["code"] == "DIAGRAMA_NO_GENERABLE"
    assert data["message"] == "El diagrama contiene errores que deben corregirse"
    assert data["mensaje_chat"] is not None
    assert "No se pudo generar el backend" in data["mensaje_chat"]
    assert data["interaccion_id"] is not None
    assert len(data["errores"]) > 0
    assert any(e["codigo"] == "DIAGRAMA_VACIO" for e in data["errores"])
    assert any(e.get("elemento") == "Diagrama Vacio" for e in data["errores"])

    # Verificar que GENERACION_BACKEND se persistió en estado 'error'
    stmt = select(GeneracionBackendModel).where(GeneracionBackendModel.id_diagrama == diagrama.id)
    generaciones = session.exec(stmt).all()
    assert len(generaciones) == 1
    gen = generaciones[0]
    assert gen.estado == "error"
    assert gen.detalle_error is not None
    assert "Errores estructurales" in gen.detalle_error

    # Verificar que se persistió la interacción IA con la lista de errores
    stmt_ia = select(InteraccionIaModel).where(InteraccionIaModel.id_diagrama == diagrama.id)
    interacciones = session.exec(stmt_ia).all()
    assert len(interacciones) == 1
    ia = interacciones[0]
    assert ia.tipo_interaccion == "generacion_backend"
    assert ia.entrada_usuario is None
    assert "No se pudo generar el backend porque el diagrama contiene los siguientes errores" in ia.respuesta_ia
    assert "• El diagrama no contiene clases" in ia.respuesta_ia
    assert ia.estado == "error"


def test_generar_backend_router_multiples_errores_validacion_devuelve_lista_completa(
    client: TestClient, session: Session
):
    usuario = BetterAuthUser(
        id="usuario-propietario-1",
        name="Propietario",
        email="propietario@drawi.com",
        email_verified=True,
    )
    session.add(usuario)
    session.flush()

    proyecto = ProyectoModel(
        propietario_id=usuario.id,
        nombre="Proyecto Multiples Errores",
        slug="proyecto-multiples-errores",
    )
    session.add(proyecto)
    session.flush()

    diagrama = DiagramaModel(
        id_proyecto=proyecto.id,
        nombre="Diagrama Multiples Errores",
        numero=1,
    )
    session.add(diagrama)
    session.flush()

    # Clase 1: Venta sin PK (es_llave_primaria=False) y con PK nullable
    clase_venta = ClaseModel(
        id_diagrama=diagrama.id,
        nombre="Venta",
        posicion_x=0.0,
        posicion_y=0.0,
        ancho=200.0,
    )
    session.add(clase_venta)
    session.flush()

    attr_total = AtributoModel(
        id_clase=clase_venta.id,
        nombre="total",
        tipo_dato="decimal",
        precision=10,
        escala=2,
        es_llave_primaria=False,
        permite_nulo=False,
        orden_de_posicion=1,
        procedencia="manual",
    )
    session.add(attr_total)

    # Clase 2: Cliente con atributos duplicados
    clase_cliente = ClaseModel(
        id_diagrama=diagrama.id,
        nombre="Cliente",
        posicion_x=250.0,
        posicion_y=0.0,
        ancho=200.0,
    )
    session.add(clase_cliente)
    session.flush()

    attr_id_cliente = AtributoModel(
        id_clase=clase_cliente.id,
        nombre="id",
        tipo_dato="bigint",
        es_llave_primaria=True,
        permite_nulo=False,
        orden_de_posicion=1,
        procedencia="manual",
    )
    attr_nombre1 = AtributoModel(
        id_clase=clase_cliente.id,
        nombre="nombre",
        tipo_dato="varchar",
        longitud=50,
        es_llave_primaria=False,
        permite_nulo=False,
        orden_de_posicion=2,
        procedencia="manual",
    )
    attr_nombre2 = AtributoModel(
        id_clase=clase_cliente.id,
        nombre="nombre",
        tipo_dato="varchar",
        longitud=50,
        es_llave_primaria=False,
        permite_nulo=False,
        orden_de_posicion=3,
        procedencia="manual",
    )
    session.add(attr_id_cliente)
    session.add(attr_nombre1)
    session.add(attr_nombre2)
    session.commit()

    response = client.post(f"/api/diagramas/{diagrama.id}/generaciones-backend")
    assert response.status_code == 422, response.text
    data = response.json()
    assert data["code"] == "DIAGRAMA_NO_GENERABLE"
    assert data["message"] == "El diagrama contiene errores que deben corregirse"

    # Verificar que se devuelven TODOS los errores (sin detenerse en el primero)
    codigos_error = [e["codigo"] for e in data["errores"]]
    assert "CLASE_SIN_PK" in codigos_error
    assert "ATRIBUTO_NOMBRE_DUPLICADO" in codigos_error

    # Verificar que el elemento afectado aparece en los errores
    elementos = [e.get("elemento") for e in data["errores"]]
    assert "Venta" in elementos
    assert "Cliente.nombre" in elementos

    # Verificar que se guardó una única interacción de tipo generacion_backend con todos los errores
    stmt_ia = select(InteraccionIaModel).where(InteraccionIaModel.id_diagrama == diagrama.id)
    interacciones = session.exec(stmt_ia).all()
    assert len(interacciones) == 1
    ia = interacciones[0]
    assert ia.tipo_interaccion == "generacion_backend"
    assert ia.entrada_usuario is None
    assert ia.estado == "error"
    assert "• La clase 'Venta' no tiene una clave primaria (PK) definida." in ia.respuesta_ia
    assert "• El atributo normalizado 'nombre' está duplicado en la clase 'Cliente'." in ia.respuesta_ia

    # Verificar que el endpoint GET /api/diagramas/{id}/interacciones-ia devuelve la interacción completa tras 422
    res_get = client.get(f"/api/diagramas/{diagrama.id}/interacciones-ia")
    assert res_get.status_code == 200
    data_get = res_get.json()
    assert len(data_get["items"]) == 1
    item = data_get["items"][0]
    assert item["tipoInteraccion"] == "generacion_backend"
    assert item["entradaUsuario"] is None
    assert item["estado"] == "error"
    assert "• La clase 'Venta' no tiene una clave primaria (PK) definida." in item["respuestaIa"]
    assert "• El atributo normalizado 'nombre' está duplicado en la clase 'Cliente'." in item["respuestaIa"]


def test_generar_backend_router_no_autorizado(client: TestClient, session: Session):
    usuario_otro = BetterAuthUser(
        id="otro-usuario",
        name="Otro",
        email="otro@drawi.com",
        email_verified=True,
    )
    session.add(usuario_otro)
    session.flush()

    proyecto_otro = ProyectoModel(
        propietario_id="otro-usuario",
        nombre="Proyecto Privado",
        slug="proyecto-privado",
    )
    session.add(proyecto_otro)
    session.flush()

    diagrama_otro = DiagramaModel(
        id_proyecto=proyecto_otro.id,
        nombre="Diagrama Privado",
        numero=1,
    )
    session.add(diagrama_otro)
    session.commit()

    # El usuario autenticado es "usuario-propietario-1", no tiene acceso a este proyecto
    response = client.post(f"/api/diagramas/{diagrama_otro.id}/generaciones-backend")
    assert response.status_code in [403, 404]
