import logging

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import DEFAULT_NAME
from .coordinator import SMGwDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class SMGWEntity(CoordinatorEntity[SMGwDataUpdateCoordinator]):
    """Base class for all entities originating from SMGW."""

    entity_description: EntityDescription

    def __init__(
        self,
        coordinator: SMGwDataUpdateCoordinator,
        entity_description: EntityDescription,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)

        self.entity_description = entity_description

        _LOGGER.debug(
            "Initializing %s. EntryID: %s",
            entity_description.key,
            coordinator.config_entry.entry_id,
        )

        self._attr_device_info = DeviceInfo(
            identifiers={
                (
                    coordinator.config_entry.domain,
                    coordinator.config_entry.entry_id,
                ),
            },
            name=self.get_name(),
            manufacturer=self.get_manufacturer(),
            model=self.get_model(),
            sw_version=self.get_firmware_version(),
        )

        self._attr_has_entity_name = True

    def get_entity_id_template(self):
        return slugify(
            f"{self.coordinator.config_entry.entry_id}_{self.entity_description.key}"
        )

    def get_firmware_version(self) -> str:
        if self.coordinator.data is None:
            return "Unknown"
        try:
            return self.coordinator.data.firmware_version
        except AttributeError:
            return "Unknown"

    def get_manufacturer(self) -> str:
        if self.coordinator.data is None:
            return "Unknown"
        try:
            return self.coordinator.data.manufacturer
        except AttributeError:
            return "Unknown"

    def get_model(self) -> str:
        if self.coordinator.data is None:
            return "Unknown"
        try:
            return self.coordinator.data.model
        except AttributeError:
            return "Unknown"

    def get_name(self) -> str:
        if self.coordinator.data is None:
            return DEFAULT_NAME
        try:
            return self.coordinator.data.name
        except AttributeError:
            return DEFAULT_NAME
