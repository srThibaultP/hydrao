"""Diagnostics support for Hydrao."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .coordinator import HydraoCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a Hydrao config entry."""
    coordinator: HydraoCoordinator = entry.runtime_data
    device = coordinator.device
    data = coordinator.data or {}

    return {
        "entry": {
            "address": entry.data.get("address"),
            "name": entry.data.get("name"),
            "options": dict(entry.options),
        },
        "device": {
            "address": device.address,
            "name": device.name,
            "uuid": device.uuid,
            "hw_version": device.hw_version,
            "fw_version": device.fw_version,
            "calibration": device.calibration,
            "rssi": device.rssi,
            "ble_connected": device.ble_device is not None,
        },
        "live": {
            "is_showering": data.get("is_showering"),
            "live_volume": data.get("live_volume"),
            "live_flow": data.get("live_flow"),
            "live_temperature": data.get("live_temperature"),
            "live_duration": data.get("live_duration"),
        },
        "last_shower": data.get("last_shower"),
    }
