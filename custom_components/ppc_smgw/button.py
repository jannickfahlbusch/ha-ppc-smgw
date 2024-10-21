import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, RestartGatewayButtonDescription
from .coordinator import PPC_SMGWLocalDataUpdateCoordinator, PPC_SMGWLocalEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = [RestartGatewayButton(coordinator)]

    _LOGGER.debug(f"Adding button entities: {entities}")
    async_add_entities(entities)


class RestartGatewayButton(PPC_SMGWLocalEntity, ButtonEntity):
    """Button entity to restart the gateway."""

    def __init__(
        self,
        coordinator: PPC_SMGWLocalDataUpdateCoordinator,
    ) -> None:
        """Initialize the Button."""
        super().__init__(
            coordinator=coordinator, description=RestartGatewayButtonDescription
        )

        self.coordinator = coordinator

        key = self.entity_description.key.lower()

        self._attr_unique_id = (
            f"button.{self.coordinator._config_entry.entry_id}_restart"
        )

        _LOGGER.debug(f"Entity ID: {self._attr_unique_id}")

        # we use the "key" also as our internal translation-key - and EXTREMELY important we have
        # to set the '_attr_has_entity_name' to trigger the calls to the localization framework!
        self._attr_translation_key = key
        self._attr_has_entity_name = True

    async def async_press(self) -> None:
        """Press the Restart Button."""
        _LOGGER.debug("Restart of Gateway requested")
        await self.coordinator.ppc_smgw.ppc_smgw_client.reboot()
