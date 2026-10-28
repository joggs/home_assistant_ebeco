"""The climate entity: attributes and the three write actions."""

from homeassistant.components.climate import (
    ATTR_HVAC_ACTION,
    ATTR_PRESET_MODE,
    DOMAIN as CLIMATE_DOMAIN,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_PRESET_MODE,
    SERVICE_SET_TEMPERATURE,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_ENTITY_ID, ATTR_TEMPERATURE

from .conftest import TOKEN_URL, UPDATE_URL, entity_id, register_api


def _puts(mock_api):
    return [d for m, u, d, h in mock_api.mock_calls if m == "PUT" and str(u) == UPDATE_URL]


async def test_climate_attributes(hass, setup_integration):
    state = hass.states.get(entity_id(hass, "climate", "1118"))

    assert state.state == HVACMode.HEAT
    attrs = state.attributes
    assert attrs["friendly_name"] == "Uterum"
    assert attrs["current_temperature"] == 22.1  # floor sensor, decimals
    assert attrs["temperature"] == 21.0
    assert attrs["min_temp"] == 5
    assert attrs["max_temp"] == 35
    assert attrs["target_temp_step"] == 1
    assert attrs[ATTR_HVAC_ACTION] == HVACAction.IDLE
    assert attrs["hvac_modes"] == [HVACMode.HEAT, HVACMode.OFF]
    assert attrs[ATTR_PRESET_MODE] == "Manual"
    assert attrs["preset_modes"] == ["Manual", "Home", "Timer"]


async def test_climate_uses_room_sensor_when_configured(
    hass, config_entry, mock_api, no_sleep_ha
):
    hass.config_entries.async_update_entry(
        config_entry, data={**config_entry.data, "main_sensor": "room"}
    )
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(entity_id(hass, "climate", "1118"))
    assert state.attributes["current_temperature"] == 20.8


async def test_climate_reports_heating_and_off(hass, config_entry, mock_api, device_data, no_sleep_ha):
    device_data.update({"relayOn": True})
    register_api(mock_api, device_data)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(entity_id(hass, "climate", "1118"))
    assert state.attributes[ATTR_HVAC_ACTION] == HVACAction.HEATING
    assert state.attributes["icon"] == "mdi:radiator"


async def test_set_temperature(hass, setup_integration, mock_api):
    eid = entity_id(hass, "climate", "1118")
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: eid, ATTR_TEMPERATURE: 23},
        blocking=True,
    )
    await hass.async_block_till_done()

    # The id is sent as the string from the config entry; the API accepts it.
    assert _puts(mock_api) == [{"id": "1118", "powerOn": True, "temperatureSet": 23.0}]
    # The change is shown immediately, without waiting for the next poll
    assert hass.states.get(eid).attributes["temperature"] == 23


async def test_set_hvac_mode_off_and_on(hass, setup_integration, mock_api):
    eid = entity_id(hass, "climate", "1118")
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: eid, "hvac_mode": HVACMode.OFF},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert _puts(mock_api) == [{"id": "1118", "powerOn": False}]
    state = hass.states.get(eid)
    assert state.state == HVACMode.OFF
    assert state.attributes[ATTR_HVAC_ACTION] == HVACAction.OFF
    assert state.attributes["icon"] == "mdi:radiator-off"

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: eid, "hvac_mode": HVACMode.HEAT},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert _puts(mock_api)[-1] == {"id": "1118", "powerOn": True}
    assert hass.states.get(eid).state == HVACMode.HEAT


async def test_set_preset_mode(hass, setup_integration, mock_api):
    eid = entity_id(hass, "climate", "1118")
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: eid, ATTR_PRESET_MODE: "Home"},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert _puts(mock_api) == [{"id": "1118", "selectedProgram": "Home"}]
    assert hass.states.get(eid).attributes[ATTR_PRESET_MODE] == "Home"


async def test_write_failure_is_logged_and_state_kept(
    hass, setup_integration, mock_api, caplog
):
    mock_api.clear_requests()
    mock_api.post(TOKEN_URL, json={"result": {"accessToken": "tok"}})
    mock_api.put(UPDATE_URL, status=500, json={})

    eid = entity_id(hass, "climate", "1118")
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: eid, ATTR_TEMPERATURE: 23},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert "Unable to update Ebeco thermostat" in caplog.text
    assert "HTTP 500" in caplog.text
    assert hass.states.get(eid).attributes["temperature"] == 21.0
