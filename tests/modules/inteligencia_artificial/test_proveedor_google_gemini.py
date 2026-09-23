import httpx
import pytest
from unittest.mock import MagicMock, patch

from google.genai import errors, types
from app.modules.inteligencia_artificial.infrastructure.external.proveedor_google_gemini import (
    ProveedorGoogleGemini,
)
from app.modules.inteligencia_artificial.domain.exceptions import (
    ProveedorIaNoRecuperableException,
    ProveedorIaRecuperableException,
)


def test_proveedor_gemini_configura_timeout_y_desactiva_afc():
    proveedor = ProveedorGoogleGemini(api_key="fake-key-123", timeout_segundos=10.0)

    with patch("google.genai.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance

        mock_response = MagicMock()
        mock_response.text = '{"clases": []}'
        mock_instance.models.generate_content.return_value = mock_response

        res = proveedor.analizar_diagrama_imagen(
            modelo="gemini-3.6-flash",
            contenido_imagen=b"fake",
            mime_type="image/png",
            prompt_estructural="prompt",
        )

        assert res == '{"clases": []}'

        mock_client_cls.assert_called_once()
        _, client_kwargs = mock_client_cls.call_args
        assert client_kwargs["http_options"].timeout == 10000

        mock_instance.models.generate_content.assert_called_once()
        _, call_kwargs = mock_instance.models.generate_content.call_args
        config = call_kwargs["config"]
        assert isinstance(config, types.GenerateContentConfig)
        assert config.automatic_function_calling.disable is True
        assert config.http_options.timeout == 10000


def test_proveedor_gemini_timeout_httpx_lanza_recuperable():
    proveedor = ProveedorGoogleGemini(api_key="fake-key-123", timeout_segundos=10.0)

    with patch("google.genai.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance

        mock_instance.models.generate_content.side_effect = httpx.ReadTimeout("Timeout after 10.0s")

        with pytest.raises(ProveedorIaRecuperableException) as exc_info:
            proveedor.generar_respuesta(
                modelo="gemini-3.6-flash",
                prompt_sistema="system",
                mensaje_usuario="hola",
            )

        assert "Timeout" in str(exc_info.value) or "ReadTimeout" in str(exc_info.value)


def test_proveedor_gemini_503_high_demand_lanza_recuperable():
    proveedor = ProveedorGoogleGemini(api_key="fake-key-123", timeout_segundos=10.0)

    with patch("google.genai.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance

        error_503 = errors.APIError(
            503,
            {"error": {"message": "The model is overloaded. High Demand.", "code": 503}},
        )
        mock_instance.models.generate_content.side_effect = error_503

        with pytest.raises(ProveedorIaRecuperableException) as exc_info:
            proveedor.analizar_diagrama_imagen(
                modelo="gemini-3.6-flash",
                contenido_imagen=b"fake",
                mime_type="image/png",
                prompt_estructural="prompt",
            )

        assert "503" in str(exc_info.value) or "overloaded" in str(exc_info.value)


def test_proveedor_gemini_401_auth_error_lanza_no_recuperable():
    proveedor = ProveedorGoogleGemini(api_key="fake-key-123", timeout_segundos=10.0)

    with patch("google.genai.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance

        error_401 = errors.APIError(
            401,
            {"error": {"message": "API_KEY_INVALID", "code": 401}},
        )
        mock_instance.models.generate_content.side_effect = error_401

        with pytest.raises(ProveedorIaNoRecuperableException) as exc_info:
            proveedor.generar_respuesta(
                modelo="gemini-3.6-flash",
                prompt_sistema="system",
                mensaje_usuario="hola",
            )

        assert "401" in str(exc_info.value) or "autoriz" in str(exc_info.value).lower()


def test_proveedor_gemini_400_deadline_o_config_invalida_lanza_no_recuperable():
    proveedor = ProveedorGoogleGemini(api_key="fake-key-123", timeout_segundos=10.0)

    with patch("google.genai.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance

        error_400 = errors.APIError(
            400,
            {"error": {"message": "Manually set deadline 4s is too short. Minimum allowed deadline is 10s.", "code": 400}},
        )
        mock_instance.models.generate_content.side_effect = error_400

        with pytest.raises(ProveedorIaNoRecuperableException) as exc_info:
            proveedor.analizar_diagrama_imagen(
                modelo="gemini-3.6-flash",
                contenido_imagen=b"fake",
                mime_type="image/png",
                prompt_estructural="prompt",
            )

        assert "400" in str(exc_info.value) or "deadline" in str(exc_info.value).lower()


def test_proveedor_gemini_404_no_longer_available_lanza_recuperable():
    proveedor = ProveedorGoogleGemini(api_key="fake-key-123", timeout_segundos=10.0)

    with patch("google.genai.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance

        error_404 = errors.APIError(
            404,
            {"error": {"message": "This model models/gemini-2.5-flash is no longer available to new users.", "code": 404}},
        )
        mock_instance.models.generate_content.side_effect = error_404

        with pytest.raises(ProveedorIaRecuperableException) as exc_info:
            proveedor.analizar_diagrama_imagen(
                modelo="gemini-3.1-flash-lite",
                contenido_imagen=b"fake",
                mime_type="image/png",
                prompt_estructural="prompt",
            )

        assert "404" in str(exc_info.value) or "no longer available" in str(exc_info.value)

