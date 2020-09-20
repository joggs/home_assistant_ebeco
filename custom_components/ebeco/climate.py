"""Support for Ebeco wifi-enabled thermostats"""
import asyncio
import datetime
import json
import logging

import aiohttp
import ssl
import async_timeout
import voluptuous as vol

from homeassistant.components.climate import ClimateEntity, PLATFORM_SCHEMA
from homeassistant.components.climate.const import (
    SUPPORT_TARGET_TEMPERATURE,
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT,
    SUPPORT_PRESET_MODE,
    ATTR_PRESET_MODE,
    ATTR_PRESET_MODES,
)
from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
    ATTR_TEMPERATURE,
    PRECISION_WHOLE,
)

from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from collections import namedtuple
from enum import Enum

_LOGGER = logging.getLogger(__name__)

PRESET_MANUAL = "Manual"
PRESET_PROGRAM = "Program"
PRESET_TIMER = "Timer"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional("main_sensor", default="floor"): vol.In(["floor", "room"]),
    }
)


class RequestType(Enum):
    GET = 1
    PUT = 2
    POST = 3


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):

    """Set up the thermostat."""
    username = config[CONF_USERNAME]
    password = config[CONF_PASSWORD]
    main_sensor = config["main_sensor"]

    ebeco_data_handler = Ebeco(
        username, password, websession=async_get_clientsession(hass)
    )

    dev = []
    for device_data in await ebeco_data_handler.get_devices():
        dev.append(EbecoDevice(device_data, ebeco_data_handler, main_sensor))
    async_add_entities(dev)


class EbecoDevice(ClimateEntity):
    def __init__(self, device_data, ebeco_data_handler, main_sensor):
        """Initialize the thermostat."""
        self.main_sensor = main_sensor
        self._device_data = device_data
        self._ebeco_data_handler = ebeco_data_handler

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_TARGET_TEMPERATURE  # | SUPPORT_PRESET_MODE #To be implemented after getting some answers

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._device_data['id']}"

    @property
    def name(self):
        """Return the name of the device, if any."""
        return self._device_data["displayName"]

    @property
    def hvac_action(self):
        """Return hvac operation ie. heat, cool mode.
        Need to be one of HVAC_MODE_*.
        """
        if self._device_data["powerOn"]:
            return HVAC_MODE_HEAT
        return HVAC_MODE_OFF

    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode.
        Need to be one of HVAC_MODE_*.
        """
        if self._device_data["powerOn"]:
            return HVAC_MODE_HEAT
        return HVAC_MODE_OFF

    @property
    def icon(self):
        if self.hvac_mode == HVAC_MODE_HEAT:
            return "mdi:radiator"
        else:
            return "mdi:radiator-off"

    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes.
        Need to be a subset of HVAC_MODES.
        """
        return [HVAC_MODE_HEAT, HVAC_MODE_OFF]

    @property
    def temperature_unit(self):
        """Return the unit of measurement which this device uses."""
        return TEMP_CELSIUS

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return 5

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return 35

    @property
    def current_temperature(self):
        """Return the current temperature."""
        if self.main_sensor == "floor":
            return self._device_data["temperatureFloor"]
        else:
            return self._device_data["temperatureRoom"]

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._device_data["temperatureSet"]

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return PRECISION_WHOLE

    @property
    def device_state_attributes(self):
        """Return device specific state attributes."""
        res = {
            "current_temperature_floor": self._device_data["temperatureFloor"],
            "current_temperature_room": self._device_data["temperatureRoom"],
            "selected_program": self._device_data["selectedProgram"],
            "program_state": self._device_data["programState"],
            "relay_on": self._device_data["relayOn"],
            "main_temperature_sensor": self.main_sensor,
            "minutes_to_target": self._device_data["minutesToTarget"],
            "remote_input": self._device_data["remoteInput"],
            "has_error": self._device_data["hasError"],
            "error_message": self._device_data["errorMessage"],
            "todays_on_minutes": self._device_data["todaysOnMinutes"],
            "building": self._device_data["building"]["name"],
        }
        return res

    @property
    def preset_mode(self):
        """Return preset mode."""
        return self._device_data["selectedProgram"]

    @property
    def preset_modes(self):
        """Return valid preset modes."""
        return [PRESET_MANUAL, PRESET_PROGRAM, PRESET_TIMER]

    async def async_set_hvac_mode(self, hvac_mode):
        """Set hvac mode."""
        # self.hvac_mode = hvac_mode

        """Set hvac mode."""
        if hvac_mode == HVAC_MODE_HEAT:
            await self._ebeco_data_handler.set_powerstate(self._device_data["id"], True)
        #
        #  self._device_data["powerOn"] = True

        elif hvac_mode == HVAC_MODE_OFF:
            await self._ebeco_data_handler.set_powerstate(
                self._device_data["id"], False
            )
        # self._device_data["powerOn"] = False
        else:
            return
        await self._ebeco_data_handler.update(force_update=True)

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""

        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        await self._ebeco_data_handler.set_room_target_temperature(
            self._device_data["id"], temperature, True
        )
        await self._ebeco_data_handler.update(force_update=True)

    async def async_update(self):
        """Get the latest data."""

        for device in await self._ebeco_data_handler.get_devices():

            if device["id"] == self._device_data["id"]:

                self._device_data = device
                return

    # To be implemented after getting some answers
    async def async_set_preset_mode(self, preset_mode):
        """Set the hold mode."""
        await self._ebeco_data_handler.set_preset_mode(
            self._device_data["id"], preset_mode
        )


