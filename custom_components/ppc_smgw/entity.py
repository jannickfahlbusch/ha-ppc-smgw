import logging

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_NAME
from .coordinator import SMGwDataUpdateCoordinator
from homeassistant.util import slugify


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
        self._coordinator = coordinator

        _LOGGER.debug(
            f"Initializing {entity_description.key}. EntryID: {coordinator.config_entry.entry_id}"
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

        self._attr_translation_key = self.entity_description.key.lower()
        self._attr_has_entity_name = True

    def get_entity_id_template(self):
        return slugify(
            f"{self.coordinator.config_entry.entry_id}_{self.entity_description.key}"
        )

    def get_firmware_version(self) -> str:
        firmware_version = "Unknown"
        try:
            firmware_version = self._coordinator.data.firmware_version
        except AttributeError:
            _LOGGER.debug(
                f"Firmware version not available. Data available: {self._coordinator.data}"
            )

        return firmware_version

    def get_manufacturer(self) -> str:
        manufacturer = "Unknown"
        try:
            manufacturer = self._coordinator.data.manufacturer
        except AttributeError:
            _LOGGER.debug(
                f"Manufacturer data not available. Data available: {self._coordinator.data}"
            )

        return manufacturer

    def get_model(self) -> str:
        model = "Unknown"
        try:
            model = self._coordinator.data.model
        except AttributeError:
            _LOGGER.debug(
                f"Model data not available. Data available: {self._coordinator.data}"
            )

        return model

    def get_name(self) -> str:
        name = DEFAULT_NAME
        try:
            name = self._coordinator.data.name
        except AttributeError:
            _LOGGER.debug(
                f"Name not available, using default. Data available: {self._coordinator.data}"
            )

        return name
