from __future__ import annotations

from datetime import datetime
import logging

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify
from obis_parser import OBIS

from custom_components.ppc_smgw.gateways.reading import Information

from .const import (
    SENSOR_TYPES,
    FirmwareVersionSensorDescription,
    LastUpdatedSensorDescription,
)
from .coordinator import ConfigEntry, SMGwDataUpdateCoordinator
from .entity import SMGWEntity
from .obis_ha import OBISSensorSpec, build_obis_sensor_description

_LOGGER = logging.getLogger(__name__)
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""

    coordinator = entry.runtime_data.coordinator
    dynamic_enabled = (
        getattr(entry.runtime_data.client, "dynamic_obis_discovery_enabled", False)
        is True
    )
    _LOGGER.debug(
        "Setting up sensors with dynamic OBIS discovery %s",
        "enabled" if dynamic_enabled else "disabled",
    )

    if not dynamic_enabled:
        _LOGGER.debug("Creating %d static OBIS sensor(s)", len(SENSOR_TYPES))
        entities: list[SensorEntity] = [
            OBISSensor(
                coordinator=coordinator,
                spec=OBISSensorSpec(description=entity_description),
            )
            for entity_description in SENSOR_TYPES
        ]
        entities.append(
            LastUpdatedSensor(
                coordinator=coordinator,
                entity_description=LastUpdatedSensorDescription,
            )
        )
        entities.append(
            FirmwareSensor(
                coordinator=coordinator,
                entity_description=FirmwareVersionSensorDescription,
            )
        )

        async_add_entities(entities)
        return

    known_obis_codes: set[str] = set()
    entities = _build_dynamic_obis_sensors(coordinator, known_obis_codes)
    if known_obis_codes:
        _remove_stale_static_obis_entities(hass, entry, known_obis_codes)
    else:
        _LOGGER.debug("Skipping stale OBIS cleanup because no readings were delivered")
    _LOGGER.debug("Creating %d initial dynamic OBIS sensor(s)", len(entities))

    entities.append(
        LastUpdatedSensor(
            coordinator=coordinator,
            entity_description=LastUpdatedSensorDescription,
        )
    )
    entities.append(
        FirmwareSensor(
            coordinator=coordinator,
            entity_description=FirmwareVersionSensorDescription,
        )
    )

    async_add_entities(entities)

    def _add_new_obis_sensors() -> None:
        if new_entities := _build_dynamic_obis_sensors(coordinator, known_obis_codes):
            _LOGGER.debug(
                "Adding %d newly discovered dynamic OBIS sensor(s)", len(new_entities)
            )
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_add_new_obis_sensors))


def _build_dynamic_obis_sensors(
    coordinator: SMGwDataUpdateCoordinator, known_obis_codes: set[str]
) -> list[OBISSensor]:
    data = coordinator.data
    if not isinstance(data, Information):
        return []

    entities: list[OBISSensor] = []
    for obis_obj in data.readings:
        key = obis_obj.canonical
        if key in known_obis_codes:
            continue

        known_obis_codes.add(key)

        if not obis_obj.is_electricity:
            _LOGGER.info(
                "Skipping non-electricity OBIS code %s (medium A=%s); "
                "sub-metered gas/heat/water is not supported",
                key,
                obis_obj.a,
            )
            continue

        _LOGGER.debug("Discovered dynamic OBIS sensor for %s", key)
        entities.append(
            OBISSensor(
                coordinator=coordinator,
                spec=build_obis_sensor_description(key),
            )
        )

    return entities


def _remove_stale_static_obis_entities(
    hass: HomeAssistant, entry: ConfigEntry, delivered_obis_codes: set[str]
) -> None:
    registry = er.async_get(hass)
    for description in SENSOR_TYPES:
        if description.key in delivered_obis_codes:
            continue

        unique_id = f"sensor.{slugify(f'{entry.entry_id}_{description.key}')}"
        entity_id = registry.async_get_entity_id("sensor", entry.domain, unique_id)
        if entity_id is None:
            continue

        _LOGGER.debug(
            "Removing stale static OBIS entity %s for missing OBIS code %s",
            entity_id,
            description.key,
        )
        registry.async_remove(entity_id)


class OBISSensor(SMGWEntity, SensorEntity):
    def __init__(
        self,
        coordinator: SMGwDataUpdateCoordinator,
        spec: OBISSensorSpec,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator, spec.description)
        self.entity_description = spec.description
        self._obis_key: OBIS | None = OBIS.parse(spec.description.key)

        self._attr_unique_id = f"sensor.{self.get_entity_id_template()}"
        self.entity_id = self._attr_unique_id

        if spec.translation_key is not None:
            # Name comes from translation_key. HA's _name_internal returns
            # self._attr_name FIRST if that attribute exists at all — even when
            # None — which would suppress the translation lookup. So we must NOT
            # assign _attr_name here; leave the attribute unset.
            self._attr_translation_key = spec.translation_key
            if spec.translation_placeholders:
                self._attr_translation_placeholders = spec.translation_placeholders
        elif spec.name_fallback is not None:
            self._attr_translation_key = None
            self._attr_name = spec.name_fallback
        else:
            # Static path: the SMGWEntity base sets _attr_translation_key to the
            # OBIS code (e.g. "1-0:2.8.0"), which is not a valid translation slug
            # and matches no entry, leaving the entity nameless. Fall back to the
            # description's own name explicitly.
            self._attr_translation_key = None
            self._attr_name = spec.description.name

    @property
    def native_value(self) -> str | float | None:
        """Return the native value of the sensor."""
        data = self.coordinator.data

        if not isinstance(data, Information):
            return None

        if self._obis_key is not None and (
            reading := data.readings.get(self._obis_key)
        ):
            return reading.value

        for obis_obj, reading in data.readings.items():
            if obis_obj.canonical == self.entity_description.key:
                return reading.value

        _LOGGER.debug("Found no value for %s", self.entity_description.key)
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
