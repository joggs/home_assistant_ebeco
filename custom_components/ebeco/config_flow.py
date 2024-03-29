"""Config flow for Ebeco device."""
import logging
from typing import Any, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_DEVICE_ID, CONF_DEVICES, CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, MAIN_SENSOR
from .data_handler import EbecoApi

_LOGGER = logging.getLogger(__name__)

EBECO_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class EbecoFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config Ebeco API connection."""

    VERSION = 1
    DOMAIN = DOMAIN
    data: Optional[dict[str, Any]]

    async def async_step_user(self, user_input=None):
        """Get configuration from the user."""
        errors = {}
        if user_input:
            email = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]

            try:
                data = await EbecoApi(
                    email, password, async_get_clientsession(self.hass)
                ).fetch_user_devices()
            except Exception:
                _LOGGER.warning(
                    "Unable to connect/authenticate with Ebeco API", exc_info=1
                )
                errors["base"] = "cannot_connect"
            else:
                self.data = {
                    CONF_EMAIL: email,
                    CONF_PASSWORD: password,
                    CONF_DEVICES: data,
                }
                return await self.async_step_pick_device()

        return self.async_show_form(
            step_id="user",
            data_schema=EBECO_SCHEMA,
            errors=errors,
        )

    async def async_step_pick_device(self, user_input=None):
        """Get device selection from the user."""
        errors = {}
        if user_input is not None:
            device = user_input[CONF_DEVICE_ID]
            main_sensor = user_input[MAIN_SENSOR]

            await self.async_set_unique_id(device)
            self._abort_if_unique_id_configured()

            device_data = next(
                (e for e in self.data[CONF_DEVICES] if str(e["id"]) == device),
                None,
            )
            data = {
                CONF_DEVICE_ID: device,
                MAIN_SENSOR: main_sensor,
                CONF_EMAIL: self.data[CONF_EMAIL],
                CONF_PASSWORD: self.data[CONF_PASSWORD],
            }
            return self.async_create_entry(
                title=device_data["displayName"],
                data=data,
            )

        devices = {
            str(device["id"]): device["displayName"]
            for device in self.data[CONF_DEVICES]
        }
        schema = vol.Schema(
            {
                vol.Required(CONF_DEVICE_ID): vol.In(devices),
                vol.Optional(MAIN_SENSOR, default="floor"): vol.In(["floor", "room"]),
            }
        )

        return self.async_show_form(
            step_id="pick_device", data_schema=schema, errors=errors
        )
