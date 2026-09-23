from uuid import uuid4
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.modules.diagramas.infrastructure.persistence.models.diagrama_model import DiagramaModel
from app.modules.gestion_proyectos.infrastructure.persistence.models.proyecto_model import ProyectoModel
from app.modules.inteligencia_artificial.application.ports.providers.proveedor_ia import (
    ProveedorIa,
    ResultadoProveedorIa,
)
from app.modules.inteligencia_artificial.infrastructure.api.routers.interaccion_ia_router import (
    set_proveedor_ia_override,
)
from app.shared.infrastructure.db.better_auth import BetterAuthUser


class FakeRouterProveedor(ProveedorIa):
    def generar_respuesta(
        self,
        *,
        modelo: str,
        prompt_sistema: str,
        mensaje_usuario: str,
        temperatura: float = 0.2,
    ) -> ResultadoProveedorIa:
        return ResultadoProveedorIa(
            texto_respuesta='{"respuesta_usuario": "Hola desde la API de DRAWI", "acciones": []}',
            modelo=modelo,
        )


def test_interacciones_ia_api_post_y_get(client: TestClient, session: Session):
    usuario = BetterAuthUser(id="usuario-propietario-1", name="Prop", email="propietario@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy API IA", color="azul", icono="caja", slug="proy-api-ia")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Pagina 1", numero=1)
    session.add(diagrama)
    session.commit()

    set_proveedor_ia_override(FakeRouterProveedor())

    clave = str(uuid4())
    # 1. POST para enviar mensaje
    res_post = client.post(
        f"/api/diagramas/{diagrama.id}/interacciones-ia",
        json={"texto": "¿Cómo normalizar esta tabla?", "claveIdempotencia": clave},
    )
    assert res_post.status_code == 201, res_post.text
    data_post = res_post.json()
    assert data_post["entradaUsuario"] == "¿Cómo normalizar esta tabla?"
    assert data_post["respuestaIa"] == "Hola desde la API de DRAWI"
    assert data_post["estado"] == "completado"
    assert data_post["creadoEn"] is not None
    t1_creado_en = data_post["creadoEn"]

    # 2. GET para listar historial en T2
    res_get = client.get(f"/api/diagramas/{diagrama.id}/interacciones-ia")
    assert res_get.status_code == 200, res_get.text
    data_get = res_get.json()
    assert len(data_get["items"]) >= 1
    assert data_get["items"][0]["id"] == data_post["id"]
    # Verificar que creadoEn persiste exactamente la fecha original de T1
    assert data_get["items"][0]["creadoEn"] == t1_creado_en

    set_proveedor_ia_override(None)


def test_creado_en_persiste_timestamp_original(client: TestClient, session: Session):
    usuario = BetterAuthUser(id="usuario-propietario-1", name="PropT1", email="t1@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy T1", color="azul", icono="caja", slug="proy-t1")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Pagina 1", numero=1)
    session.add(diagrama)
    session.commit()

    set_proveedor_ia_override(FakeRouterProveedor())

    # Crear interacción en T1
    res_crear = client.post(
        f"/api/diagramas/{diagrama.id}/interacciones-ia",
        json={"texto": "Consulta en T1", "claveIdempotencia": str(uuid4())},
    )
    assert res_crear.status_code == 201
    timestamp_t1 = res_crear.json()["creadoEn"]
    assert timestamp_t1 is not None

    # Consultar posteriormente en T2
    res_consultar = client.get(f"/api/diagramas/{diagrama.id}/interacciones-ia")
    assert res_consultar.status_code == 200
    items = res_consultar.json()["items"]
    assert len(items) == 1
    assert items[0]["creadoEn"] == timestamp_t1

    set_proveedor_ia_override(None)


def test_interaccion_ia_api_crud_action(client: TestClient, session: Session):
    usuario = BetterAuthUser(id="usuario-propietario-1", name="PropCRUD", email="crud@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy CRUD", color="azul", icono="caja", slug="proy-crud")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Pagina 1", numero=1)
    session.add(diagrama)
    session.commit()

    from app.modules.diagramas.infrastructure.persistence.models.clase_model import ClaseModel
    clase = ClaseModel(id_diagrama=diagrama.id, nombre="Cliente", posicion_x=100.0, posicion_y=100.0, ancho=280.0)
    session.add(clase)
    session.commit()

    class FakeCrudProveedor(ProveedorIa):
        def generar_respuesta(self, *, modelo: str, prompt_sistema: str, mensaje_usuario: str, temperatura: float = 0.2) -> ResultadoProveedorIa:
            return ResultadoProveedorIa(
                texto_respuesta='{"respuesta_usuario": "Renombré Cliente a ClienteAct.", "acciones": [{"tipo": "actualizar_clase", "clase_referencia": "Cliente", "nuevo_nombre": "ClienteAct"}]}',
                modelo=modelo,
            )

    set_proveedor_ia_override(FakeCrudProveedor())

    res_post = client.post(
        f"/api/diagramas/{diagrama.id}/interacciones-ia",
        json={"texto": "Renombra la clase Cliente a ClienteAct", "claveIdempotencia": str(uuid4())},
    )
    assert res_post.status_code == 201, res_post.text
    data = res_post.json()
    assert data["estado"] == "completado"
    assert data["respuestaIa"] == "Renombré Cliente a ClienteAct."

    # Verificar que en base de datos la clase cambió de nombre
    session.refresh(clase)
    assert clase.nombre == "ClienteAct"

    set_proveedor_ia_override(None)


