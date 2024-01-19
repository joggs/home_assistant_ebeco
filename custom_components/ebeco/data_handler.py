"""Communicate with the Ebeco API."""

import asyncio
from collections import namedtuple
import datetime
from enum import Enum
import json
import logging

import aiohttp

API_URL = "https://ebecoconnect.com/api"
_LOGGER = logging.getLogger(__name__)


class RequestType(Enum):
    GET = 1
    PUT = 2
    POST = 3


class EbecoApi:
    """Ebeco data handler."""

    def __init__(self, username, password, websession) -> None:
        """Init ebeco data handler."""

        self._username = username
        self._password = password
        self.websession = websession
        self._access_token = None
        self._auth_header = None
        self._last_updated = datetime.datetime.utcnow() - datetime.timedelta(hours=2)
        self._timeout = 10

    async def fetch_user_devices(self):
        """Get user devices."""

        response = await self._request(
            API_URL + "/services/app/Devices/GetUserDevices/", RequestType.GET
        )

        if response is None:
            return

        json_data = await response.json()
        if json_data is None:
            return

        return json_data["result"]

    async def fetch_user_device(self, device_id):
        """Get a single device."""

        response = await self._request(
            API_URL + f"/services/app/Devices/GetUserDeviceById/?id={device_id}",
            RequestType.GET,
        )

        if response is None:
            return

        json_data = await response.json()
        if json_data is None:
            return

        return json_data["result"]

    async def set_room_target_temperature(self, json_data):
        await self._request(
            API_URL + "/services/app/Devices/UpdateUserDevice",
            RequestType.PUT,
            json_data=json_data,
        )

    async def set_powerstate(self, json_data):
        await self._request(
            API_URL + "/services/app/Devices/UpdateUserDevice",
            RequestType.PUT,
            json_data=json_data,
        )

    async def set_preset_mode(self, json_data):
        await self._request(
            API_URL + "/services/app/Devices/UpdateUserDevice",
            RequestType.PUT,
            json_data=json_data,
        )

    async def _getAccessToken(self, arg, max_retries: int = 6):
        for attempt in range(max_retries):
            response = await self.websession.post(
                f"{API_URL}/TokenAuth",
                headers={"Content-type": "application/json", "Abp.TenantId": "1"},
                json={
                    "userNameOrEmailAddress": self._username,
                    "password": self._password,
                },
            )

            if response.status != HTTPStatus.TOO_MANY_REQUESTS:
                break

            _LOGGER.info("Backing off")
            await asyncio.sleep(2**attempt)

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
            async with asyncio.timeout(self._timeout):
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
                if response.status != HTTPStatus.TOO_MANY_REQUESTS:
                    # No need to reset token if we're simply being rate limited
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
