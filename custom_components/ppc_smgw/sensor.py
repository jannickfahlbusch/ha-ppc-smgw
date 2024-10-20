import logging

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import slugify

from .const import DOMAIN, SENSOR_TYPES, LastUpdatedSensorDescription
from .coordinator import PPC_SMGWLocalDataUpdateCoordinator, PPC_SMGWLocalEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = [LastUpdatedSensor(coordinator, LastUpdatedSensorDescription)]
    available_sensors = None
    if hasattr(coordinator, "ppc_smgw"):
        if hasattr(coordinator.ppc_smgw, "_readings"):
            if len(coordinator.ppc_smgw._readings) > 0:
                available_sensors = []
                for reading in coordinator.ppc_smgw._readings:
                    available_sensors.append(reading.obis)
                _LOGGER.info(f"available sensors found: {available_sensors}")
            else:
                _LOGGER.warning(f"no sensors found @ ppc_smgw")

    if available_sensors is None or len(available_sensors) == 0:
        _LOGGER.warning(
            f"Could not detect available sensors (obis-codes) using just 'import total' as default!"
        )
        available_sensors = ["1-0:1.8.0"]

    for reading in available_sensors:
        _LOGGER.debug(f"Creating sensor for reading: {reading}")

        description = get_sensor_description(reading)
        _LOGGER.debug(f"Description: {description}")

        entity = PPC_SMGWSensor(coordinator, description)
        entities.append(entity)

    _LOGGER.debug(f"Adding entities: {entities}")
    for entity in entities:
        _LOGGER.debug(
            f"Adding entity: {entity.entity_description} - {entity.entity_description.key}"
        )

    async_add_entities(entities)


class PPC_SMGWSensor(PPC_SMGWLocalEntity, SensorEntity):
    def __init__(
        self,
        coordinator: PPC_SMGWLocalDataUpdateCoordinator,
        description: SensorEntityDescription,
    ):
        """Initialize a singular value sensor."""
        super().__init__(coordinator=coordinator, description=description)
        if hasattr(self.entity_description, "entity_registry_enabled_default"):
            self._attr_entity_registry_enabled_default = (
                self.entity_description.entity_registry_enabled_default
            )
        else:
            self._attr_entity_registry_enabled_default = True

        key = self.entity_description.key.lower()
        self.entity_id = (
            f"sensor.{slugify(self.coordinator._config_entry.entry_id)}_{key}"
        )

        # we use the "key" also as our internal translation-key - and EXTREMELY important we have
        # to set the '_attr_has_entity_name' to trigger the calls to the localization framework!
        self._attr_translation_key = key
        self._attr_has_entity_name = True

        if (
            hasattr(description, "suggested_display_precision")
            and description.suggested_display_precision is not None
        ):
            self._attr_suggested_display_precision = (
                description.suggested_display_precision
            )
        else:
            self._attr_suggested_display_precision = 2

    @property
    def state(self):
        """Return the current state."""
        reading = self.coordinator.ppc_smgw.get_reading_for_obis_code(
            self.entity_description.key
        )
        if reading is None:
            return None

        value = reading.value
        if type(value) != type(False):
            try:
                rounded_value = round(
                    float(value), self._attr_suggested_display_precision
                )
                return rounded_value
            except (ValueError, TypeError):
                return value
        else:
            return value


class LastUpdatedSensor(PPC_SMGWLocalEntity, SensorEntity):
    def __init__(
        self,
        coordinator: PPC_SMGWLocalDataUpdateCoordinator,
        description: SensorEntityDescription,
    ):
        """Initialize a singular value sensor."""
        super().__init__(coordinator=coordinator, description=description)

        key = self.entity_description.key.lower()
        self.entity_id = (
            f"sensor.{slugify(self.coordinator._config_entry.entry_id)}_{key}"
        )

        # we use the "key" also as our internal translation-key - and EXTREMELY important we have
        # to set the '_attr_has_entity_name' to trigger the calls to the localization framework!
        self._attr_translation_key = key
        self._attr_has_entity_name = True

    @property
    def state(self):
        """Return the current state."""

        _LOGGER.info("Requesting last update timestamp")

        readings = self.coordinator.ppc_smgw.get_readings()

        if len(readings) == 0:
            return None

        return readings[0].timestamp


def get_sensor_description(obis_code: str) -> SensorEntityDescription | None:
    for description in SENSOR_TYPES:
        if description.key == obis_code:
            return description

    return None
