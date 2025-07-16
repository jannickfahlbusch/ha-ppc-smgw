import logging
from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import DOMAIN
from dataclasses import dataclass
from homeassistant.config_entries import ConfigEntry
from homeassistant.loader import Integration

from .gateways.gateway import Gateway


_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=10)

type ConfigEntry = ConfigEntry[Data]


class SMGwDataUpdateCoordinator(DataUpdateCoordinator):
    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
    ) -> None:
        super().__init__(
            hass=hass, logger=_LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL
        )

    async def _async_update_data(self):
        try:
            _LOGGER.debug("Fetching data from API")
            return await self.config_entry.runtime_data.client.get_data()
        except Exception as e:
            _LOGGER.error(e)
            raise e


@dataclass
class Data:
    """Data for the Blueprint integration."""

    client: Gateway
    coordinator: SMGwDataUpdateCoordinator
    integration: Integration