def test_interaccion_ia_api_crear_estructura_nm_con_atributo(client: TestClient, session: Session):
    from app.modules.diagramas.infrastructure.persistence.models.clase_model import ClaseModel
    from app.modules.diagramas.infrastructure.persistence.models.atributo_model import AtributoModel
    from app.modules.diagramas.domain.value_objects.procedencia_atributo import ProcedenciaAtributo
    from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_clase_repository import SQLModelClaseRepository
    from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_atributo_repository import SQLModelAtributoRepository
    from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_estructura_relacion_nm_repository import SQLModelEstructuraRelacionNmRepository

    usuario = BetterAuthUser(id="usuario-propietario-1", name="PropNM", email="nm@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy API NM", color="azul", icono="caja", slug="proy-api-nm")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Diagrama API NM", numero=1)
    session.add(diagrama)
    session.commit()

    c1 = ClaseModel(id_diagrama=diagrama.id, nombre="Cliente", posicion_x=100.0, posicion_y=100.0, ancho=280.0)
    c2 = ClaseModel(id_diagrama=diagrama.id, nombre="Vehiculo", posicion_x=500.0, posicion_y=100.0, ancho=280.0)
    session.add(c1)
    session.add(c2)
    session.commit()

    a1 = AtributoModel(id_clase=c1.id, nombre="id", tipo_dato="integer", orden_de_posicion=1, es_llave_primaria=True, permite_nulo=False, es_unico=True, procedencia=ProcedenciaAtributo.SISTEMA_CLASE.value)
    a2 = AtributoModel(id_clase=c2.id, nombre="id", tipo_dato="integer", orden_de_posicion=1, es_llave_primaria=True, permite_nulo=False, es_unico=True, procedencia=ProcedenciaAtributo.SISTEMA_CLASE.value)
    session.add(a1)
    session.add(a2)
    session.commit()

    class FakeNmProveedor(ProveedorIa):
        def generar_respuesta(self, *, modelo: str, prompt_sistema: str, mensaje_usuario: str, temperatura: float = 0.2) -> ResultadoProveedorIa:
            return ResultadoProveedorIa(
                texto_respuesta='''{
                  "respuesta_usuario": "Relación N:M creada exitosamente con el atributo prueba en Cliente_Vehiculo.",
                  "acciones": [
                    {
                      "tipo": "crear_estructura_nm",
                      "referencia_intermedia": "cliente_vehiculo",
                      "clase_origen_referencia": "Cliente",
                      "clase_destino_referencia": "Vehiculo",
                      "nombre_intermedia": "Cliente_Vehiculo"
                    },
                    {
                      "tipo": "crear_atributo",
                      "clase_referencia": "cliente_vehiculo",
                      "nombre": "prueba",
                      "tipo_dato": "text"
                    }
                  ]
                }''',
                modelo=modelo,
            )

    set_proveedor_ia_override(FakeNmProveedor())

    res_post = client.post(
        f"/api/diagramas/{diagrama.id}/interacciones-ia",
        json={
            "texto": "Crea una relacion de la tabla Cliente con Vehiculo, una relacion de muchos a muchos, en la tabla de muchos a muchos crea un atributo llamado prueba de tipo texto.",
            "claveIdempotencia": str(uuid4()),
        },
    )
    assert res_post.status_code == 201, res_post.text
    data = res_post.json()
    assert data["estado"] == "completado"
    assert "Cliente_Vehiculo" in data["respuestaIa"]

    c_repo = SQLModelClaseRepository(session)
    a_repo = SQLModelAtributoRepository(session)
    nm_repo = SQLModelEstructuraRelacionNmRepository(session)

    clases = c_repo.listar_por_diagrama(diagrama.id)
    assert len(clases) == 3
    intermedia = next(c for c in clases if c.nombre == "Cliente_Vehiculo")
    attrs = a_repo.listar_por_clase(intermedia.id)
    nombres_attrs = {a.nombre for a in attrs}
    assert "id" in nombres_attrs
    assert "prueba" in nombres_attrs
    assert len(nm_repo.listar_por_diagrama(diagrama.id)) == 1

    set_proveedor_ia_override(None)


