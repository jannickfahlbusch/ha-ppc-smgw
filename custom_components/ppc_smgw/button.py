import logging

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import RestartGatewayButtonDescription
from .coordinator import SMGwDataUpdateCoordinator
from .entity import SMGWEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    restart_button = RestartGatewayButton(
        config_entry.runtime_data.coordinator, RestartGatewayButtonDescription
    )

    _LOGGER.debug(f"Adding button entities: {restart_button}")
    async_add_entities([restart_button])


class RestartGatewayButton(SMGWEntity, ButtonEntity):
    """Button entity to restart the gateway."""

    def __init__(
        self,
        coordinator: SMGwDataUpdateCoordinator,
        entity_description: ButtonEntityDescription,
    ) -> None:
        """Initialize the Button."""
        super().__init__(coordinator, entity_description)
        self.entity_description = entity_description
        self.coordinator = coordinator

        self._attr_unique_id = f"sensor.{self.get_entity_id_template()}"
        self.entity_id = self._attr_unique_id

    async def async_press(self) -> None:
        """Press the Restart Button."""
        _LOGGER.debug("Restart of Gateway requested")
        await self.coordinator.config_entry.runtime_data.client.ppc_smgw_client.reboot()
