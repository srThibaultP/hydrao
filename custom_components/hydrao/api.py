"""Hydrao API client for hydrao-ble-raspberry REST/WebSocket gateway."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable

import aiohttp

_LOGGER = logging.getLogger(__name__)


class HydraoApiClient:
    """Client HTTP + WebSocket pour le gateway hydrao-ble-raspberry."""

    def __init__(self, host: str, port: int, session: aiohttp.ClientSession) -> None:
        self._host = host
        self._port = port
        self._session = session
        self._base_url = f"http://{host}:{port}"
        self._ws_url = f"ws://{host}:{port}/ws/live"
        self._ws_task: asyncio.Task | None = None
        self._live_callbacks: list[Callable[[dict], None]] = []

    # ------------------------------------------------------------------
    # REST
    # ------------------------------------------------------------------

    async def get_devices(self) -> list[dict[str, Any]]:
        """Retourne la liste de tous les pommeaux détectés."""
        url = f"{self._base_url}/devices"
        async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            resp.raise_for_status()
            data = await resp.json()
        return data.get("devices", [])

    async def get_showers(self, device_id: str, limit: int = 1) -> list[dict[str, Any]]:
        """Retourne l'historique de douches d'un appareil (dernière par défaut)."""
        url = f"{self._base_url}/devices/{device_id}/showers"
        params = {"limit": limit, "offset": 0}
        async with self._session.get(
            url, params=params, timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
        return data.get("showers", [])

    async def get_live(self, device_id: str) -> dict[str, Any]:
        """Retourne les mesures temps réel pour un appareil."""
        url = f"{self._base_url}/devices/{device_id}/live"
        async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def test_connection(self) -> bool:
        """Vérifie que le gateway est joignable."""
        try:
            await self.get_devices()
            return True
        except Exception:  # noqa: BLE001
            return False

    # ------------------------------------------------------------------
    # WebSocket live feed
    # ------------------------------------------------------------------

    def register_live_callback(self, callback: Callable[[dict], None]) -> None:
        """Enregistre une callback appelée à chaque message WebSocket."""
        self._live_callbacks.append(callback)

    def start_websocket(self) -> None:
        """Démarre la tâche WebSocket en arrière-plan."""
        if self._ws_task is None or self._ws_task.done():
            self._ws_task = asyncio.create_task(self._ws_listener())

    def stop_websocket(self) -> None:
        """Arrête la tâche WebSocket."""
        if self._ws_task and not self._ws_task.done():
            self._ws_task.cancel()
            self._ws_task = None

    async def _ws_listener(self) -> None:
        """Écoute le WebSocket /ws/live et appelle les callbacks à chaque message."""
        backoff = 5
        while True:
            try:
                _LOGGER.debug("Connexion WebSocket Hydrao: %s", self._ws_url)
                async with self._session.ws_connect(
                    self._ws_url,
                    heartbeat=30,
                    timeout=aiohttp.ClientWSTimeout(ws_receive=60),
                ) as ws:
                    backoff = 5  # reset on success
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            try:
                                payload = json.loads(msg.data)
                                for cb in self._live_callbacks:
                                    cb(payload)
                            except json.JSONDecodeError:
                                _LOGGER.warning("Message WebSocket invalide: %s", msg.data)
                        elif msg.type in (
                            aiohttp.WSMsgType.CLOSED,
                            aiohttp.WSMsgType.ERROR,
                        ):
                            _LOGGER.warning("WebSocket Hydrao fermé/erreur, reconnexion...")
                            break
            except asyncio.CancelledError:
                _LOGGER.debug("WebSocket Hydrao arrêté")
                return
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning(
                    "Erreur WebSocket Hydrao (%s), nouvelle tentative dans %ds", err, backoff
                )
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)
