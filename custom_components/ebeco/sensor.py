"""Support power, energy and temperature measurement for Ebeco wifi-enabled thermostats."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
    StateType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfPower, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN as EBECO_DOMAIN, MAIN_SENSOR
from .entity import EbecoEntity


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    """Set up Ebeco sensor platform."""

    instance = hass.data[EBECO_DOMAIN][config_entry.entry_id]
    sensor = config_entry.data[MAIN_SENSOR]
    device_data = instance["coordinator"].data
    dev = []
    dev.append(EbecoRelaySensor(instance, device_data, sensor))
    dev.append(EbecoPowerSensor(instance, device_data, sensor))
    dev.append(EbecoInstalledPowerSensor(instance, device_data, sensor))
    dev.append(EbecoEnergySensor(instance, device_data, sensor))
    dev.append(EbecoTemperatureSensor(instance, device_data, "Floor"))
    dev.append(EbecoTemperatureSensor(instance, device_data, "Room"))
    async_add_entities(dev)


class EbecoRelaySensor(EbecoEntity, BinarySensorEntity):
    def __init__(self, instance, device_data, sensor) -> None:
        """Initialize the thermostat."""
        super().__init__(instance, device_data["id"], sensor)

    @property
    def device_class(self) -> str:
        """Return device class."""
        return BinarySensorDeviceClass.HEAT

    @property
    def entity_category(self) -> str:
        return EntityCategory.DIAGNOSTIC

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._device['id']}-relay"

    @property
    def name(self):
        """Return the name of the device, if any."""
        return f"{self._device['displayName']} Relay"

    @property
    def is_on(self) -> bool:
        """Return the state of the entity."""
        return self._device["relayOn"] is True


class EbecoPowerSensor(EbecoEntity, SensorEntity):
    def __init__(self, instance, device_data, sensor) -> None:
        """Initialize the thermostat."""
        super().__init__(instance, device_data["id"], sensor)
        self.main_sensor = MAIN_SENSOR

    @property
    def device_class(self) -> str:
        """Return device class."""
        return SensorDeviceClass.POWER

    @property
    def state_class(self) -> str:
        """Return the state class of this entity."""
        return SensorStateClass.MEASUREMENT

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._device['id']}-power"

    @property
    def name(self):
        """Return the name of the device, if any."""
        return f"{self._device['displayName']} Power"

    @property
    def entity_category(self) -> str:
        return EntityCategory.DIAGNOSTIC

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement of this entity."""
        return UnitOfPower.WATT

    @property
    def installed_power(self):
        """Return the installed power in Watts."""
        return self._device["installedEffect"]

    def is_on(self) -> bool:
        """Return the state of the relay."""
        return self._device["relayOn"] is True

    @property
    def native_value(self) -> StateType:
        """Return the state of the entity."""
        if self.is_on():
            return self.installed_power

        return 0


class EbecoInstalledPowerSensor(EbecoEntity, SensorEntity):
    def __init__(self, instance, device_data, sensor) -> None:
        """Initialize the thermostat."""
        super().__init__(instance, device_data["id"], sensor)
        self.main_sensor = MAIN_SENSOR

    @property
    def device_class(self) -> str:
        """Return device class."""
        return SensorDeviceClass.POWER

    @property
    def state_class(self) -> str:
        """Return the state class of this entity."""
        return SensorStateClass.MEASUREMENT

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._device['id']}-installed-power"

    @property
    def name(self):
        """Return the name of the device, if any."""
        return f"{self._device['displayName']} Installed Power"

    @property
    def entity_category(self) -> str:
        return EntityCategory.DIAGNOSTIC

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement of this entity."""
        return UnitOfPower.WATT

    @property
    def installed_power(self):
        """Return the installed power in Watts."""
        return self._device["installedEffect"]

    @property
    def native_value(self) -> StateType:
        """Return the state of the entity."""
        return self.installed_power


class EbecoEnergySensor(EbecoEntity, SensorEntity):
    _decimals: int = 2
    _divisor: int = 1
    _multiplier: int = 1

    def __init__(self, instance, device_data, sensor) -> None:
        """Initialize the thermostat energy sensor."""
        super().__init__(instance, device_data["id"], sensor)
        self.main_sensor = MAIN_SENSOR

    @property
    def device_class(self) -> str:
        """Return device class."""
        return SensorDeviceClass.ENERGY

    @property
    def state_class(self) -> str:
        """Return the state class of this entity."""
        return SensorStateClass.TOTAL_INCREASING

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._device['id']}-energy"

    @property
    def name(self):
        """Return the name of the device, if any."""
        return f"{self._device['displayName']} Energy Usage"

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement of this entity."""
        return UnitOfEnergy.KILO_WATT_HOUR

    @property
    def todays_on_minutes(self):
        """Return the number of minutes it has been running today."""
        return self._device["todaysOnMinutes"]

    @property
    def installed_power(self):
        """Return the installed power in Watts."""
        return self._device["installedEffect"]

    @property
    def native_value(self) -> StateType:
        """Return the state of the entity."""
        minutes = self.todays_on_minutes
        power = self.installed_power
        return self.formatter((minutes / 60) * (power / 1000))

    def formatter(self, value):
        """Numeric pass-through formatter."""
        if self._decimals > 0:
            return round(
                float(value * self._multiplier) / self._divisor, self._decimals
            )
        return round(float(value * self._multiplier) / self._divisor)


class EbecoTemperatureSensor(EbecoEntity, SensorEntity):
    def __init__(self, instance, device_data, sensor) -> None:
        """Initialize the thermostat temperature sensor."""
        super().__init__(instance, device_data["id"], sensor.lower())
        self._sensor = sensor

    @property
    def device_class(self) -> str:
        """Return device class."""
        return SensorDeviceClass.TEMPERATURE

    @property
    def state_class(self) -> str:
        """Return the state class of this entity."""
        return SensorStateClass.MEASUREMENT

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._device['id']}-temperature-{self._sensor}"

    @property
    def name(self):
        """Return the name of the device, if any."""
        return f"{self._device['displayName']} {self._sensor} Temperature"

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement of this entity."""
        return UnitOfTemperature.CELSIUS

    @property
    def native_value(self) -> StateType:
        """Return the state of the entity."""
        return self._device[f"temperature{self._sensor}"]
