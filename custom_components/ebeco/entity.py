"""Ebeco parent entity class."""

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class EbecoEntity(CoordinatorEntity):
    """Parent class for Ebeco Entities."""

    def __init__(self, instance, device_key, main_sensor):
        """Initialize common aspects of an Ebeco sensor."""
        super().__init__(instance["coordinator"])
        self.async_change = instance["async_change"]
        self.device_key = device_key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_key)},
            manufacturer="Ebeco",
            main_temperature_sensor=main_sensor,
            name=self._device["displayName"],
            building=self._device["building"]["name"],
            suggested_area="Bathroom",
        )

    @property
    def _device(self):
        return self.coordinator.data