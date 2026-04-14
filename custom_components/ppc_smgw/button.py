import logging

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import RestartGatewayButtonDescription
from .coordinator import SMGwDataUpdateCoordinator
from .entity import SMGWEntity

_LOGGER = logging.getLogger(__name__)


@callback
def _migrate_button_unique_ids(ent_reg: er.EntityRegistry, entry_id: str) -> None:
    """Migrate button unique_ids from old format (button.xxx) to new (xxx)."""
    for entity_entry in er.async_entries_for_config_entry(ent_reg, entry_id):
        old_uid = entity_entry.unique_id
        if old_uid.startswith("button."):
            new_uid = old_uid.removeprefix("button.")
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
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    _migrate_button_unique_ids(er.async_get(hass), config_entry.entry_id)

    restart_button = RestartGatewayButton(
        config_entry.runtime_data.coordinator, RestartGatewayButtonDescription
    )

    _LOGGER.debug("Adding button entities: %s", restart_button)
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

        self._attr_unique_id = self.get_entity_id_template()
        self._attr_name = entity_description.name

    async def async_press(self) -> None:
        """Press the Restart Button."""
        _LOGGER.debug("Restart of Gateway requested")
        await self.coordinator.config_entry.runtime_data.client.reboot()
