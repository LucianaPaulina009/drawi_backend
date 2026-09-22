from io import BytesIO
from unittest.mock import MagicMock
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.modules.diagramas.infrastructure.persistence.models.diagrama_model import DiagramaModel
from app.modules.gestion_colaboradores.infrastructure.persistence.models.colaborador_proyecto_model import (
    ColaboradorProyectoModel,
)
from app.modules.gestion_proyectos.infrastructure.persistence.models.proyecto_model import ProyectoModel
from app.modules.inteligencia_artificial.application.ports.providers.proveedor_ia import ProveedorIa
from app.modules.inteligencia_artificial.application.ports.providers.proveedor_transcripcion import (
    ProveedorTranscripcion,
    ResultadoTranscripcion,
)
from app.modules.inteligencia_artificial.application.services.estrategia_modelos_gemini import (
    EstrategiaModelosGemini,
)
from app.modules.inteligencia_artificial.domain.exceptions import (
    AudioVacioException,
    DuracionAudioExcedidaException,
    FormatoAudioNoSoportadoException,
    ProveedorIaRecuperableException,
    ProveedorTranscripcionException,
    ProveedorTranscripcionRecuperableException,
    TamanoAudioExcedidoException,
)
from app.modules.inteligencia_artificial.infrastructure.api.routers.interaccion_ia_router import (
    set_proveedor_transcripcion_override,
)
from app.modules.inteligencia_artificial.infrastructure.external.proveedor_transcripcion_gemini import (
    ProveedorTranscripcionGemini,
)
from app.modules.inteligencia_artificial.infrastructure.persistence.models.interaccion_ia_model import (
    InteraccionIaModel,
)
from app.shared.infrastructure.db.better_auth import BetterAuthUser


class FakeProveedorTranscripcion(ProveedorTranscripcion):
    def __init__(
        self,
        texto_a_retornar: str = "Crea una clase Cliente",
        debe_fallar: bool = False,
        recuperable: bool = False,
    ) -> None:
        self.texto_a_retornar = texto_a_retornar
        self.debe_fallar = debe_fallar
        self.recuperable = recuperable

    def transcribir_audio(
        self,
        *,
        contenido_audio: bytes,
        mime_type: str,
        idioma: str | None = None,
    ) -> ResultadoTranscripcion:
        if self.recuperable:
            raise ProveedorTranscripcionRecuperableException()
        if self.debe_fallar:
            raise ProveedorTranscripcionException("Error en proveedor Gemini")
        return ResultadoTranscripcion(texto=self.texto_a_retornar, idioma=idioma or "es")


@pytest.fixture(autouse=True)
def cleanup_provider_override():
    yield
    set_proveedor_transcripcion_override(None)


def test_transcripcion_audio_exitosa(client: TestClient, session: Session):
    usuario = BetterAuthUser(id="usuario-propietario-1", name="Prop", email="prop@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy Audio", color="azul", icono="caja", slug="proy-audio")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Diagrama 1", numero=1)
    session.add(diagrama)
    session.commit()

    fake_provider = FakeProveedorTranscripcion(texto_a_retornar="Crea una clase Cliente con atributo nombre")
    set_proveedor_transcripcion_override(fake_provider)

    audio_bytes = b"\x1a\x45\xdf\xa3" + b"dummy webm audio content"
    files = {"audio": ("grabacion.webm", BytesIO(audio_bytes), "audio/webm")}
    data = {"duracion_segundos": "3.5", "idioma": "es-419"}

    response = client.post(
        f"/api/diagramas/{diagrama.id}/transcripciones-ia",
        files=files,
        data=data,
    )

    assert response.status_code == 200, response.text
    json_data = response.json()
    assert json_data["texto"] == "Crea una clase Cliente con atributo nombre"
    assert json_data["idioma"] == "es-419"

    # Verificar que NO se persistió ninguna InteraccionIa ni audio en la base de datos
    interacciones = session.exec(select(InteraccionIaModel)).all()
    assert len(interacciones) == 0


