"""Ebeco parent entity class."""

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class EbecoEntity(CoordinatorEntity):
    """Parent class for Ebeco Entities."""

    def __init__(self, instance, device_key, main_sensor) -> None:
        """Initialize common aspects of an Ebeco sensor."""
        super().__init__(instance["coordinator"])
        self.async_change = instance["async_change"]
        self.device_key = device_key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_key)},
            manufacturer="Ebeco",
            name=self._device["displayName"],
            suggested_area="Bathroom",
        )

    @property
    def building(self):
        """Which building this entity is installed in."""
        return self._device["building"]["name"]

    @property
    def _device(self):
        return self.coordinator.data
