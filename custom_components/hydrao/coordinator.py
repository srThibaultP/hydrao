"""Hydrao DataUpdateCoordinator — bridges HydraoDevice BLE callbacks to HA."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .ble_client import HydraoDevice

_LOGGER = logging.getLogger(__name__)


class HydraoCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """
    Coordinator for one Hydrao BLE device.
    Data is pushed by the BLE client (no polling interval needed here).
    coordinator.data is the latest snapshot dict from HydraoDevice.as_dict().
    """

    def __init__(self, hass: HomeAssistant, device: HydraoDevice) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{device.address}",
            # No update_interval: updates are pushed from BLE callbacks
        )
        self.device = device
        self.data: dict[str, Any] = device.as_dict()

        # Register ourselves as a BLE callback
        device.register_callback(self._on_device_update)

    @callback
    def _on_device_update(self, snapshot: dict[str, Any]) -> None:
        """Called by HydraoDevice every time data changes (live poll or history)."""
        self.async_set_updated_data(snapshot)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fallback — normally never called since we use push callbacks."""
        return self.device.as_dict()
