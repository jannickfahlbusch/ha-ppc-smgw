import logging
from datetime import datetime

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import LastUpdatedSensorDescription
from .coordinator import ConfigEntry, SMGwDataUpdateCoordinator
from .entity import SMGWEntity
from .gateways.reading import Information
from .obis import (
    build_obis_name,
    get_obis_info,
    parse_obis,
)

_LOGGER = logging.getLogger(__name__)
PARALLEL_UPDATES = 0


def build_entity_description(obis_code: str) -> SensorEntityDescription:
    """Build a SensorEntityDescription from an OBIS code using the catalog."""
    parsed = parse_obis(obis_code)
    if parsed is None:
        return SensorEntityDescription(
            key=obis_code,
            name=f"OBIS {obis_code}",
            icon="mdi:meter-electric",
            entity_registry_enabled_default=False,
            entity_category=EntityCategory.DIAGNOSTIC,
        )

    info = get_obis_info(parsed)
    name = build_obis_name(parsed, info)

    if info is None:
        return SensorEntityDescription(
            key=obis_code,
            name=name,
            icon="mdi:meter-electric",
            entity_registry_enabled_default=False,
            entity_category=EntityCategory.DIAGNOSTIC,
        )

    return SensorEntityDescription(
        key=obis_code,
        name=name,
        device_class=info.device_class,
        state_class=info.state_class,
        native_unit_of_measurement=info.unit,
        icon=info.icon,
        suggested_display_precision=info.suggested_display_precision,
        entity_registry_enabled_default=True,
    )


@callback
def _migrate_sensor_unique_ids(ent_reg: er.EntityRegistry, entry_id: str) -> None:
    """Migrate sensor unique_ids from old format (sensor.xxx) to new (xxx)."""
    for entity_entry in er.async_entries_for_config_entry(ent_reg, entry_id):
        old_uid = entity_entry.unique_id
        if old_uid.startswith("sensor."):
            new_uid = old_uid.removeprefix("sensor.")
            try:
                ent_reg.async_update_entity(
                    entity_entry.entity_id, new_unique_id=new_uid
                )
                _LOGGER.info(
                    "Migrated unique_id for %s: %s -> %s",
                    entity_entry.entity_id,
                    old_uid,
                    new_uid,
                )
            except ValueError:
                _LOGGER.warning(
                    "Could not migrate unique_id for %s: %s -> %s (already exists)",
                    entity_entry.entity_id,
                    old_uid,
                    new_uid,
                )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator = entry.runtime_data.coordinator

    # Migrate old unique_ids before creating entities
    _migrate_sensor_unique_ids(er.async_get(hass), entry.entry_id)

    known_obis_codes: set[str] = set()

    @callback
    def _async_add_new_entities() -> None:
        """Check coordinator data for new OBIS codes and add entities."""
        data = coordinator.data
        if not isinstance(data, Information):
            return

        new_entities: list[SensorEntity] = []
        for obis_code in data.readings:
            if obis_code not in known_obis_codes:
                known_obis_codes.add(obis_code)
                new_entities.append(
                    OBISSensor(
                        coordinator=coordinator,
                        entity_description=build_entity_description(obis_code),
                    )
                )

        if new_entities:
            _LOGGER.debug(
                "Discovered %d new OBIS sensors: %s",
                len(new_entities),
                [e.entity_description.key for e in new_entities],
            )
            async_add_entities(new_entities)

    # Create entities from current data (already populated via first refresh)
    _async_add_new_entities()

    # Listen for future updates to discover new OBIS codes
    entry.async_on_unload(coordinator.async_add_listener(_async_add_new_entities))

    # LastUpdatedSensor is always created (not OBIS-based)
    async_add_entities(
        [
            LastUpdatedSensor(
                coordinator=coordinator,
                entity_description=LastUpdatedSensorDescription,
            )
        ]
    )


class OBISSensor(SMGWEntity, SensorEntity):
    def __init__(
        self,
        coordinator: SMGwDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator, entity_description)
        self.entity_description = entity_description

        self._attr_unique_id = self.get_entity_id_template()
        self._attr_name = entity_description.name

    @property
    def native_value(self) -> str | float | None:
        """Return the native value of the sensor."""
        data = self.coordinator.data

        if not isinstance(data, Information):
            return None

        if self.entity_description.key not in data.readings:
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

        self._attr_unique_id = self.get_entity_id_template()
        self._attr_name = entity_description.name

    @property
    def native_value(self) -> datetime | None:
        """Return the native value of the sensor."""
        data = self.coordinator.data

        if not isinstance(data, Information):
            return None

        return data.last_update
