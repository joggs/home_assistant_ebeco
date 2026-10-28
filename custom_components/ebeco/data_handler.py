"""Communicate with the Ebeco API."""

import asyncio
from enum import Enum
from http import HTTPStatus
import logging

import aiohttp

API_URL = "https://ebecoconnect.com/api"
_LOGGER = logging.getLogger(__name__)


class RequestType(Enum):
    GET = 1
    PUT = 2
    POST = 3


class EbecoApiError(Exception):
    """The Ebeco API returned an unusable response."""


class EbecoAuthError(EbecoApiError):
    """Authentication against the Ebeco API failed."""


class EbecoApi:
    """Ebeco data handler."""

    def __init__(self, username, password, websession) -> None:
        """Init ebeco data handler."""

        self._username = username
        self._password = password
        self.websession = websession
        self._access_token = None
        self._auth_header = None
        self._timeout = 10

    async def fetch_user_devices(self):
        """Get user devices."""

        response = await self._request(
            API_URL + "/services/app/Devices/GetUserDevices/", RequestType.GET
        )
        return self._result(response, "GetUserDevices")

    async def fetch_user_device(self, device_id):
        """Get a single device."""

        response = await self._request(
            API_URL + f"/services/app/Devices/GetUserDeviceById/?id={device_id}",
            RequestType.GET,
        )
        return self._result(response, f"GetUserDeviceById(id={device_id})")

    @staticmethod
    def _result(json_data, what):
        """Return the "result" element of an API response, or raise."""
        if not isinstance(json_data, dict) or json_data.get("result") is None:
            raise EbecoApiError(f"Empty response from Ebeco API ({what})")
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

    async def _get_access_token(self, max_retries: int = 6):
        """Log in and store the bearer token."""
        for attempt in range(max_retries):
            async with asyncio.timeout(self._timeout):
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

        if response.status != HTTPStatus.OK:
            raise EbecoAuthError(f"Login failed with HTTP {response.status}")

        try:
            token_data = await response.json(content_type=None)
            access_token = token_data["result"]["accessToken"]
        except (ValueError, KeyError, TypeError) as err:
            raise EbecoAuthError(
                "Login response from Ebeco API did not contain a token"
            ) from err

        self._access_token = access_token
        self._auth_header = {"Authorization": f"Bearer {self._access_token}"}

    async def _request(self, url, requesttype, json_data=None, retries=3):
        """Make an authenticated request and return the decoded JSON body.

        Retries transient failures (5xx, connection errors, timeouts) a few
        times, then raises so the caller never gets None back. Ebeco allows
        10 requests per 10 s and 30 per 60 s per IP, so on 429 we stop at
        once and leave it to the next scheduled poll.
        """
        attempt = 0
        while True:
            try:
                if self._access_token is None:
                    await self._get_access_token()
                async with asyncio.timeout(self._timeout):
                    response = await self._send(url, requesttype, json_data)
                    if response.status == HTTPStatus.OK:
                        return await response.json(content_type=None)
                if response.status == HTTPStatus.TOO_MANY_REQUESTS:
                    raise EbecoApiError(f"HTTP 429 Too Many Requests from {url}")
                if response.status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
                    # Token expired or revoked: log in again on the next attempt
                    self._access_token = None
                error = EbecoApiError(f"HTTP {response.status} from {url}")
            except (aiohttp.ClientError, TimeoutError) as err:
                error = err

            if attempt >= retries:
                raise error
            attempt += 1
            _LOGGER.debug(
                "Ebeco API request failed (%s: %s), retry %s of %s",
                type(error).__name__,
                error,
                attempt,
                retries,
            )
            await asyncio.sleep(1)

    async def _send(self, url, requesttype, json_data):
        """Send one HTTP request with the current auth header."""
        if requesttype == RequestType.GET:
            method = self.websession.get
        elif requesttype == RequestType.POST:
            method = self.websession.post
        else:
            method = self.websession.put
        kwargs = {"headers": self._auth_header}
        if json_data:
            kwargs["json"] = json_data
        return await method(url, **kwargs)
