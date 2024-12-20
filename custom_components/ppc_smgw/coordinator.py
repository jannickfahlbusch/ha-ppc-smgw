import logging
from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import DOMAIN
from dataclasses import dataclass
from homeassistant.config_entries import ConfigEntry
from homeassistant.loader import Integration
from .ppc_smgw import PPC_SMGW


_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=10)

type ConfigEntry = ConfigEntry[Data]


class PPC_SMGWDataUpdateCoordinator(DataUpdateCoordinator):
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

    client: PPC_SMGW
    coordinator: PPC_SMGWDataUpdateCoordinator
    integration: Integration
