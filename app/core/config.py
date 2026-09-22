from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = Field(default="API")
    ENVIRONMENT: str = Field(default="DEV")

    # ── Base de datos ─────────────────────────────────────────────────────────
    # Valor por defecto: SQLite local para poder arrancar sin configurar nada.
    # En producción (Render / Railway / Fly.io) o en local contra Neon,
    # define DATABASE_URL en tu .env con la URL completa de PostgreSQL.
    DATABASE_URL: str = Field(default="sqlite:///./dev.db")
    SQL_ECHO: bool = Field(default=False)

    # ── JWT / Auth ────────────────────────────────────────────────────────────
    # BETTER_AUTH_SECRET ya NO se usa para verificar JWTs.
    # La verificación cambió de HS256 + secret compartido a EdDSA + JWKS:
    # FastAPI descarga la clave pública desde {FRONTEND_URL}/api/auth/jwks.
    # Se conserva por si algún módulo futuro lo necesita (ej: webhooks propios).
    BETTER_AUTH_SECRET: str = Field(
        default="super-secret-key"
    )

    # URL del frontend Next.js. Se usa para construir la URL del JWKS endpoint:
    #   {FRONTEND_URL}/api/auth/jwks
    # En producción: https://tu-dominio.com
    FRONTEND_URL: str = Field(
        default="http://localhost:3000"
    )
    # Limita cuanto espera FastAPI al JWKS de Better Auth durante validacion JWT.
    JWKS_TIMEOUT_SECONDS: float = Field(
        default=5.0, gt=0
    )

    # Identificador del emisor del JWT (claim "iss").
    # Debe coincidir con JWT_ISSUER configurado en el frontend (lib/auth.ts).
    # Si está vacío, la validación del issuer se desactiva automáticamente.
    JWT_ISSUER: str = Field(default="")

    # Identificador del receptor del JWT (claim "aud").
    # Debe coincidir con JWT_AUDIENCE configurado en el frontend.
    # Si está vacío (recomendado para empezar), la validación se desactiva.
    JWT_AUDIENCE: str = Field(default="")

    # ── Colaboración / Invitaciones ───────────────────────────────────────────
    # Duración configurable de las invitaciones en días (default: 7).
    INVITACION_DURACION_DIAS: int = Field(
        default=7, gt=0
    )

    # ── Better Auth: Configuración de Roles y JWKS ────────────────────────────
    # Si en el frontend tienes instalado el plugin de 'admin', déjalo en True.
    # Si NO usas el plugin de admin en Better Auth, cambia a False en tu .env:
    #   BETTER_AUTH_ENABLE_ROLES=false
    # Al estar en False, el backend NO exige el claim 'role' en el JWT;
    # únicamente valida que el usuario esté autenticado con un token válido.
    BETTER_AUTH_ENABLE_ROLES: bool = Field(
        default=False
    )

    # URL personalizada para descargar el JWKS (útil si FastAPI corre en Docker
    # y debe comunicarse con Next.js mediante red interna como http://frontend:3000/api/auth/jwks
    # mientras el navegador usa http://localhost:3000). Si es None, usa {FRONTEND_URL}/api/auth/jwks.
    BETTER_AUTH_JWKS_URL: str | None = Field(
        default=None
    )

    @property
    def jwks_url(self) -> str:
        """URL definitiva para el JWKS endpoint de Better Auth."""
        if self.BETTER_AUTH_JWKS_URL:
            return self.BETTER_AUTH_JWKS_URL.strip()
        return f"{self.FRONTEND_URL.rstrip('/')}/api/auth/jwks"

    # ── Inteligencia Artificial / Google Gemini ──────────────────────────────
    GEMINI_API_KEY: str = Field(default="")
    GEMINI_TIMEOUT_SECONDS: float = Field(
        default=30.0, gt=0
    )
    IA_GEMINI_PRIMARY_MODEL: str = Field(
        default="gemini-3.6-flash"
    )
    IA_GEMINI_FALLBACK_MODEL: str = Field(
        default="gemini-3.5-flash-lite"
    )
    IA_GEMINI_TIMEOUT_SECONDS: float = Field(
        default=10.0, gt=0
    )
    IA_GEMINI_RETRY_BACKOFF_MS: int = Field(
        default=300, ge=0
    )
    IA_GEMINI_BREAKER_FAILURES: int = Field(
        default=2, ge=1
    )
    IA_GEMINI_BREAKER_SECONDS: int = Field(
        default=60, ge=1
    )
    IA_HISTORIAL_LIMITE: int = Field(
        default=5, ge=1, le=20
    )
    IA_TRANSCRIPCION_IDIOMA: str = Field(default="es")
    IA_TRANSCRIPCION_TIMEOUT_SECONDS: float = Field(
        default=15.0, gt=0
    )

    # ── Reconocimiento de Imagen IA ─────────────────────────────────────────
    IA_IMAGEN_MAX_SIZE_BYTES: int = Field(
        default=10 * 1024 * 1024, gt=0
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"]
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return [o.strip() for o in value.split(",") if o.strip()]
        return value  # type: ignore[return-value]

    @property
    def database_url_normalized(self) -> str:
        """
        Devuelve la DATABASE_URL lista para SQLAlchemy con el driver correcto.

        Reglas:
        - SQLite  → se mantiene tal cual (usado en DEV por defecto).
        - postgres:// o postgresql:// sin driver explícito
          → se convierte a postgresql+psycopg://  (psycopg v3, el que
            tenemos instalado vía psycopg / psycopg-binary).
        """
        url = self.DATABASE_URL.strip()

        if url.startswith("sqlite"):
            return url

        # Normalizar a psycopg v3
        if url.startswith("postgres://"):
            return "postgresql+psycopg://" + url[len("postgres://"):]
        if url.startswith("postgresql://") and "+psycopg" not in url:
            return "postgresql+psycopg://" + url[len("postgresql://"):]

        return url

    @property
    def is_sqlite(self) -> bool:
        return self.database_url_normalized.startswith("sqlite")

    model_config = SettingsConfigDict(
        env_file=(
            str(Path(__file__).resolve().parent.parent.parent / ".env"),
            ".env",
        ),
        extra="ignore",
    )


settings = Settings()
