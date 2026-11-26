"""Upgrading from a release that did not have the power-control option.

A config entry created by 0.6.14 or earlier has no options at all. After the
upgrade it must behave exactly as before: the same entities, the 5-35 °C range
with whole-degree setpoints, and nothing stored or sent on its own.
"""

import json

import pytest
from homeassistant.components.climate import (
    DOMAIN as CLIMATE_DOMAIN,
    SERVICE_SET_TEMPERATURE,
)
from homeassistant.const import ATTR_ENTITY_ID, ATTR_TEMPERATURE, STATE_UNAVAILABLE
from homeassistant.exceptions import HomeAssistantError

from .conftest import ALL_ENTITIES, REPO_ROOT, entity_id
from .test_climate import _puts


async def test_entry_without_options_is_unchanged(hass, setup_integration, mock_api):
    entry = setup_integration
    assert dict(entry.options) == {}  # what releases before the option stored

    for domain, unique_id in ALL_ENTITIES:
        state = hass.states.get(entity_id(hass, domain, unique_id))
        assert state is not None, (domain, unique_id)
        assert state.state != STATE_UNAVAILABLE, (domain, unique_id)

    attrs = hass.states.get(entity_id(hass, "climate", "1118")).attributes
    assert (attrs["min_temp"], attrs["max_temp"]) == (5, 35)
    assert attrs["target_temp_step"] == 1
    assert attrs["power_control"] is False
    assert "target_power_percent" not in attrs

    # Setting up must not turn the option on or write to the thermostat
    assert dict(entry.options) == {}
    assert _puts(mock_api) == []


async def test_entry_without_options_keeps_degree_setpoints(
    hass, setup_integration, mock_api
):
    eid = entity_id(hass, "climate", "1118")

    # 22 is not a multiple of five: the power-control step must not apply here
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: eid, ATTR_TEMPERATURE: 22},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert _puts(mock_api) == [{"id": "1118", "powerOn": True, "temperatureSet": 22.0}]

    # 50 is a valid power level but not a temperature: still refused, not sent
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {ATTR_ENTITY_ID: eid, ATTR_TEMPERATURE: 50},
            blocking=True,
        )
    assert len(_puts(mock_api)) == 1


def test_hacs_minimum_covers_the_options_flow():
    """config_flow.py uses OptionsFlowWithReload, which Home Assistant has from
    2025.8.0. On an older core the module cannot be imported, so HACS must not
    offer this release there."""
    minimum = json.loads((REPO_ROOT / "hacs.json").read_text())["homeassistant"]
    assert tuple(int(part) for part in minimum.split(".")) >= (2025, 8, 0)
