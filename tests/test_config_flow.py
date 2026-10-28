"""The two-step config flow: credentials, then thermostat + sensor choice."""

from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType

from .conftest import TOKEN_URL


async def test_full_flow_creates_entry(hass, mock_api, no_sleep_ha):
    result = await hass.config_entries.flow.async_init(
        "ebeco", context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"email": "user@example.com", "password": "secret"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "pick_device"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"device_id": "1118", "main_sensor": "room"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Uterum"
    assert result["data"] == {
        "device_id": "1118",
        "main_sensor": "room",
        "email": "user@example.com",
        "password": "secret",
    }
    assert result["result"].unique_id == "1118"


async def test_bad_credentials_show_cannot_connect(hass, aioclient_mock, no_sleep_ha):
    aioclient_mock.post(TOKEN_URL, status=500, json={"error": {"message": "Invalid"}})

    result = await hass.config_entries.flow.async_init(
        "ebeco", context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"email": "user@example.com", "password": "wrong"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_same_thermostat_twice_aborts(hass, config_entry, mock_api, no_sleep_ha):
    result = await hass.config_entries.flow.async_init(
        "ebeco", context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"email": "user@example.com", "password": "secret"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"device_id": "1118", "main_sensor": "floor"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
