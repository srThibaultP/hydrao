"""Config flow for Hydrao — passive BLE discovery only."""
from __future__ import annotations

from typing import Any

from homeassistant import config_entries
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN


class HydraoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Discovered automatically via BLE — no manual input needed."""

    VERSION = 1

    def __init__(self) -> None:
        self._address: str = ""
        self._name: str = ""

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Called by HA when a HYDRAO_SHOWER* advertisement is seen."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        self._address = discovery_info.address
        self._name = discovery_info.name or discovery_info.address
        self.context["title_placeholders"] = {"name": self._name}

        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Single confirm dialog — no fields to fill."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._name,
                data={"address": self._address, "name": self._name},
            )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": self._name},
        )

    # Pas de async_step_user → HA n'affiche pas ce composant dans la liste
    # "Ajouter une intégration" manuelle. Tout passe par la découverte BLE.
