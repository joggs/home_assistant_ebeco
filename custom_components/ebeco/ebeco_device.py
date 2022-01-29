"""Wrap a single Ebeco device and the API to communicate with it"""

import logging

from .data_handler import EbecoApi

from .const import EbecoClimateActions

_LOGGER = logging.getLogger(__name__)


class EbecoDevice:
    """Wrap methods for a single Ebeco device."""

    def __init__(self, device_id, ebeco_data_handler: EbecoApi):
        self._device_id = device_id
        self._device = {}
        self._ebeco_data_handler = ebeco_data_handler

    async def get_device(self):
        """Get device."""

        return self._device

    async def async_get(self):
        """Get updated data for device."""
        data = await self._ebeco_data_handler.fetch_user_device(self._device_id)
        self._device = data
        return data

    async def async_change(self, changes) -> bool:
        """Apply requested changes"""
        _LOGGER.debug("Going to apply changes %s", changes)
        action = changes["action"]

        # The time between the API receiving the request and the device apply
        # the changes seems to take a bit longer time than we want, and the
        # coordinator has time to reset back to the previous value. So instead
        # we fake the correct changes being applied and wait for the next
        # scheduled refresh to take place
        try:
            if action == EbecoClimateActions.SET_POWERSTATE:
                await self.set_powerstate(changes["state"])
            elif action == EbecoClimateActions.SET_ROOM_TARGET_TEMPERATURE:
                await self.set_room_target_temperature(changes["temperature"], True)
            elif action == EbecoClimateActions.SET_PRESET_MODE:
                await self.set_preset_mode(changes["mode"])
            else:
                _LOGGER.error("Attempted to apply unsupported change %s", action)
                return False
        except Exception:
            _LOGGER.exception("Unable to update Ebeco thermostat")
            return False

        return True

    async def set_room_target_temperature(self, temperature, heating_enabled):
        """Set target temperature for room."""

        json_data = {
            "id": self._device_id,
            "powerOn": heating_enabled,
            "temperatureSet": temperature,
        }

        await self._ebeco_data_handler.set_room_target_temperature(json_data)

        self._device["powerOn"] = heating_enabled
        self._device["temperatureSet"] = temperature

    async def set_powerstate(self, heating_enabled):
        """Set power state."""
        json_data = {
            "id": self._device_id,
            "powerOn": heating_enabled,
        }
        await self._ebeco_data_handler.set_powerstate(json_data)
        self._device["powerOn"] = heating_enabled

    async def set_preset_mode(self, preset_mode):
        """Set preset mode."""
        json_data = {
            "id": self._device_id,
            "selectedProgram": preset_mode,
        }
        await self._ebeco_data_handler.set_preset_mode(json_data)
        self._device["selectedProgram"] = preset_mode
