"""Support for Ebeco wifi-enabled thermostats"""

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    CURRENT_HVAC_OFF,
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_TEMPERATURE,
)

from homeassistant.const import (
    TEMP_CELSIUS,
    ATTR_TEMPERATURE,
    PRECISION_WHOLE,
)

from .const import (
    DOMAIN as EBECO_DOMAIN,
    MAIN_SENSOR,
    PRESET_MANUAL,
    PRESET_TIMER,
    PRESET_WEEK,
    EbecoClimateActions,
)
from .entity import EbecoEntity


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Ebeco climate platform."""

    instance = hass.data[EBECO_DOMAIN][config_entry.entry_id]
    sensor = config_entry.data[MAIN_SENSOR]
    dev = []
    for device_data in instance["coordinator"].data:
        dev.append(EbecoClimateDevice(instance, device_data, sensor))
    async_add_entities(dev)


class EbecoClimateDevice(EbecoEntity, ClimateEntity):
    """Ebeco climate device."""

    def __init__(self, instance, device_data, main_sensor):
        """Initialize the thermostat."""
        super().__init__(instance, device_data["id"], main_sensor)
        self.main_sensor = main_sensor

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._device['id']}"

    @property
    def name(self):
        """Return the name of the device, if any."""
        return self._device["displayName"]

    @property
    def hvac_action(self):
        """Return hvac action ie. the thermostat relay state.
        Need to be one of CURRENT_HVAC_*.
        """
        if self.hvac_mode == HVAC_MODE_HEAT:
            if self._device["relayOn"]:
                return CURRENT_HVAC_HEAT
            return CURRENT_HVAC_IDLE
        else:
            return CURRENT_HVAC_OFF

    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode.
        Need to be one of HVAC_MODE_*.
        """
        if self._device["powerOn"]:
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
            return self._device["temperatureFloor"]
        else:
            return self._device["temperatureRoom"]

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._device["temperatureSet"]

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return PRECISION_WHOLE

    @property
    def todays_on_minutes(self):
        """Return the number of minutes it has been running today."""
        return self._device["todaysOnMinutes"]

    @property
    def installed_effect(self):
        """Return the installed effect in Watts."""
        return self._device["installedEffect"]

    @property
    def preset_mode(self):
        """Return preset mode."""
        return self._device["selectedProgram"]

    @property
    def preset_modes(self):
        """Return valid preset modes."""
        return [PRESET_MANUAL, PRESET_WEEK, PRESET_TIMER]

    async def async_set_hvac_mode(self, hvac_mode):
        """Set hvac mode."""
        if hvac_mode == HVAC_MODE_HEAT:
            await self.async_change(
                {
                    "id": self._device["id"],
                    "action": EbecoClimateActions.SET_POWERSTATE,
                    "state": True,
                }
            )
        elif hvac_mode == HVAC_MODE_OFF:
            await self.async_change(
                {
                    "id": self._device["id"],
                    "action": EbecoClimateActions.SET_POWERSTATE,
                    "state": False,
                }
            )
        else:
            return

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        await self.async_change(
            {
                "id": self._device["id"],
                "action": EbecoClimateActions.SET_ROOM_TARGET_TEMPERATURE,
                "temperature": temperature,
                "heating_enabled": True,
            }
        )

    async def async_set_preset_mode(self, preset_mode):
        await self.async_change(
            {
                "id": self._device["id"],
                "action": EbecoClimateActions.SET_PRESET_MODE,
                "mode": preset_mode,
            }
        )
