"""Hydrao BLE integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.components.bluetooth import (
    async_ble_device_from_address,
    async_last_service_info,
    async_register_callback,
    BluetoothChange,
    BluetoothCallbackMatcher,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback

from .ble_client import HydraoDevice
from .const import DOMAIN
from .coordinator import HydraoCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Set up a Hydrao device from a config entry.

    The showerhead only advertises over BLE while a shower is running, so it
    is normal for it to be unreachable most of the time. We never block setup
    on it being present: entities are created right away in an "unavailable"
    state, and a Bluetooth callback resolves/reconnects the device as soon as
    it shows up again (i.e. next time someone showers).
    """
    address: str = entry.data["address"]
    name: str = entry.data.get("name", address)

    device = HydraoDevice(ble_device=None, rssi=0)
    device.address = address
    device.name = name

    coordinator = HydraoCoordinator(hass, device)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # If the device is already visible (mid-shower at HA startup), start now.
    ble_device = async_ble_device_from_address(hass, address, connectable=True)
    if ble_device is not None:
        last_info = async_last_service_info(hass, address, connectable=True)
        device.update_ble_device(ble_device, last_info.rssi if last_info else 0)
        device.start()

    # Otherwise, wait for the next BLE advertisement (next shower) to connect.
    @callback
    def _on_bluetooth_event(
        service_info, change: BluetoothChange
    ) -> None:
        device.update_ble_device(service_info.device, service_info.rssi or 0)
        device.start()  # no-op if already running

    unregister = async_register_callback(
        hass,
        _on_bluetooth_event,
        BluetoothCallbackMatcher(address=address, connectable=True),
        # MAC-based match: fires on every advertisement from this device
    )

    entry.async_on_unload(unregister)
    entry.async_on_unload(device.stop)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Hydrao config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: HydraoCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        coordinator.device.stop()
    return unload_ok
