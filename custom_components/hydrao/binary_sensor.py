"""Hydrao binary sensor — is a shower currently active."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HydraoCoordinator
from .sensor import _device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HydraoCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HydraoShoweringBinarySensor(coordinator)])


class HydraoShoweringBinarySensor(CoordinatorEntity[HydraoCoordinator], BinarySensorEntity):
    """True when the showerhead reports an active shower."""

    _attr_has_entity_name = True
    _attr_translation_key = "is_showering"
    _attr_name = "Douche en cours"
    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:shower"

    def __init__(self, coordinator: HydraoCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device.address}_is_showering"
        self._attr_device_info = _device_info(coordinator)

    @property
    def is_on(self) -> bool | None:
        if not self.coordinator.data:
            return None
        return bool(self.coordinator.data.get("is_showering", False))
