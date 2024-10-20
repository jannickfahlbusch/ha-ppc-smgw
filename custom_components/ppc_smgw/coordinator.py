from datetime import timedelta
import logging

from homeassistant.components.sensor import Entity, EntityDescription
from homeassistant.const import CONF_HOST, CONF_ID, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, MANUFACTURER
from .ppc_smgw import PPC_SMGW

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=10)


class PPC_SMGWLocalDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, config_entry):
        self._host = config_entry.options.get(CONF_HOST, config_entry.data[CONF_HOST])
        username = config_entry.options.get(
            CONF_USERNAME, config_entry.data[CONF_USERNAME]
        )
        password = config_entry.options.get(
            CONF_PASSWORD, config_entry.data[CONF_PASSWORD]
        )

        self.ppc_smgw = PPC_SMGW(
            hass=hass,
            host=self._host,
            username=username,
            password=password,
            websession=get_async_client(hass, verify_ssl=False),
            logger=_LOGGER,
        )
        self.name = config_entry.title
        self._config_entry = config_entry
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)

    async def init_on_load(self):
        try:
            await self.ppc_smgw.update()
            _LOGGER.info(f"after init - found readings: '{self.ppc_smgw._readings}'")
        except Exception as exception:
            _LOGGER.warning(f"init caused an exception {exception}")

    async def _async_update_data(self):
        try:
            await self.ppc_smgw.update()
            return self.ppc_smgw
        except UpdateFailed as exception:
            raise UpdateFailed() from exception

    # async def _async_switch_to_state(self, switch_key, state):
    #    try:
    #        await self.ppc_smgw.switch(switch_key, state)
    #        return self.ppc_smgw
    #    except UpdateFailed as exception:
    #        raise UpdateFailed() from exception


class PPC_SMGWLocalEntity(Entity):
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: PPC_SMGWLocalDataUpdateCoordinator,
        description: EntityDescription,
    ) -> None:
        self.coordinator = coordinator
        self.entity_description = description
        self._stitle = coordinator._config_entry.title
        self._state = None

    @property
    def device_info(self) -> dict:
        _LOGGER.info("Requesting device info")
        # "hw_version": self.coordinator._config_entry.options.get(CONF_DEV_NAME, self.coordinator._config_entry.data.get(CONF_DEV_NAME)),
        return {
            "identifiers": {(DOMAIN, self.coordinator._host, self._stitle)},
            "name": "PPC SMGW",
            "model": "SMGW",
            "sw_version": self.coordinator._config_entry.data.get(CONF_ID, "-unknown-"),
            "manufacturer": MANUFACTURER,
        }

    @property
    def available(self):
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        sensor = self.entity_description.key
        return f"{self._stitle}_{sensor}"

    async def async_added_to_hass(self):
        """Connect to dispatcher listening for entity data notifications."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update entity."""
        await self.coordinator.async_request_refresh()

    @property
    def should_poll(self) -> bool:
        """Entities do not individually poll."""
        return False
