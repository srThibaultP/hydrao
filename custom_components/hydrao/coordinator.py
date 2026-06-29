"""Hydrao DataUpdateCoordinator — bridges HydraoDevice BLE callbacks to HA."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
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

    def __init__(
        self, hass: HomeAssistant, device: HydraoDevice, entry: ConfigEntry
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{device.address}",
        )
        self.device = device
        self._entry = entry
        self._was_available = False
        self.data: dict[str, Any] = device.as_dict()

        device.register_callback(self._on_device_update)

    @callback
    def _on_device_update(self, snapshot: dict[str, Any]) -> None:
        """Called by HydraoDevice every time data changes (live poll or history)."""
        self.async_set_updated_data(snapshot)

        # IQS log-when-unavailable: log once when connected, once when lost
        now_available = device_is_connected(snapshot)
        if now_available and not self._was_available:
            _LOGGER.info("[%s] Device connected and available", self.device.address)
        elif not now_available and self._was_available:
            _LOGGER.info("[%s] Device unavailable (shower ended / out of range)", self.device.address)
        self._was_available = now_available

        # Persist fw_version and hw_version so they survive HA restarts
        fw = snapshot.get("fw_version")
        hw = snapshot.get("hw_version")
        current_opts = self._entry.options
        if fw and (current_opts.get("fw_version") != fw or current_opts.get("hw_version") != hw):
            self.hass.config_entries.async_update_entry(
                self._entry,
                options={**current_opts, "fw_version": fw, "hw_version": hw},
            )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fallback — normally never called since we use push callbacks."""
        return self.device.as_dict()


def device_is_connected(snapshot: dict[str, Any]) -> bool:
    """True when the device is actively showering (BLE connected)."""
    return bool(snapshot.get("is_showering", False))
