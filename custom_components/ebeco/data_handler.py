"""Communicate with the Ebeco API"""

from collections import namedtuple
from enum import Enum
import asyncio
import datetime
import json
import logging
import aiohttp
import async_timeout

from .const import EbecoClimateActions

API_URL = "https://ebecoconnect.com/api"
_LOGGER = logging.getLogger(__name__)


class RequestType(Enum):
    GET = 1
    PUT = 2
    POST = 3


class Ebeco:
    """Ebeco data handler."""

    def __init__(self, username, password, websession):
        """Init ebeco data handler."""

        self._username = username
        self._password = password
        self.websession = websession
        self._access_token = None
        self._auth_header = None
        self._devices = []
        self._last_updated = datetime.datetime.utcnow() - datetime.timedelta(hours=2)
        self._timeout = 10

    async def get_devices(self):
        """Get devices."""

        return self._devices

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
        for device in self._devices:
            if device["id"] == device_id:
                device["powerOn"] = heating_enabled
                device["temperatureSet"] = temperature

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
        for device in self._devices:
            if device["id"] == device_id:
                device["powerOn"] = heating_enabled

    async def set_preset_mode(self, device_id, preset_mode):
        json_data = {
            "id": device_id,
            "selectedProgram": preset_mode,
        }
        await self._request(
            API_URL + "/services/app/Devices/UpdateUserDevice",
            RequestType.PUT,
            json_data=json_data,
        )
        for device in self._devices:
            if device["id"] == device_id:
                device["selectedProgram"] = preset_mode

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
        return self._devices

    async def async_change(self, changes) -> bool:
        """Apply requested changes"""
        _LOGGER.debug("Going to apply changes %s", changes)
        device_id = changes["id"]
        action = changes["action"]

        # The time between the API receiving the request and the device apply
        # the changes seems to take a bit longer time than we want, and the
        # coordinator has time to reset back to the previous value. So instead
        # we fake the correct changes being applied and wait for the next
        # scheduled refresh to take place
        try:
            if action == EbecoClimateActions.SET_POWERSTATE:
                await self.set_powerstate(device_id, changes["state"])
            elif action == EbecoClimateActions.SET_ROOM_TARGET_TEMPERATURE:
                await self.set_room_target_temperature(
                    device_id, changes["temperature"], True
                )
            elif action == EbecoClimateActions.SET_PRESET_MODE:
                await self.set_preset_mode(device_id, changes["mode"])
            else:
                _LOGGER.error("Attempted to apply unsupported change %s", action)
                return False
        except Exception:
            _LOGGER.exception("Unable to update Ebeco thermostat")
            return False

        return True

    async def _getAccessToken(self, arg):
        response = await self.websession.post(
            f"{API_URL}/TokenAuth",
            headers={"Content-type": "application/json", "Abp.TenantId": "1"},
            json={
                "userNameOrEmailAddress": self._username,
                "password": self._password,
            },
        )

        response_string = await response.text()
        token_data = json.loads(
            response_string,
            object_hook=lambda d: namedtuple("X", d.keys(), rename=True)(*d.values()),
        )

        self._access_token = token_data.result.accessToken
        self._auth_header = {"Authorization": f"Bearer {self._access_token}"}

    async def _request(self, url, requesttype, json_data=None, retry=3):

        if self._access_token is None:
            await self._getAccessToken(self)
        try:
            with async_timeout.timeout(self._timeout):
                if json_data:
                    if requesttype == RequestType.GET:
                        response = await self.websession.get(
                            url, json=json_data, headers=self._auth_header
                        )
                    elif requesttype == RequestType.POST:
                        response = await self.websession.post(
                            url, json=json_data, headers=self._auth_header
                        )
                    else:
                        response = await self.websession.put(
                            url, json=json_data, headers=self._auth_header
                        )

                else:  # If no json_data
                    if requesttype == RequestType.GET:
                        response = await self.websession.get(
                            url, headers=self._auth_header
                        )
                    elif requesttype == RequestType.POST:
                        response = await self.websession.post(
                            url, headers=self._auth_header
                        )
                    else:
                        response = await self.websession.put(
                            url, headers=self._auth_header
                        )

            if response.status != 200:
                self._access_token = None
                if retry > 0:
                    await asyncio.sleep(1)
                    return await self._request(
                        url, requesttype, json_data, retry=retry - 1
                    )
                return None
        except aiohttp.ClientError:
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
