"""Hydrao BLE integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.components.bluetooth import (
    async_ble_device_from_address,
    async_last_service_info,
    async_register_callback,
    BluetoothChange,
    BluetoothCallbackMatcher,
    BluetoothScanningMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback

from .ble_client import HydraoDevice
from .const import DOMAIN
from .coordinator import HydraoCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

type HydraoConfigEntry = ConfigEntry[HydraoCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: HydraoConfigEntry) -> bool:
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

    # Restore persisted metadata so firmware/hw sensors show right away,
    # even before the next shower connects.
    opts = entry.options
    if opts.get("fw_version"):
        device.fw_version = opts["fw_version"]
    if opts.get("hw_version") is not None:
        device.hw_version = opts["hw_version"]

    coordinator = HydraoCoordinator(hass, device, entry)

    # IQS runtime-data: store coordinator on entry instead of hass.data
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # If the device is already visible (mid-shower at HA startup), start now.
    ble_device = async_ble_device_from_address(hass, address, connectable=True)
    if ble_device is not None:
        last_info = async_last_service_info(hass, address, connectable=True)
        device.update_ble_device(ble_device, last_info.rssi if last_info else 0)
        device.start()

    _unavailable_logged = False

    @callback
    def _on_bluetooth_event(
        service_info, change: BluetoothChange
    ) -> None:
        nonlocal _unavailable_logged
        device.update_ble_device(service_info.device, service_info.rssi or 0)
        if _unavailable_logged:
            _LOGGER.info("[%s] Device back in range", address)
            _unavailable_logged = False
        device.start()  # no-op if already running

    unregister = async_register_callback(
        hass,
        _on_bluetooth_event,
        BluetoothCallbackMatcher(address=address, connectable=True),
        BluetoothScanningMode.ACTIVE,
    )

    entry.async_on_unload(unregister)
    entry.async_on_unload(device.stop)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: HydraoConfigEntry) -> bool:
    """Unload a Hydrao config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