def test_interaccion_ia_api_audio_unificado(client: TestClient, session: Session):
    from app.modules.inteligencia_artificial.application.ports.providers.proveedor_transcripcion import (
        ProveedorTranscripcion,
        ResultadoTranscripcion,
    )
    from app.modules.inteligencia_artificial.infrastructure.api.routers.interaccion_ia_router import (
        set_proveedor_transcripcion_override,
    )
    from app.modules.diagramas.infrastructure.persistence.models.clase_model import ClaseModel

    usuario = BetterAuthUser(id="usuario-propietario-1", name="PropAudio", email="audio@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy Audio", color="azul", icono="caja", slug="proy-audio")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Pagina 1", numero=1)
    session.add(diagrama)
    session.commit()

    class FakeAudioIaProveedor(ProveedorIa):
        def generar_respuesta(self, *, modelo: str, prompt_sistema: str, mensaje_usuario: str, temperatura: float = 0.2) -> ResultadoProveedorIa:
            return ResultadoProveedorIa(texto_respuesta="", modelo=modelo)

        def generar_respuesta_audio(
            self,
            *,
            modelo: str,
            prompt_sistema: str,
            contenido_audio: bytes,
            mime_type: str,
            temperatura: float = 0.2,
        ) -> ResultadoProveedorIa:
            return ResultadoProveedorIa(
                texto_respuesta='''{
                  "transcripcion_usuario": "Crea una clase Factura con total y fecha",
                  "respuesta_usuario": "Clase Factura creada exitosamente.",
                  "acciones": [
                    {
                      "tipo": "crear_clase",
                      "referencia": "factura",
                      "nombre": "Factura"
                    },
                    {
                      "tipo": "crear_atributo",
                      "clase_referencia": "factura",
                      "nombre": "total",
                      "tipo_dato": "decimal"
                    },
                    {
                      "tipo": "crear_atributo",
                      "clase_referencia": "factura",
                      "nombre": "fecha",
                      "tipo_dato": "date"
                    }
                  ]
                }''',
                modelo=modelo,
            )

    set_proveedor_ia_override(FakeAudioIaProveedor())

    clave = str(uuid4())
    res_audio = client.post(
        f"/api/diagramas/{diagrama.id}/interacciones-ia/audio",
        files={"audio": ("grabacion.webm", b"fake-audio-payload", "audio/webm")},
        data={"clave_idempotencia": clave, "duracion_segundos": "3.5"},
    )
    assert res_audio.status_code == 201, res_audio.text
    data = res_audio.json()

    assert data["tipoInteraccion"] == "audio"
    assert data["entradaUsuario"] == "Crea una clase Factura con total y fecha"
    assert data["respuestaIa"] == "Clase Factura creada exitosamente."
    assert data["estado"] == "completado"

    # Verificar que en base de datos existe exactamente una interacción
    res_get = client.get(f"/api/diagramas/{diagrama.id}/interacciones-ia")
    assert res_get.status_code == 200
    items = res_get.json()["items"]
    assert len(items) == 1
    assert items[0]["entradaUsuario"] == "Crea una clase Factura con total y fecha"
    assert items[0]["tipoInteraccion"] == "audio"

    # Verificar que el plan se ejecutó creando la clase en el dominio
    from sqlmodel import select
    clases = session.exec(select(ClaseModel).where(ClaseModel.id_diagrama == diagrama.id)).all()
    assert len(clases) == 1
    assert clases[0].nombre == "Factura"

    set_proveedor_ia_override(None)


def test_interaccion_ia_api_audio_rechaza_archivo_vacio(client: TestClient, session: Session):
    usuario = BetterAuthUser(id="usuario-propietario-1", name="PropAudioVacio", email="audiovacio@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy Audio Vacio", color="azul", icono="caja", slug="proy-audio-vacio")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Pagina 1", numero=1)
    session.add(diagrama)
    session.commit()

    res = client.post(
        f"/api/diagramas/{diagrama.id}/interacciones-ia/audio",
        files={"audio": ("vacio.webm", b"", "audio/webm")},
        data={"clave_idempotencia": str(uuid4())},
    )
    assert res.status_code == 400


def test_interaccion_ia_api_audio_rechaza_transcripcion_vacia(client: TestClient, session: Session):
    usuario = BetterAuthUser(id="usuario-propietario-1", name="PropAudioSilencio", email="silencio@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy Silencio", color="azul", icono="caja", slug="proy-silencio")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Pagina 1", numero=1)
    session.add(diagrama)
    session.commit()

    class FakeSilencioProveedor(ProveedorIa):
        def generar_respuesta(self, *, modelo: str, prompt_sistema: str, mensaje_usuario: str, temperatura: float = 0.2) -> ResultadoProveedorIa:
            return ResultadoProveedorIa(texto_respuesta="", modelo=modelo)

        def generar_respuesta_audio(
            self,
            *,
            modelo: str,
            prompt_sistema: str,
            contenido_audio: bytes,
            mime_type: str,
            temperatura: float = 0.2,
        ) -> ResultadoProveedorIa:
            return ResultadoProveedorIa(
                texto_respuesta='{"transcripcion_usuario": "   ", "respuesta_usuario": "No se detectó voz.", "acciones": []}',
                modelo=modelo,
            )

    set_proveedor_ia_override(FakeSilencioProveedor())

    res = client.post(
        f"/api/diagramas/{diagrama.id}/interacciones-ia/audio",
        files={"audio": ("silencio.webm", b"silence-bytes", "audio/webm")},
        data={"clave_idempotencia": str(uuid4())},
    )
    assert res.status_code == 422
    assert "No se detectó contenido comprensible" in res.text

    set_proveedor_ia_override(None)



