"""Config flow for Hydrao — BLE discovery or manual MAC address entry."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.data_entry_flow import FlowResult

from .const import DEVICE_NAME_PREFIX, DOMAIN

_LOGGER = logging.getLogger(__name__)


class HydraoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """
    Config flow for Hydrao BLE devices.
    - Passive discovery: HA Bluetooth finds a HYDRAO_SHOWER* device → confirm dialog.
    - Manual: user types a MAC address.
    """

    VERSION = 1

    def __init__(self) -> None:
        self._discovered_address: str | None = None
        self._discovered_name: str | None = None

    # ── Passive Bluetooth discovery ───────────────────────────────────────────

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Called by HA when a matching BLE advertisement is seen."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        self._discovered_address = discovery_info.address
        self._discovered_name = discovery_info.name or discovery_info.address

        self.context["title_placeholders"] = {"name": self._discovered_name}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirmation dialog after passive discovery."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._discovered_name or self._discovered_address,
                data={"address": self._discovered_address, "name": self._discovered_name},
            )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": self._discovered_name},
        )

    # ── Manual entry ──────────────────────────────────────────────────────────

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """
        Shown when user clicks '+ Add integration'.
        Lists discovered devices not yet configured, or lets user type a MAC.
        """
        errors: dict[str, str] = {}

        # Collect already-configured addresses to exclude from suggestions
        configured = {
            entry.data["address"]
            for entry in self._async_current_entries()
            if "address" in entry.data
        }

        # Devices discovered by HA BLE scanner but not yet configured
        discovered = {
            info.address: info.name or info.address
            for info in async_discovered_service_info(self.hass, connectable=True)
            if info.name and info.name.startswith(DEVICE_NAME_PREFIX)
            and info.address not in configured
        }

        if user_input is not None:
            address = user_input.get("address", "").strip().upper()
            name = discovered.get(address, address)

            if not address:
                errors["address"] = "invalid_address"
            else:
                await self.async_set_unique_id(address)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=name,
                    data={"address": address, "name": name},
                )

        # Build schema: dropdown if devices found, else free text
        if discovered:
            schema = vol.Schema(
                {
                    vol.Required("address"): vol.In(
                        {addr: f"{name} ({addr})" for addr, name in discovered.items()}
                    )
                }
            )
        else:
            schema = vol.Schema({vol.Required("address"): str})

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "found": str(len(discovered)) if discovered else "0"
            },
        )
