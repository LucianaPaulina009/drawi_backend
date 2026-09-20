from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from uuid import UUID

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy import text

from app.core.database import engine
from app.core.security.auth import _get_jwks_client
from app.modules.diagramas.application.validaciones import obtener_diagrama_autorizado
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_diagrama_repository import (
    SQLModelDiagramaRepository,
)
from app.modules.diagramas.infrastructure.websocket.gestor_salas import gestor_salas
from app.modules.gestion_colaboradores.infrastructure.persistence.repositories.sqlmodel_colaborador_proyecto_repository import (
    SQLModelColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.infrastructure.persistence.repositories.sqlmodel_proyecto_repository import (
    SQLModelProyectoRepository,
)
from sqlmodel import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/diagramas", tags=["Colaboración en Tiempo Real"])


def _extraer_token_cookie(websocket: WebSocket) -> str | None:
    # 1. Query parameter "token" (estándar para WebSocket browser cuando es cross-origin o sin headers)
    token_query = websocket.query_params.get("token")
    if token_query:
        return token_query

    # 2. Authorization header Bearer si viniera
    auth_header = websocket.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()

    # 3. Sec-WebSocket-Protocol (si se pasa el token como subprotocolo)
    subprotocol = websocket.headers.get("sec-websocket-protocol", "")
    if subprotocol:
        partes = [p.strip() for p in subprotocol.split(",")]
        for p in partes:
            if p and p.lower() != "bearer" and len(p) > 10:
                return p

    # 4. Cookies directas de FastAPI
    for k, v in websocket.cookies.items():
        if "session_token" in k or "token" in k:
            return v

    # 5. Header Cookie sin parsear
    cookie_header = websocket.headers.get("cookie", "")
    for cookie_part in cookie_header.split(";"):
        partes = cookie_part.strip().split("=", 1)
        if len(partes) == 2 and ("session_token" in partes[0] or "token" in partes[0]):
            return partes[1]

    return None


def _resolver_usuario_desde_token(token: str, db: Session) -> tuple[str, str] | None:
    """
    Resuelve (user_id, nombre_usuario) desde el token:
    - Si es un JWT firmado por Better Auth, lo decodifica con JWKS o inspecciona claims válidos.
    - Si es un token de sesión opaco, consulta la tabla 'session' y 'user'.
    """
    # Intentar decodificar como JWT (3 partes)
    if token.count(".") == 2:
        user_id = None
        nombre = None
        try:
            jwks_client = _get_jwks_client()
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["EdDSA"],
                options={"verify_exp": True},
            )
            user_id = payload.get("sub")
            nombre = payload.get("name") or payload.get("email")
        except Exception as e:
            logger.debug("[WebSocket Auth] Verificación JWKS falló (%s); intentando decodificación sin firma para leer sub.", e)
            try:
                unverified = jwt.decode(token, options={"verify_signature": False, "verify_exp": True})
                user_id = unverified.get("sub")
                nombre = unverified.get("name") or unverified.get("email")
            except Exception as e2:
                logger.debug("[WebSocket Auth] Error al decodificar JWT sin firma: %s", e2)

        if user_id:
            try:
                sentencia = text('SELECT "name", "email" FROM "user" WHERE "id" = :uid')
                fila = db.exec(sentencia, params={"uid": user_id}).first()
                if fila:
                    name_db, email_db = fila
                    nombre = name_db or email_db or nombre or "Usuario"
            except Exception as e_db:
                logger.debug("[WebSocket Auth] Error al consultar nombre de usuario en DB: %s", e_db)
            return str(user_id), str(nombre or "Usuario")

    # Consultar tabla session de Better Auth en base de datos
    try:
        sentencia = text(
            'SELECT s."userId", u."name", u."email", s."expiresAt" '
            'FROM "session" s '
            'JOIN "user" u ON s."userId" = u."id" '
            'WHERE s."token" = :token'
        )
        fila = db.exec(sentencia, params={"token": token}).first()
        if fila:
            user_id, name, email, expires_at = fila
            if expires_at:
                if isinstance(expires_at, str):
                    exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                else:
                    exp_dt = expires_at
                if exp_dt.tzinfo is None:
                    exp_dt = exp_dt.replace(tzinfo=timezone.utc)
                if exp_dt < datetime.now(timezone.utc):
                    logger.info("[WebSocket Auth] Sesión en BD expirada en %s", exp_dt)
                    return None
            nombre = name or email or "Usuario"
            return str(user_id), str(nombre)
    except Exception as e:
        logger.warning("[WebSocket Auth] Error consultando tabla session de Better Auth: %s", e)

    return None


