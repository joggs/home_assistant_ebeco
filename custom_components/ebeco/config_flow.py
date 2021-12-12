"""Config flow for Ebeco device"""
import voluptuous as vol
import logging

from homeassistant import config_entries
from homeassistant.const import CONF_DEVICE, CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import MAIN_SENSOR, DOMAIN
from .data_handler import Ebeco

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

    async def async_step_user(self, user_input=None):
        """Get configuration from the user."""
        errors = {}
        if user_input:
            email = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]

            try:
                data = await Ebeco(
                    email, password, async_get_clientsession(self.hass)
                ).fetch_user_devices()
            except Exception:
                errors["base"] = "cannot_connect"
            else:
                user_input["devices"] = data
                self.init_data = user_input
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
            device = user_input[CONF_DEVICE]
            main_sensor = user_input[MAIN_SENSOR]

            await self.async_set_unique_id(device)
            self._abort_if_unique_id_configured()

            device_data = next(
                (e for e in self.init_data["devices"] if str(e["id"]) == device), None
            )
            data = {
                CONF_DEVICE: device,
                MAIN_SENSOR: main_sensor,
                CONF_EMAIL: self.init_data[CONF_EMAIL],
                CONF_PASSWORD: self.init_data[CONF_PASSWORD],
            }
            return self.async_create_entry(
                title=device_data["displayName"],
                data=data,
            )

        devices = {
            str(device["id"]): device["displayName"]
            for device in self.init_data["devices"]
        }
        schema = vol.Schema(
            {
                vol.Required(CONF_DEVICE): vol.In(devices),
                vol.Optional(MAIN_SENSOR, default="floor"): vol.In(["floor", "room"]),
            }
        )

        return self.async_show_form(
            step_id="pick_device", data_schema=schema, errors=errors
        )
