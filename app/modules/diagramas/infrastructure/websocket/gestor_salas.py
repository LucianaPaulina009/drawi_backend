from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from uuid import UUID
from fastapi import WebSocket

from app.modules.diagramas.infrastructure.websocket.schemas_ws import (
    BloqueoConcedidoPayload,
    BloqueoDenegadoPayload,
    BloqueoLiberadoPayload,
    BloqueoWS,
    CursorActualizadoPayload,
    DragClaseActualizadoPayload,
    MutacionConfirmadaPayload,
    ParticipanteDesconectadoPayload,
    ParticipanteWS,
    SalaUnidaPayload,
)

logger = logging.getLogger(__name__)

PALETA_COLORES = [
    "#3B82F6",  # Azul
    "#10B981",  # Verde
    "#F59E0B",  # Amarillo / Ámbar
    "#EF4444",  # Rojo
    "#8B5CF6",  # Púrpura
    "#EC4899",  # Rosa
    "#14B8A6",  # Teal
    "#F97316",  # Naranja
]


def _asignar_color(usuario_id: str) -> str:
    indice = abs(hash(usuario_id)) % len(PALETA_COLORES)
    return PALETA_COLORES[indice]


@dataclass
class ParticipanteConectado:
    usuario_id: str
    nombre_usuario: str
    color: str
    rol: str
    puede_editar: bool
    socket: WebSocket
    ultimo_latido: float = field(default_factory=time.time)


@dataclass
class BloqueoClaseInfo:
    id_clase: str
    id_usuario: str
    nombre_usuario: str
    expira_en: float  # Epoch en segundos


@dataclass
class SalaEfimera:
    diagrama_id: UUID
    conexiones: dict[WebSocket, ParticipanteConectado] = field(default_factory=dict)
    bloqueos: dict[str, BloqueoClaseInfo] = field(default_factory=dict)

    def limpiar_bloqueos_expirados(self) -> list[str]:
        ahora = time.time()
        liberados: list[str] = []
        for id_clase, bloqueo in list(self.bloqueos.items()):
            if bloqueo.expira_en <= ahora:
                liberados.append(id_clase)
                del self.bloqueos[id_clase]
        return liberados


