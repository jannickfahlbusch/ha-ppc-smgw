import asyncio
import logging
from datetime import timedelta

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL, CONF_PASSWORD, CONF_USERNAME, CONF_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.entity import EntityDescription, Entity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    MANUFACTURER,
    DEFAULT_SCAN_INTERVAL,
)

from .ppc_smgw import PPC_SMGW

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=10)
CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

PLATFORMS = ["sensor"]

def mask_map(d):
    for k, v in d.copy().items():
        if isinstance(v, dict):
            d.pop(k)
            d[k] = v
            mask_map(v)
        else:
            lk = k.lower()
            if lk == "username" or lk == "password":
                v = "<MASKED>"
            d.pop(k)
            d[k] = v
    return d

async def async_setup(hass: HomeAssistant, config: dict):
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    global SCAN_INTERVAL
    SCAN_INTERVAL = timedelta(minutes=config_entry.options.get(CONF_SCAN_INTERVAL,
                                                               config_entry.data.get(CONF_SCAN_INTERVAL,
                                                                                     DEFAULT_SCAN_INTERVAL)))

    _LOGGER.info(f"Starting PPC_SMGW with interval: {SCAN_INTERVAL} - ConfigEntry: {mask_map(dict(config_entry.as_dict()))}")

    if DOMAIN not in hass.data:
        value = "UNKOWN"
        hass.data.setdefault(DOMAIN, {"manifest_version": value})
    coordinator = PPC_SMGWLocalDataUpdateCoordinator(hass, config_entry)
    if not coordinator.last_update_success:
        raise ConfigEntryNotReady
    else:
        await coordinator.init_on_load()

    hass.data[DOMAIN][config_entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    if config_entry.state != ConfigEntryState.LOADED:
        config_entry.add_update_listener(async_reload_entry)

    return True


class PPC_SMGWLocalDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, config_entry):
        self._host = config_entry.options.get(CONF_HOST, config_entry.data[CONF_HOST])
        username = config_entry.options.get(CONF_USERNAME, config_entry.data[CONF_USERNAME])
        password = config_entry.options.get(CONF_PASSWORD, config_entry.data[CONF_PASSWORD])

        self.ppc_smgw = PPC_SMGW(hass=hass, host=self._host, username=username, password=password, websession=get_async_client(hass, verify_ssl=False), logger=_LOGGER)
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


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
    if unload_ok:
        if DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]:
            hass.data[DOMAIN].pop(config_entry.entry_id)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    if await async_unload_entry(hass, config_entry):
        await asyncio.sleep(2)
        await async_setup_entry(hass, config_entry)

class PPC_SMGWLocalEntity(Entity):
    _attr_should_poll = False

    def __init__(
            self, coordinator: PPC_SMGWLocalDataUpdateCoordinator, description: EntityDescription
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
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))

    async def async_update(self):
        """Update entity."""
        await self.coordinator.async_request_refresh()

    @property
    def should_poll(self) -> bool:
        """Entities do not individually poll."""
        return False
