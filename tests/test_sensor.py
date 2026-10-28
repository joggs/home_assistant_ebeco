"""The six sensor entities created for a thermostat."""

from .conftest import ALL_ENTITIES, entity_id, register_api


async def test_sensor_values(hass, setup_integration):
    def state(domain, unique_id):
        return hass.states.get(entity_id(hass, domain, unique_id))

    relay = state("sensor", "1118-relay")  # see ALL_ENTITIES in conftest
    assert relay.state == "off"
    assert relay.attributes["device_class"] == "heat"

    power = state("sensor", "1118-power")
    assert power.state == "0"  # relay off -> no power drawn
    assert power.attributes["unit_of_measurement"] == "W"

    installed = state("sensor", "1118-installed-power")
    assert installed.state == "2200"

    energy = state("sensor", "1118-energy")
    assert energy.state == "4.69"  # 128 min * 2.2 kW / 60
    assert energy.attributes["unit_of_measurement"] == "kWh"
    assert energy.attributes["state_class"] == "total_increasing"

    floor = state("sensor", "1118-temperature-Floor")
    assert floor.state == "22.1"
    assert floor.attributes["unit_of_measurement"] == "°C"
    assert floor.attributes["friendly_name"] == "Uterum Floor Temperature"

    room = state("sensor", "1118-temperature-Room")
    assert room.state == "20.8"


async def test_power_follows_relay(hass, config_entry, mock_api, device_data, no_sleep_ha):
    device_data.update({"relayOn": True, "todaysOnMinutes": 60})
    register_api(mock_api, device_data)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(entity_id(hass, "sensor", "1118-relay")).state == "on"
    assert hass.states.get(entity_id(hass, "sensor", "1118-power")).state == "2200"
    assert hass.states.get(entity_id(hass, "sensor", "1118-energy")).state == "2.2"


async def test_temperature_without_decimals_field(
    hass, config_entry, mock_api, device_data, no_sleep_ha
):
    """Older API answers only carry the whole-degree fields."""
    del device_data["temperatureFloorDecimals"]
    del device_data["temperatureRoomDecimals"]
    register_api(mock_api, device_data)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(entity_id(hass, "sensor", "1118-temperature-Floor")).state == "22.0"
    assert hass.states.get(entity_id(hass, "climate", "1118")).attributes[
        "current_temperature"
    ] == 22.0


async def test_all_entities_belong_to_one_device(hass, setup_integration):
    from homeassistant.helpers import device_registry as dr, entity_registry as er

    entries = er.async_entries_for_config_entry(
        er.async_get(hass), setup_integration.entry_id
    )
    assert len(entries) == len(ALL_ENTITIES) == 7
    device_ids = {e.device_id for e in entries}
    assert len(device_ids) == 1

    device = dr.async_get(hass).async_get(device_ids.pop())
    assert device.manufacturer == "Ebeco"
    assert device.name == "Uterum"
    assert ("ebeco", 1118) in device.identifiers