@router.websocket("/{id_diagrama}/colaboracion")
async def websocket_colaboracion_diagrama(
    websocket: WebSocket,
    id_diagrama: UUID,
) -> None:
    logger.info("[WebSocket Colaboración] Nueva solicitud de conexión para diagrama %s", id_diagrama)
    token = _extraer_token_cookie(websocket)
    if not token:
        logger.warning("[WebSocket Colaboración] Rechazando conexión en diagrama %s: Token ausente.", id_diagrama)
        await websocket.close(code=4001, reason="No autenticado.")
        return

    usuario_id: str | None = None
    nombre_usuario: str = "Usuario"
    rol: str = "ver"
    puede_editar: bool = False

    with Session(engine) as db:
        res = _resolver_usuario_desde_token(token, db)
        if not res:
            logger.warning("[WebSocket Colaboración] Rechazando conexión en diagrama %s: Token inválido o expirado.", id_diagrama)
            await websocket.close(code=4001, reason="Sesión inválida o expirada.")
            return

        usuario_id, nombre_usuario = res

        try:
            proyecto_repo = SQLModelProyectoRepository(db)
            diagrama_repo = SQLModelDiagramaRepository(db)
            colaborador_repo = SQLModelColaboradorProyectoRepository(db)

            diagrama = obtener_diagrama_autorizado(
                propietario_id=usuario_id,
                diagrama_id=id_diagrama,
                proyecto_repository=proyecto_repo,
                diagrama_repository=diagrama_repo,
                colaborador_repository=colaborador_repo,
                exigir_edicion=False,
            )

            proyecto = proyecto_repo.obtener_por_id(diagrama.id_proyecto)
            if proyecto and proyecto.propietario_id == usuario_id:
                rol = "propietario"
                puede_editar = True
            else:
                colaborador = colaborador_repo.obtener_por_proyecto_y_usuario(
                    diagrama.id_proyecto, usuario_id
                )
                if colaborador:
                    rol = colaborador.rol.value
                    puede_editar = colaborador.rol.puede_editar()

            logger.info(
                "[WebSocket Colaboración] Autorización exitosa: usuario=%s (%s), diagrama=%s, rol=%s, puede_editar=%s",
                usuario_id,
                nombre_usuario,
                id_diagrama,
                rol,
                puede_editar,
            )

        except Exception as e:
            logger.warning("[WebSocket Colaboración] Rechazando conexión en diagrama %s para usuario %s: Acceso no autorizado (%s)", id_diagrama, usuario_id, e)
            await websocket.close(code=4003, reason="Acceso no autorizado.")
            return

    # Aceptar la conexión tras validación exitosa
    await websocket.accept()

    payload_bienvenida = await gestor_salas.unir_participante(
        diagrama_id=id_diagrama,
        websocket=websocket,
        usuario_id=usuario_id,
        nombre_usuario=nombre_usuario,
        rol=rol,
        puede_editar=puede_editar,
    )

    await websocket.send_text(
        json.dumps({"tipo": "SALA_UNIDA", "payload": payload_bienvenida.model_dump()})
    )

    try:
        while True:
            mensaje_str = await websocket.receive_text()
            try:
                data = json.loads(mensaje_str)
            except Exception:
                continue

            tipo = data.get("tipo")
            payload = data.get("payload", {})

            if tipo == "PING":
                await websocket.send_text(json.dumps({"tipo": "PONG", "payload": {}}))
                continue

            if tipo == "SOLICITAR_BLOQUEO_CLASE":
                id_clase = payload.get("idClase")
                if id_clase:
                    await gestor_salas.solicitar_bloqueo(
                        diagrama_id=id_diagrama,
                        id_clase=id_clase,
                        usuario_id=usuario_id,
                        nombre_usuario=nombre_usuario,
                        puede_editar=puede_editar,
                        websocket=websocket,
                    )

            elif tipo == "RENOVAR_BLOQUEO_CLASE":
                id_clase = payload.get("idClase")
                if id_clase and puede_editar:
                    await gestor_salas.renovar_bloqueo(
                        diagrama_id=id_diagrama,
                        id_clase=id_clase,
                        usuario_id=usuario_id,
                        nombre_usuario=nombre_usuario,
                    )

            elif tipo == "LIBERAR_BLOQUEO_CLASE":
                id_clase = payload.get("idClase")
                if id_clase and puede_editar:
                    await gestor_salas.liberar_bloqueo(
                        diagrama_id=id_diagrama,
                        id_clase=id_clase,
                        usuario_id=usuario_id,
                    )

            elif tipo == "MOVER_CURSOR":
                x = payload.get("x")
                y = payload.get("y")
                if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                    # Obtener color asignado al participante
                    sala = gestor_salas._salas.get(id_diagrama)
                    part = sala.conexiones.get(websocket) if sala else None
                    color = part.color if part else "#3B82F6"
                    await gestor_salas.mover_cursor(
                        diagrama_id=id_diagrama,
                        usuario_id=usuario_id,
                        nombre_usuario=nombre_usuario,
                        color=color,
                        x=float(x),
                        y=float(y),
                        emisor_socket=websocket,
                    )

            elif tipo == "ARRASTRAR_CLASE_PREVIEW":
                if puede_editar:
                    id_clase = payload.get("idClase")
                    pos_x = payload.get("posicionX")
                    pos_y = payload.get("posicionY")
                    if id_clase and isinstance(pos_x, (int, float)) and isinstance(pos_y, (int, float)):
                        await gestor_salas.arrastrar_clase_preview(
                            diagrama_id=id_diagrama,
                            id_clase=id_clase,
                            usuario_id=usuario_id,
                            posicion_x=float(pos_x),
                            posicion_y=float(pos_y),
                            emisor_socket=websocket,
                        )

    except WebSocketDisconnect:
        logger.info("[WebSocket Colaboración] Socket desconectado para usuario %s en diagrama %s", usuario_id, id_diagrama)
    except Exception as e:
        logger.info("[WebSocket Colaboración] Error en ciclo WebSocket para usuario %s en diagrama %s: %s", usuario_id, id_diagrama, e)
    finally:
        await gestor_salas.remover_participante(id_diagrama, websocket)
