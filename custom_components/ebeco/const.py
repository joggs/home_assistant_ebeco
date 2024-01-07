"""Constants used by the Ebeco integration."""

from enum import StrEnum

DOMAIN = "ebeco"
MAIN_SENSOR = "main_sensor"
REFRESH_INTERVAL_MINUTES = 1
PRESET_MANUAL = "Manual"  # Enable Manual mode on the thermostat
PRESET_WEEK = "Home"  # Enable The Week program on the thermostat, defined in the phone app or thermostat menu. Misleading value "home" in api instead of "week"
PRESET_TIMER = "Timer"  # Enable the timer on the thermostat, defined in the phone app or thermostat menu


class EbecoClimateActions(StrEnum):
    """List of available actions for the climate platform."""

    SET_ROOM_TARGET_TEMPERATURE = "set_room_target_temperature"
    SET_POWERSTATE = "set_powerstate"
    SET_PRESET_MODE = "set_preset_mode"
