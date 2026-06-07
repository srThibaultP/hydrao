"""Hydrao BLE integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.components.bluetooth import (
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
    async_ble_device_from_address,
    async_last_service_info,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .ble_client import HydraoDevice
from .const import DOMAIN
from .coordinator import HydraoCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a Hydrao device from a config entry."""
    address: str = entry.data["address"]
    name: str = entry.data.get("name", address)

    # Resolve the BLE device object from HA's Bluetooth subsystem
    ble_device = async_ble_device_from_address(hass, address, connectable=True)
    if ble_device is None:
        raise ConfigEntryNotReady(
            f"Hydrao device {address} not found — make sure it is in range"
        )

    # Grab RSSI from last advertisement if available
    rssi = 0
    last_info = async_last_service_info(hass, address, connectable=True)
    if last_info:
        rssi = last_info.rssi or 0

    device = HydraoDevice(ble_device, rssi=rssi)
    device.name = name

    coordinator = HydraoCoordinator(hass, device)

    # Start BLE connection loop in the background
    device.start()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(device.stop)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Hydrao config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: HydraoCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        coordinator.device.stop()
    return unload_ok
