import logging

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import SENSOR_TYPES, LastUpdatedSensorDescription
from .coordinator import SMGwDataUpdateCoordinator, ConfigEntry
from .entity import SMGWEntity
from custom_components.ppc_smgw.gateways.reading import Information

_LOGGER = logging.getLogger(__name__)
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
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

        data: Information = self.coordinator.data

        if self.entity_description.key not in data.readings:
            _LOGGER.debug(f"Found no value for {self.entity_description.key}")
            return None

        reading = data.readings[self.entity_description.key]

        return reading.value


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
    def native_value(self) -> str | None:
        """Return the native value of the sensor."""

        data: Information = self.coordinator.data

        return data.last_update
