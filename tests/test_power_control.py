"""Regression tests for opt-in EB-Therm 500 power control."""

import pytest
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, ATTR_TEMPERATURE
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError

from .conftest import entity_id
from .test_climate import _puts


@pytest.mark.parametrize("enabled,minimum,maximum", [(False, 5, 35), (True, 0, 100)])
async def test_power_control_limits(hass, config_entry, mock_api, no_sleep_ha, enabled, minimum, maximum):
    hass.config_entries.async_update_entry(config_entry, options={"power_control": enabled})
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    attrs = hass.states.get(entity_id(hass, "climate", "1118")).attributes
    assert attrs["min_temp"] == minimum
    assert attrs["max_temp"] == maximum
    assert attrs["target_temp_step"] == (5 if enabled else 1)
    assert attrs["power_control"] is enabled
    assert attrs["current_temperature"] == 22.1


@pytest.mark.parametrize("value", [0, 5, 50, 95, 100])
async def test_power_control_setpoint(hass, config_entry, mock_api, no_sleep_ha, value):
    hass.config_entries.async_update_entry(config_entry, options={"power_control": True})
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    eid = entity_id(hass, "climate", "1118")
    await hass.services.async_call(
        CLIMATE_DOMAIN, "set_temperature", {ATTR_ENTITY_ID: eid, ATTR_TEMPERATURE: value}, blocking=True
    )
    await hass.async_block_till_done()
    assert _puts(mock_api) == [{"id": "1118", "powerOn": True, "temperatureSet": float(value)}]
    assert hass.states.get(eid).attributes["target_power_percent"] == value


async def test_options_flow_toggle(hass, setup_integration, mock_api):
    entry = setup_integration
    for enabled, minimum, maximum in [(True, 0, 100), (False, 5, 35)]:
        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result["type"] is FlowResultType.FORM
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"power_control": enabled}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        await hass.async_block_till_done()
        assert entry.options["power_control"] is enabled
        attrs = hass.states.get(entity_id(hass, "climate", "1118")).attributes
        assert (attrs["min_temp"], attrs["max_temp"]) == (minimum, maximum)
        assert attrs["target_temp_step"] == (5 if enabled else 1)
    assert _puts(mock_api) == []


async def test_power_control_rejects_non_multiple_of_five(
    hass, config_entry, mock_api, no_sleep_ha
):
    hass.config_entries.async_update_entry(config_entry, options={"power_control": True})
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    eid = entity_id(hass, "climate", "1118")
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            "set_temperature",
            {ATTR_ENTITY_ID: eid, ATTR_TEMPERATURE: 53},
            blocking=True,
        )
    assert _puts(mock_api) == []
