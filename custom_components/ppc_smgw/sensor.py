from datetime import datetime
import logging

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.ppc_smgw.gateways.reading import Information

from .const import (
    SENSOR_TYPES,
    FirmwareVersionSensorDescription,
    LastUpdatedSensorDescription,
)
from .coordinator import ConfigEntry, SMGwDataUpdateCoordinator
from .entity import SMGWEntity

_LOGGER = logging.getLogger(__name__)
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""

    entities: list[SensorEntity] = [
        OBISSensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in SENSOR_TYPES
    ]

    entities.append(
        LastUpdatedSensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=LastUpdatedSensorDescription,
        )
    )

    entities.append(
        FirmwareSensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=FirmwareVersionSensorDescription,
        )
    )

    async_add_entities(entities)


class OBISSensor(SMGWEntity, SensorEntity):
    def __init__(
        self,
        coordinator: SMGwDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator, entity_description)
        self.entity_description = entity_description

        self._attr_unique_id = f"sensor.{self.get_entity_id_template()}"
        self.entity_id = self._attr_unique_id

    @property
    def native_value(self) -> str | None:
        """Return the native value of the sensor."""
        _LOGGER.debug(f"Data: {self.coordinator.data}")

        data = self.coordinator.data

        if not isinstance(data, Information):
            return None

        for obis_obj, reading in data.readings.items():
            if obis_obj.canonical == self.entity_description.key:
                return reading.value

        _LOGGER.debug(f"Found no value for {self.entity_description.key}")
        return None


class LastUpdatedSensor(SMGWEntity, SensorEntity):
    def __init__(
        self,
        coordinator: SMGwDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator, entity_description)
        self.entity_description = entity_description

        self._attr_unique_id = f"sensor.{self.get_entity_id_template()}"
        self.entity_id = self._attr_unique_id

    @property
    def native_value(self) -> datetime | None:
        """Return the native value of the sensor."""

        data = self.coordinator.data

        if not isinstance(data, Information):
            return None

        return data.last_update


class FirmwareSensor(SMGWEntity, SensorEntity):
    """Sensor for the gateway firmware version."""

    def __init__(
        self,
        coordinator: SMGwDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator, entity_description)
        self.entity_description = entity_description

        self._attr_unique_id = f"sensor.{self.get_entity_id_template()}"
        self.entity_id = self._attr_unique_id
        self._cached_firmware_version: str | None = None

    @property
    def native_value(self) -> str | None:
        """Return the firmware version."""
        data = self.coordinator.data

        if not isinstance(data, Information):
            return self._cached_firmware_version

        if data.firmware_version and data.firmware_version != "Unknown":
            self._cached_firmware_version = data.firmware_version

        return self._cached_firmware_version
