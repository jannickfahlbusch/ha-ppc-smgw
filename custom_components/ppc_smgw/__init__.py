import asyncio
from datetime import timedelta
import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_SCAN_INTERVAL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import PPC_SMGWLocalDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

PLATFORMS = [
    Platform.BUTTON,
    Platform.SENSOR,
]


def mask_map(d):
    for k, v in d.copy().items():
        if isinstance(v, dict):
            d.pop(k)
            d[k] = v
            mask_map(v)
        else:
            lk = k.lower()
            if lk in ("username", "password"):
                v = "<MASKED>"
            d.pop(k)
            d[k] = v
    return d


async def async_setup(hass: HomeAssistant, config: dict):
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    global SCAN_INTERVAL
    SCAN_INTERVAL = timedelta(
        minutes=config_entry.options.get(
            CONF_SCAN_INTERVAL,
            config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
    )

    _LOGGER.info(
        f"Starting PPC_SMGW with interval: {SCAN_INTERVAL} - ConfigEntry: {mask_map(dict(config_entry.as_dict()))}"
    )

    if DOMAIN not in hass.data:
        value = "UNKOWN"
        hass.data.setdefault(DOMAIN, {"manifest_version": value})

    coordinator = PPC_SMGWLocalDataUpdateCoordinator(hass, config_entry)
    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    await coordinator.init_on_load()

    hass.data[DOMAIN][config_entry.entry_id] = coordinator

    _LOGGER.debug(
        f"Setting up entry for {config_entry.entry_id}, Platforms: {PLATFORMS}"
    )
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    if config_entry.state != ConfigEntryState.LOADED:
        config_entry.add_update_listener(async_reload_entry)

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )
    if unload_ok:
        if DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]:
            hass.data[DOMAIN].pop(config_entry.entry_id)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    if await async_unload_entry(hass, config_entry):
        await asyncio.sleep(2)
        await async_setup_entry(hass, config_entry)