######


API_URL = "https://ebecoconnect.com/api"  # services/app/Devices


class Ebeco:
    """Ebeco data handler."""

    def __init__(self, username, password, websession):
        """Init ebeco data handler."""
        self._username = username
        self._password = password
        self.websession = websession
        self._access_token = None
        self.authHeader = None
        self._devices = []
        self._last_updated = datetime.datetime.utcnow() - datetime.timedelta(hours=2)
        self._timeout = 10

    async def get_devices(self):
        """Get devices."""

        await self.update()
        return self._devices

    # skicka inte med temp om stänger av
    async def update(self, force_update=False):
        """Update data."""

        now = datetime.datetime.utcnow()
        if (
            now - self._last_updated < datetime.timedelta(seconds=30)
            and not force_update
        ):
            return
        self._last_updated = now

        await self.fetch_user_devices()

    async def set_room_target_temperature(
        self, device_id, temperature, heating_enabled
    ):
        """Set target temperature"""

        json_data = {
            "id": device_id,
            "powerOn": heating_enabled,
            "temperatureSet": temperature,
        }
        await self._request(
            API_URL + "/services/app/Devices/UpdateUserDevice",
            RequestType.PUT,
            json_data=json_data,
        )

    async def set_powerstate(self, device_id, heating_enabled):

        json_data = {
            "id": device_id,
            "powerOn": heating_enabled,
        }
        await self._request(
            API_URL + "/services/app/Devices/UpdateUserDevice",
            RequestType.PUT,
            json_data=json_data,
        )

    async def fetch_user_devices(self):
        """Get user devices"""

        response = await self._request(
            API_URL + "/services/app/Devices/GetUserDevices/", RequestType.GET
        )

        if response is None:

            return
        json_data = await response.json()
        if json_data is None:
            return

        self._devices = json_data["result"]

    async def _getAccessToken(self, arg):
        response = await self.websession.post(
            f"{API_URL}/TokenAuth",
            headers={"Content-type": "application/json", "Abp.TenantId": "1"},
            json={
                "userNameOrEmailAddress": self._username,
                "password": self._password,
            },
        )

        responseString = await response.text()
        token_data = json.loads(
            responseString,
            object_hook=lambda d: namedtuple("X", d.keys(), rename=True)(*d.values()),
        )

        self._access_token = token_data.result.accessToken

        self._authHeader = {"Authorization": f"Bearer {self._access_token}"}

    async def _request(self, url, requesttype, json_data=None, retry=3):

        if self._access_token is None:

            await self._getAccessToken(self)
        try:
            with async_timeout.timeout(self._timeout):
                if json_data:

                    if requesttype == RequestType.GET:

                        response = await self.websession.get(
                            url, json=json_data, headers=self._authHeader
                        )
                    elif requesttype == RequestType.POST:

                        response = await self.websession.post(
                            url, json=json_data, headers=self._authHeader
                        )
                    else:

                        response = await self.websession.put(
                            url, json=json_data, headers=self._authHeader
                        )

                else:  # If no json_data

                    if requesttype == RequestType.GET:

                        response = await self.websession.get(
                            url, headers=self._authHeader
                        )
                    elif requesttype == RequestType.POST:

                        response = await self.websession.post(
                            url, headers=self._authHeader
                        )
                    else:

                        response = await self.websession.put(
                            url, headers=self._authHeader
                        )

            if response.status != 200:

                self._access_token = None
                if retry > 0:
                    await asyncio.sleep(1)
                    return await self._request(
                        url, requesttype, json_data, retry=retry - 1
                    )

                return None
        except aiohttp.ClientError as err:

            self._access_token = None
            if retry > 0:
                return await self._request(url, requesttype, json_data, retry=retry - 1)

            raise
        except asyncio.TimeoutError:

            self._access_token = None
            if retry > 0:
                return await self._request(url, requesttype, json_data, retry=retry - 1)

            raise
        return response
