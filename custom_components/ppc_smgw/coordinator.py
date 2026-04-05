import logging
from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import DOMAIN
from dataclasses import dataclass
from homeassistant.config_entries import ConfigEntry
from homeassistant.loader import Integration

from .gateways.gateway import Gateway
from .gateways.reading import Information


_LOGGER = logging.getLogger(__name__)

type ConfigEntry = ConfigEntry[Data]


class SMGwDataUpdateCoordinator(DataUpdateCoordinator[Information | None]):
    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        update_interval: timedelta,
    ) -> None:
        super().__init__(
            hass=hass, logger=_LOGGER, name=DOMAIN, update_interval=update_interval
        )

    async def _async_update_data(self) -> Information | None:
        try:
            _LOGGER.debug("Fetching data from API")
            data = await self.config_entry.runtime_data.client.get_data()

            # Validate data type at the source (issue #75)
            if data is not None and not isinstance(data, Information):
                _LOGGER.error(
                    f"Gateway returned unexpected type: {type(data).__name__}. "
                    f"Expected Information or None."
                )
                return None

            return data
        except Exception:
            _LOGGER.exception("Unexpected error during update")
            raise


@dataclass
class Data:
    """Data for the Blueprint integration."""

    client: Gateway
    coordinator: SMGwDataUpdateCoordinator
    integration: Integration
