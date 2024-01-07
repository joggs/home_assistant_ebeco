"""Ebeco thermostat integration."""

from datetime import timedelta
import logging

from homeassistant.const import CONF_DEVICE_ID, CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, REFRESH_INTERVAL_MINUTES
from .data_handler import EbecoApi
from .ebeco_device import EbecoDevice

PLATFORMS = [
    Platform.CLIMATE,
    Platform.SENSOR,
]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry):
    """Set up the thermostat."""
    username = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]
    device_id = entry.data[CONF_DEVICE_ID]

    device = EbecoDevice(
        device_id,
        EbecoApi(username, password, websession=async_get_clientsession(hass)),
    )

    async def async_get():
        _LOGGER.debug("Attempting to fetch new data from Ebeco API")
        try:
            data = await device.async_get()
            _LOGGER.debug("Received data: %s", data)
            return data
        except Exception as err:
            raise UpdateFailed(err) from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Ebeco",
        update_method=async_get,
        update_interval=timedelta(minutes=REFRESH_INTERVAL_MINUTES),
    )

    async def async_change(change):
        try:
            if await device.async_change(change):
                data = await device.get_device()
                coordinator.async_set_updated_data(data)
        except Exception:
            _LOGGER.exception("Failed to apply changes to thermostat")
            return False

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "async_change": async_change,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass, entry):
    """Unload Ebeco Config."""
    _LOGGER.info("Unloading Ebeco component")
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