class GestorSalasColaboracion:
    """
    Gestor en memoria de salas de colaboración para una sola instancia de backend.
    Las salas se crean al conectar el primer participante y se destruyen al quedar vacías.
    """

    def __init__(self) -> None:
        self._salas: dict[UUID, SalaEfimera] = {}
        self._lock = asyncio.Lock()

    def _obtener_o_crear_sala(self, diagrama_id: UUID) -> SalaEfimera:
        if diagrama_id not in self._salas:
            self._salas[diagrama_id] = SalaEfimera(diagrama_id=diagrama_id)
        return self._salas[diagrama_id]

    async def unir_participante(
        self,
        diagrama_id: UUID,
        websocket: WebSocket,
        usuario_id: str,
        nombre_usuario: str,
        rol: str,
        puede_editar: bool,
    ) -> SalaUnidaPayload:
        async with self._lock:
            sala = self._obtener_o_crear_sala(diagrama_id)
            color = _asignar_color(usuario_id)

            participante = ParticipanteConectado(
                usuario_id=usuario_id,
                nombre_usuario=nombre_usuario,
                color=color,
                rol=rol,
                puede_editar=puede_editar,
                socket=websocket,
                ultimo_latido=time.time(),
            )
            sala.conexiones[websocket] = participante

            # Limpiar locks expirados
            expirados = sala.limpiar_bloqueos_expirados()

        for id_exp in expirados:
            await self._broadcast_a_sala(
                diagrama_id,
                "BLOQUEO_CLASE_LIBERADO",
                BloqueoLiberadoPayload(idClase=id_exp).model_dump(),
            )

        # Preparar payload de bienvenida
        participantes_lista: list[ParticipanteWS] = []
        usuarios_vistos: set[str] = set()
        for p in sala.conexiones.values():
            if p.usuario_id not in usuarios_vistos:
                usuarios_vistos.add(p.usuario_id)
                participantes_lista.append(
                    ParticipanteWS(
                        idUsuario=p.usuario_id,
                        nombreUsuario=p.nombre_usuario,
                        color=p.color,
                        rol=p.rol,
                        puedeEditar=p.puede_editar,
                    )
                )

        bloqueos_lista = [
            BloqueoWS(
                idClase=b.id_clase,
                idUsuario=b.id_usuario,
                nombreUsuario=b.nombre_usuario,
                expiraEn=int(b.expira_en * 1000),
            )
            for b in sala.bloqueos.values()
        ]

        return SalaUnidaPayload(
            diagramaId=str(diagrama_id),
            miUsuarioId=usuario_id,
            miRol=rol,
            puedeEditar=puede_editar,
            participantes=participantes_lista,
            bloqueos=bloqueos_lista,
        )

    async def remover_participante(
        self, diagrama_id: UUID, websocket: WebSocket
    ) -> None:
        usuario_id: str | None = None
        locks_a_liberar: list[str] = []
        queda_otra_conexion = False

        async with self._lock:
            sala = self._salas.get(diagrama_id)
            if not sala:
                return

            participante = sala.conexiones.pop(websocket, None)
            if participante:
                usuario_id = participante.usuario_id
                # Verificar si el mismo usuario sigue conectado en otra pestaña
                queda_otra_conexion = any(
                    p.usuario_id == usuario_id for p in sala.conexiones.values()
                )

                if not queda_otra_conexion:
                    # Liberar todos los locks de este usuario inmediatamente
                    for id_clase, b in list(sala.bloqueos.items()):
                        if b.id_usuario == usuario_id:
                            locks_a_liberar.append(id_clase)
                            del sala.bloqueos[id_clase]

            if len(sala.conexiones) == 0:
                self._salas.pop(diagrama_id, None)

        # Broadcast liberaciones y desconexión fuera del lock
        for id_clase in locks_a_liberar:
            await self._broadcast_a_sala(
                diagrama_id,
                "BLOQUEO_CLASE_LIBERADO",
                BloqueoLiberadoPayload(idClase=id_clase).model_dump(),
            )

        if usuario_id and not queda_otra_conexion:
            await self._broadcast_a_sala(
                diagrama_id,
                "PARTICIPANTE_DESCONECTADO",
                ParticipanteDesconectadoPayload(idUsuario=usuario_id).model_dump(),
            )

    async def solicitar_bloqueo(
        self,
        diagrama_id: UUID,
        id_clase: str,
        usuario_id: str,
        nombre_usuario: str,
        puede_editar: bool,
        websocket: WebSocket,
    ) -> bool:
        if not puede_editar:
            await self._enviar_a_socket(
                websocket,
                "BLOQUEO_CLASE_DENEGADO",
                BloqueoDenegadoPayload(
                    idClase=id_clase,
                    bloqueadoPor="Sistema",
                    mensaje="Permisos insuficientes para editar clases.",
                ).model_dump(),
            )
            return False

        ahora = time.time()
        expira_en = ahora + 30.0  # 30s TTL
        concedido = False
        duenio_actual = ""

        async with self._lock:
            sala = self._salas.get(diagrama_id)
            if not sala:
                return False

            sala.limpiar_bloqueos_expirados()
            bloqueo_actual = sala.bloqueos.get(id_clase)

            if bloqueo_actual is None or bloqueo_actual.id_usuario == usuario_id:
                sala.bloqueos[id_clase] = BloqueoClaseInfo(
                    id_clase=id_clase,
                    id_usuario=usuario_id,
                    nombre_usuario=nombre_usuario,
                    expira_en=expira_en,
                )
                concedido = True
            else:
                duenio_actual = bloqueo_actual.nombre_usuario

        if concedido:
            await self._broadcast_a_sala(
                diagrama_id,
                "BLOQUEO_CLASE_CONCEDIDO",
                BloqueoConcedidoPayload(
                    idClase=id_clase,
                    idUsuario=usuario_id,
                    nombreUsuario=nombre_usuario,
                    expiraEn=int(expira_en * 1000),
                ).model_dump(),
            )
            return True
        else:
            await self._enviar_a_socket(
                websocket,
                "BLOQUEO_CLASE_DENEGADO",
                BloqueoDenegadoPayload(
                    idClase=id_clase,
                    bloqueadoPor=duenio_actual,
                    mensaje=f"La clase está siendo editada por {duenio_actual}.",
                ).model_dump(),
            )
            return False

    async def renovar_bloqueo(
        self,
        diagrama_id: UUID,
        id_clase: str,
        usuario_id: str,
        nombre_usuario: str,
    ) -> bool:
        ahora = time.time()
        expira_en = ahora + 30.0
        renovado = False

        async with self._lock:
            sala = self._salas.get(diagrama_id)
            if not sala:
                return False

            bloqueo = sala.bloqueos.get(id_clase)
            if bloqueo and bloqueo.id_usuario == usuario_id:
                bloqueo.expira_en = expira_en
                renovado = True

        if renovado:
            await self._broadcast_a_sala(
                diagrama_id,
                "BLOQUEO_CLASE_CONCEDIDO",
                BloqueoConcedidoPayload(
                    idClase=id_clase,
                    idUsuario=usuario_id,
                    nombreUsuario=nombre_usuario,
                    expiraEn=int(expira_en * 1000),
                ).model_dump(),
            )
        return renovado

    async def liberar_bloqueo(
        self, diagrama_id: UUID, id_clase: str, usuario_id: str
    ) -> None:
        liberado = False
        async with self._lock:
            sala = self._salas.get(diagrama_id)
            if not sala:
                return

            bloqueo = sala.bloqueos.get(id_clase)
            if bloqueo and bloqueo.id_usuario == usuario_id:
                del sala.bloqueos[id_clase]
                liberado = True

        if liberado:
            await self._broadcast_a_sala(
                diagrama_id,
                "BLOQUEO_CLASE_LIBERADO",
                BloqueoLiberadoPayload(idClase=id_clase).model_dump(),
            )

    async def mover_cursor(
        self,
        diagrama_id: UUID,
        usuario_id: str,
        nombre_usuario: str,
        color: str,
        x: float,
        y: float,
        emisor_socket: WebSocket,
    ) -> None:
        payload = CursorActualizadoPayload(
            idUsuario=usuario_id,
            nombreUsuario=nombre_usuario,
            color=color,
            x=x,
            y=y,
            actualizadoEn=int(time.time() * 1000),
        ).model_dump()

        await self._broadcast_a_sala(
            diagrama_id, "CURSOR_ACTUALIZADO", payload, excluir_socket=emisor_socket
        )

    async def arrastrar_clase_preview(
        self,
        diagrama_id: UUID,
        id_clase: str,
        usuario_id: str,
        posicion_x: float,
        posicion_y: float,
        emisor_socket: WebSocket,
    ) -> None:
        payload = DragClaseActualizadoPayload(
            idClase=id_clase,
            idUsuario=usuario_id,
            posicionX=posicion_x,
            posicionY=posicion_y,
        ).model_dump()

        await self._broadcast_a_sala(
            diagrama_id, "DRAG_CLASE_ACTUALIZADO", payload, excluir_socket=emisor_socket
        )

    async def limpiar_bloqueos_expirados_global(self) -> list[tuple[UUID, str]]:
        liberaciones: list[tuple[UUID, str]] = []
        async with self._lock:
            for diagrama_id, sala in list(self._salas.items()):
                expirados = sala.limpiar_bloqueos_expirados()
                for id_clase in expirados:
                    liberaciones.append((diagrama_id, id_clase))
        for diagrama_id, id_clase in liberaciones:
            logger.info(
                "[GestorSalas] TTL expirado para bloqueo de clase %s en sala %s. Emitiendo BLOQUEO_CLASE_LIBERADO",
                id_clase,
                diagrama_id,
            )
            await self._broadcast_a_sala(
                diagrama_id,
                "BLOQUEO_CLASE_LIBERADO",
                BloqueoLiberadoPayload(idClase=id_clase).model_dump(),
            )
        return liberaciones

    async def difundir_mutacion(
        self,
        diagrama_id: UUID,
        action_id: str,
        tipo_operacion: str,
        emisor_id: str,
        efectos: dict,
    ) -> None:
        sala = self._salas.get(diagrama_id)
        cant_sockets = len(sala.conexiones) if sala else 0
        logger.info(
            "[WebSocket Broadcast] MUTACION_CONFIRMADA para sala %s (actionId=%s, op=%s, emisor=%s, sockets=%d)",
            diagrama_id,
            action_id,
            tipo_operacion,
            emisor_id,
            cant_sockets,
        )

        payload = MutacionConfirmadaPayload(
            diagramaId=str(diagrama_id),
            actionId=action_id,
            tipoOperacion=tipo_operacion,
            emisorId=emisor_id,
            efectos=efectos,
        ).model_dump()

        await self._broadcast_a_sala(diagrama_id, "MUTACION_CONFIRMADA", payload)

    async def _broadcast_a_sala(
        self,
        diagrama_id: UUID,
        tipo: str,
        payload: dict | None = None,
        excluir_socket: WebSocket | None = None,
    ) -> None:
        sala = self._salas.get(diagrama_id)
        if not sala:
            return

        mensaje_str = json.dumps({"tipo": tipo, "payload": payload or {}})
        sockets = [s for s in list(sala.conexiones.keys()) if s != excluir_socket]

        for s in sockets:
            try:
                await s.send_text(mensaje_str)
            except Exception as e:
                logger.debug("Error enviando frame a socket en sala %s: %s", diagrama_id, e)

    async def _enviar_a_socket(
        self, websocket: WebSocket, tipo: str, payload: dict
    ) -> None:
        try:
            await websocket.send_text(json.dumps({"tipo": tipo, "payload": payload}))
        except Exception as e:
            logger.debug("Error enviando frame a socket individual: %s", e)


# Instancia singleton del gestor de salas
gestor_salas = GestorSalasColaboracion()
