# app/main.py
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine, init_db
from app.core.dependencies import get_event_bus
from app.core.errors.handlers import configurar_manejadores_excepciones
from app.core.events.subscriptions import configure_event_subscriptions

# Configuración de logging estándar
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ==============================================================================
# IMPORTACIONES DE ROUTERS (descomenta cuando crees los módulos)
# ==============================================================================
# from app.modules.module_a.infrastructure.api.routers.module_a_router import router as module_a_router
# from app.modules.module_b.infrastructure.api.routers.module_b_router import router as module_b_router


# ==============================================================================
# LIFESPAN
# ==============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Ciclo de vida de la aplicación.

    - DEV  + SQLite   → crea tablas automáticamente (rápido para prototipar).
    - DEV  + Postgres → se asume que Alembic ya corrió (`alembic upgrade head`).
    - PROD            → Alembic siempre. init_db() nunca se llama.
    """
    if settings.ENVIRONMENT == "DEV" and settings.is_sqlite:
        logger.info("DEV + SQLite — inicializando tablas con SQLModel...")
        init_db()
    else:
        logger.info(
            "Modo %s con %s — las migraciones deben ejecutarse con Alembic.",
            settings.ENVIRONMENT,
            "SQLite" if settings.is_sqlite else "PostgreSQL",
        )

    # ── Event Bus — registrar suscripciones de handlers ────────────────────
    configure_event_subscriptions(get_event_bus())
    logger.info("Event Bus configurado con suscripciones del sistema.")
    logger.info(
        "GEMINI_API_KEY configurada: %s",
        bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip()),
    )

    yield


# ==============================================================================
# APP FASTAPI
# ==============================================================================
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    lifespan=lifespan,
    swagger_ui_parameters={
        "persistAuthorization": True,  # Mantiene el token JWT al recargar Swagger
    },
)

configurar_manejadores_excepciones(app)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# RUTAS GENÉRICAS / HEALTHCHECK
# ==============================================================================
@app.get("/health", tags=["System"], summary="Verificar estado del sistema y BD")
def health_check():
    """
    Comprueba el estado de la API y la conectividad real con la base de datos.
    Devuelve 200 si todo está saludable, o 503 si la BD no responde.
    """
    db_status = "connected"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("Healthcheck: fallo al conectar con la base de datos: %s", exc)
        db_status = "unreachable"

    payload = {
        "status": "ok" if db_status == "connected" else "degraded",
        "database": {
            "engine": "SQLite" if settings.is_sqlite else "PostgreSQL",
            "status": db_status,
        },
        "environment": settings.ENVIRONMENT,
    }

    if db_status != "connected":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload,
        )

    return payload


# ==============================================================================
# REGISTRO DE ROUTERS
# ==============================================================================
from app.modules.gestion_proyectos.infrastructure.api.routers.proyecto_router import (
    router as proyecto_router,
)
from app.modules.gestion_colaboradores.infrastructure.api.routers.invitacion_router import (
    router as invitacion_router,
)
from app.modules.gestion_colaboradores.infrastructure.api.routers.colaborador_router import (
    router as colaborador_router,
)
from app.modules.diagramas.infrastructure.api.routers.diagrama_router import (
    router as diagrama_router,
)
from app.modules.diagramas.infrastructure.api.routers.clase_router import (
    router as clase_router,
)
from app.modules.diagramas.infrastructure.api.routers.atributo_router import router as atributo_router
from app.modules.diagramas.infrastructure.api.routers.relacion_router import (
    router as relacion_router,
)
from app.modules.diagramas.infrastructure.api.routers.referencia_fk_router import (
    router as referencia_fk_router,
)
from app.modules.diagramas.infrastructure.api.routers.estructura_relacion_nm_router import (
    router as estructura_relacion_nm_router,
)
from app.modules.diagramas.infrastructure.api.routers.colaboracion_ws_router import (
    router as colaboracion_ws_router,
)
from app.modules.diagramas.infrastructure.api.routers.operacion_diagrama_router import (
    router as operacion_diagrama_router,
)
from app.modules.inteligencia_artificial.infrastructure.api.routers.interaccion_ia_router import (
    router as interaccion_ia_router,
)
from app.modules.generacion_backend.infrastructure.api.routers.generacion_backend_router import (
    router as generacion_backend_router,
)
from app.modules.intercambio_enterprise_architect.infrastructure.api.routers.intercambio_enterprise_architect_router import (
    router as intercambio_enterprise_architect_router,
)

app.include_router(proyecto_router, prefix="/api")
app.include_router(invitacion_router, prefix="/api")
app.include_router(colaborador_router, prefix="/api")
app.include_router(diagrama_router, prefix="/api")
app.include_router(clase_router, prefix="/api")
app.include_router(atributo_router, prefix="/api")
app.include_router(relacion_router, prefix="/api")
app.include_router(referencia_fk_router, prefix="/api")
app.include_router(estructura_relacion_nm_router, prefix="/api")
app.include_router(interaccion_ia_router, prefix="/api")
app.include_router(generacion_backend_router, prefix="/api")
app.include_router(intercambio_enterprise_architect_router, prefix="/api")
app.include_router(colaboracion_ws_router, prefix="/api")
app.include_router(operacion_diagrama_router)