def test_transcripcion_audio_vacio_retorna_400(client: TestClient, session: Session):
    usuario = BetterAuthUser(id="usuario-propietario-1", name="Prop", email="prop@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy Audio", color="azul", icono="caja", slug="proy-audio-2")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Diagrama 1", numero=1)
    session.add(diagrama)
    session.commit()

    files = {"audio": ("vacio.webm", BytesIO(b""), "audio/webm")}
    response = client.post(
        f"/api/diagramas/{diagrama.id}/transcripciones-ia",
        files=files,
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "AUDIO_VACIO"


def test_transcripcion_formato_no_soportado_retorna_415(client: TestClient, session: Session):
    usuario = BetterAuthUser(id="usuario-propietario-1", name="Prop", email="prop@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy Audio", color="azul", icono="caja", slug="proy-audio-3")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Diagrama 1", numero=1)
    session.add(diagrama)
    session.commit()

    files = {"audio": ("texto.txt", BytesIO(b"no es audio"), "text/plain")}
    response = client.post(
        f"/api/diagramas/{diagrama.id}/transcripciones-ia",
        files=files,
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "FORMATO_AUDIO_NO_SOPORTADO"


def test_transcripcion_duracion_excedida_retorna_413(client: TestClient, session: Session):
    usuario = BetterAuthUser(id="usuario-propietario-1", name="Prop", email="prop@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy Audio", color="azul", icono="caja", slug="proy-audio-4")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Diagrama 1", numero=1)
    session.add(diagrama)
    session.commit()

    files = {"audio": ("largo.webm", BytesIO(b"audio"), "audio/webm")}
    data = {"duracion_segundos": "65.0"}
    response = client.post(
        f"/api/diagramas/{diagrama.id}/transcripciones-ia",
        files=files,
        data=data,
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "DURACION_AUDIO_EXCEDIDA"


def test_transcripcion_tamano_excedido_retorna_413(client: TestClient, session: Session):
    usuario = BetterAuthUser(id="usuario-propietario-1", name="Prop", email="prop@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy Audio", color="azul", icono="caja", slug="proy-audio-5")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Diagrama 1", numero=1)
    session.add(diagrama)
    session.commit()

    # 10 MiB + 1 byte
    audio_pesado = b"a" * (10 * 1024 * 1024 + 1)
    files = {"audio": ("pesado.webm", BytesIO(audio_pesado), "audio/webm")}
    response = client.post(
        f"/api/diagramas/{diagrama.id}/transcripciones-ia",
        files=files,
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "TAMANO_AUDIO_EXCEDIDO"


def test_transcripcion_diagrama_no_autorizado_retorna_403_o_404(client: TestClient, session: Session):
    # 1. Usuario ajeno sin acceso al proyecto -> 404 (oculta existencia del proyecto)
    otro_usuario = BetterAuthUser(id="usuario-ajeno", name="Ajeno", email="ajeno@drawi.com", email_verified=True)
    session.add(otro_usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=otro_usuario.id, nombre="Proy Ajeno", color="azul", icono="caja", slug="proy-ajeno")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Diagrama Ajeno", numero=1)
    session.add(diagrama)
    session.commit()

    files = {"audio": ("audio.webm", BytesIO(b"audio"), "audio/webm")}
    response_404 = client.post(
        f"/api/diagramas/{diagrama.id}/transcripciones-ia",
        files=files,
    )
    assert response_404.status_code == 404

    # 2. Colaborador bloqueado -> 403
    colaborador_bloqueado = ColaboradorProyectoModel(
        id_proyecto=proyecto.id,
        id_usuario="usuario-propietario-1",
        rol="ver",
        estado="bloqueado",
    )
    session.add(colaborador_bloqueado)
    session.commit()

    response_403 = client.post(
        f"/api/diagramas/{diagrama.id}/transcripciones-ia",
        files=files,
    )
    assert response_403.status_code == 403


def test_transcripcion_fallo_proveedor_retorna_502_y_503(client: TestClient, session: Session):
    usuario = BetterAuthUser(id="usuario-propietario-1", name="Prop", email="prop@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy Audio", color="azul", icono="caja", slug="proy-audio-6")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Diagrama 1", numero=1)
    session.add(diagrama)
    session.commit()

    # Fallo 502
    set_proveedor_transcripcion_override(FakeProveedorTranscripcion(debe_fallar=True))
    files = {"audio": ("audio.webm", BytesIO(b"audio"), "audio/webm")}
    response_502 = client.post(f"/api/diagramas/{diagrama.id}/transcripciones-ia", files=files)
    assert response_502.status_code == 502
    assert response_502.json()["error"]["code"] == "ERROR_PROVEEDOR_TRANSCRIPCION"

    # Fallo 503 (recuperable)
    set_proveedor_transcripcion_override(FakeProveedorTranscripcion(recuperable=True))
    files = {"audio": ("audio.webm", BytesIO(b"audio"), "audio/webm")}
    response_503 = client.post(f"/api/diagramas/{diagrama.id}/transcripciones-ia", files=files)
    assert response_503.status_code == 503
    assert response_503.json()["error"]["code"] == "ERROR_RECUPERABLE_PROVEEDOR_TRANSCRIPCION"


def test_proveedor_transcripcion_gemini_exito():
    mock_estrategia = MagicMock(spec=EstrategiaModelosGemini)
    mock_estrategia.transcribir_con_fallback.return_value = "Texto transcrito exitosamente"

    proveedor = ProveedorTranscripcionGemini(estrategia=mock_estrategia)
    resultado = proveedor.transcribir_audio(
        contenido_audio=b"dummy_bytes",
        mime_type="audio/webm",
        idioma="es",
    )

    assert isinstance(resultado, ResultadoTranscripcion)
    assert resultado.texto == "Texto transcrito exitosamente"
    assert resultado.idioma == "es"
    mock_estrategia.transcribir_con_fallback.assert_called_once_with(
        contenido_audio=b"dummy_bytes",
        mime_type="audio/webm",
        idioma="es",
    )


def test_proveedor_transcripcion_gemini_error_recuperable():
    mock_estrategia = MagicMock(spec=EstrategiaModelosGemini)
    mock_estrategia.transcribir_con_fallback.side_effect = ProveedorIaRecuperableException("Rate limit")

    proveedor = ProveedorTranscripcionGemini(estrategia=mock_estrategia)
    with pytest.raises(ProveedorTranscripcionRecuperableException):
        proveedor.transcribir_audio(
            contenido_audio=b"dummy_bytes",
            mime_type="audio/webm",
        )


def test_estrategia_modelos_gemini_transcribir_fallback():
    mock_proveedor = MagicMock(spec=ProveedorIa)
    # Falla en intento 1 y reintento del primer modelo, tiene éxito en el modelo de fallback
    mock_proveedor.transcribir_audio.side_effect = [
        ProveedorIaRecuperableException("Overloaded"),
        ProveedorIaRecuperableException("Overloaded (retry)"),
        "Resultado de fallback",
    ]

    estrategia = EstrategiaModelosGemini(
        proveedor=mock_proveedor,
        modelos=["gemini-2.5-flash", "gemini-2.0-flash"],
        retry_backoff_ms=0,
    )

    texto = estrategia.transcribir_con_fallback(
        contenido_audio=b"audio_bytes",
        mime_type="audio/webm",
    )

    assert texto == "Resultado de fallback"
    assert mock_proveedor.transcribir_audio.call_count == 3
    mock_proveedor.transcribir_audio.assert_any_call(
        modelo="gemini-2.5-flash",
        contenido_audio=b"audio_bytes",
        mime_type="audio/webm",
        idioma="es",
    )
    mock_proveedor.transcribir_audio.assert_any_call(
        modelo="gemini-2.0-flash",
        contenido_audio=b"audio_bytes",
        mime_type="audio/webm",
        idioma="es",
    )


