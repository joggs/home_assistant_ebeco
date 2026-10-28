"""Shared test fixtures.

test_data_handler.py loads the API client straight from its file, so those
tests also run without Home Assistant. The other test modules use the
pytest-homeassistant-custom-component plugin (hass, aioclient_mock, freezer).
"""

import asyncio
import importlib.util
import os
import pathlib

import pytest
from aiohttp import web

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# pytest-homeassistant-custom-component imports its own `custom_components`
# package before this file runs; add ours so Home Assistant can find `ebeco`.
import custom_components  # noqa: E402

if str(REPO_ROOT / "custom_components") not in custom_components.__path__:
    custom_components.__path__.insert(0, str(REPO_ROOT / "custom_components"))

# EBECO_DATA_HANDLER=/path/to/data_handler.py runs the suite against another
# copy of the client, e.g. an older release, to check what the tests catch.
MODULE_PATH = pathlib.Path(
    os.environ.get(
        "EBECO_DATA_HANDLER",
        REPO_ROOT / "custom_components" / "ebeco" / "data_handler.py",
    )
)


def load_data_handler():
    spec = importlib.util.spec_from_file_location("ebeco_data_handler", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def data_handler():
    return load_data_handler()


@pytest.fixture
def no_sleep(monkeypatch, data_handler):
    """Make the client's retry/back-off sleeps return immediately."""
    real_sleep = data_handler.asyncio.sleep
    slept = []

    async def fake_sleep(seconds):
        slept.append(seconds)
        await real_sleep(0)

    monkeypatch.setattr(data_handler.asyncio, "sleep", fake_sleep)
    return slept


class FakeEbeco:
    """A stand-in for ebecoconnect.com with programmable responses."""

    DEVICE = {
        "id": 1118,
        "displayName": "Uterum",
        "building": {"id": 1, "name": "Home"},
        "powerOn": True,
        "selectedProgram": "Manual",
        "programState": "Standby",
        "temperatureSet": 21.0,
        "temperatureFloor": 22.0,
        "temperatureRoom": 21.0,
        "temperatureFloorDecimals": 22.1,
        "temperatureRoomDecimals": 20.8,
        "relayOn": False,
        "minutesToTarget": 0,
        "remoteInput": False,
        "hasError": False,
        "errorMessage": None,
        "todaysOnMinutes": 128,
        "installedEffect": 2200,
        "sensorApplication": "Floor",
    }

    def __init__(self):
        self.real_sleep = asyncio.sleep  # captured before no_sleep patches it
        self.login_responses = []  # queue of (status, body) for /TokenAuth
        self.device_responses = []  # queue of (status, body | "hang")
        self.requests = []  # (method, path, auth header, json body)
        self.app = web.Application()
        self.app.router.add_post("/api/TokenAuth", self.token_auth)
        self.app.router.add_get(
            "/api/services/app/Devices/GetUserDeviceById/", self.get_device
        )
        self.app.router.add_get(
            "/api/services/app/Devices/GetUserDevices/", self.get_devices
        )
        self.app.router.add_put(
            "/api/services/app/Devices/UpdateUserDevice", self.update_device
        )

    async def _record(self, request):
        body = None
        if request.can_read_body:
            body = await request.json()
        self.requests.append(
            (request.method, request.path, request.headers.get("Authorization"), body)
        )

    def _pop(self, queue, default):
        return queue.pop(0) if queue else default

    async def token_auth(self, request):
        await self._record(request)
        status, body = self._pop(
            self.login_responses, (200, {"result": {"accessToken": "tok"}})
        )
        return web.json_response(body, status=status)

    async def get_device(self, request):
        await self._record(request)
        status, body = self._pop(self.device_responses, (200, {"result": self.DEVICE}))
        if body == "hang":
            await self.real_sleep(60)
        return web.json_response(body, status=status)

    async def get_devices(self, request):
        await self._record(request)
        return web.json_response({"result": [self.DEVICE]})

    async def update_device(self, request):
        await self._record(request)
        return web.json_response({"result": None})

    @property
    def login_count(self):
        return sum(1 for r in self.requests if r[1] == "/api/TokenAuth")

    @property
    def device_count(self):
        return sum(1 for r in self.requests if r[1].endswith("GetUserDeviceById/"))


@pytest.fixture
async def fake_ebeco(
    socket_enabled, aiohttp_server, aiohttp_client, data_handler, monkeypatch
):
    """Start the fake API (needs a real socket) and point the client at it."""
    fake = FakeEbeco()
    server = await aiohttp_server(fake.app)
    monkeypatch.setattr(data_handler, "API_URL", f"http://{server.host}:{server.port}/api")
    fake.session = await aiohttp_client(server)
    fake.websession = fake.session.session
    return fake


@pytest.fixture
def api(fake_ebeco, data_handler):
    client = data_handler.EbecoApi("user@example.com", "secret", fake_ebeco.websession)
    client._timeout = 0.3
    return client


# --- Home Assistant level fixtures -------------------------------------------

API_URL = "https://ebecoconnect.com/api"
TOKEN_URL = f"{API_URL}/TokenAuth"
DEVICE_URL = f"{API_URL}/services/app/Devices/GetUserDeviceById/?id=1118"
DEVICES_URL = f"{API_URL}/services/app/Devices/GetUserDevices/"
UPDATE_URL = f"{API_URL}/services/app/Devices/UpdateUserDevice"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let the hass fixture load custom_components/ebeco."""


@pytest.fixture
def device_data():
    return dict(FakeEbeco.DEVICE)


def register_api(aioclient_mock, device_data):
    """(Re)register the mocked endpoints; bodies are frozen at registration."""
    aioclient_mock.clear_requests()
    aioclient_mock.post(TOKEN_URL, json={"result": {"accessToken": "tok"}})
    aioclient_mock.get(DEVICE_URL, json={"result": device_data})
    aioclient_mock.get(DEVICES_URL, json={"result": [device_data]})
    aioclient_mock.put(UPDATE_URL, json={"result": None})
    return aioclient_mock


@pytest.fixture
def mock_api(aioclient_mock, device_data):
    """Mock the Ebeco cloud API behind Home Assistant's client session."""
    return register_api(aioclient_mock, device_data)


@pytest.fixture
def config_entry(hass):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain="ebeco",
        title="Uterum",
        unique_id="1118",
        data={
            "email": "user@example.com",
            "password": "secret",
            "device_id": "1118",
            "main_sensor": "floor",
        },
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
async def setup_integration(hass, config_entry, mock_api, no_sleep_ha):
    """Set up the Ebeco config entry against the mocked API."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


@pytest.fixture
def no_sleep_ha(monkeypatch):
    """Skip the client's 1 s retry sleeps; zero-length sleeps stay real."""
    import asyncio

    real_sleep = asyncio.sleep

    async def fast_sleep(seconds, *args, **kwargs):
        return await real_sleep(0 if seconds else seconds, *args, **kwargs)

    monkeypatch.setattr(asyncio, "sleep", fast_sleep)


def entity_id(hass, domain, unique_id):
    """Look up an Ebeco entity by unique id (entity ids depend on area naming)."""
    from homeassistant.helpers import entity_registry as er

    eid = er.async_get(hass).async_get_entity_id(domain, "ebeco", unique_id)
    assert eid, f"no {domain} entity with unique_id {unique_id}"
    return eid


# The relay is a BinarySensorEntity but is registered by the sensor platform,
# so it lives in the sensor domain (states "on"/"off"). Long-standing behaviour.
ALL_ENTITIES = [
    ("climate", "1118"),
    ("sensor", "1118-relay"),
    ("sensor", "1118-power"),
    ("sensor", "1118-installed-power"),
    ("sensor", "1118-energy"),
    ("sensor", "1118-temperature-Floor"),
    ("sensor", "1118-temperature-Room"),
]
