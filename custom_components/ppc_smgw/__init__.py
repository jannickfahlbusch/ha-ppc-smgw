import logging
from datetime import timedelta

import voluptuous as vol
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    Platform,
    CONF_SCAN_INTERVAL,
    CONF_DEBUG,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.loader import async_get_loaded_integration

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, CONF_METER_TYPE
from .coordinator import SMGwDataUpdateCoordinator, ConfigEntry, Data
from custom_components.ppc_smgw.gateways.gateway import Gateway
from custom_components.ppc_smgw.gateways.theben.theben_connexa import ThebenConnexa
from custom_components.ppc_smgw.gateways.vendors import Vendor
from custom_components.ppc_smgw.gateways.ppc.ppc_smgw import PPC_SMGW

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

PLATFORMS: list[Platform] = [
    Platform.BUTTON,
    Platform.SENSOR,
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up this integration using UI."""
    coordinator = SMGwDataUpdateCoordinator(
        hass=hass,
    )

    global SCAN_INTERVAL
    SCAN_INTERVAL = timedelta(
        minutes=entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
    )

    development_mode = False
    if CONF_DEBUG in entry.data:
        development_mode = entry.data[CONF_DEBUG]

    client: Gateway

    _LOGGER.debug(f"Vendor is: {entry.data[CONF_METER_TYPE]} ({type(entry.data[CONF_METER_TYPE])})")
    match Vendor(entry.data[CONF_METER_TYPE]):
        case Vendor.PPC:
            _LOGGER.debug(f"Initializing PPC SMGW client")
            client = PPC_SMGW(
                host=entry.data[CONF_HOST],
                username=entry.data[CONF_USERNAME],
                password=entry.data[CONF_PASSWORD],
                websession=get_async_client(hass, verify_ssl=False),
                logger=_LOGGER,
                debug=development_mode,
            )
        case Vendor.Theben:
            _LOGGER.debug(f"Initializing Theben client")
            client = ThebenConnexa(
                host=entry.data[CONF_HOST],
                username=entry.data[CONF_USERNAME],
                password=entry.data[CONF_PASSWORD],
                websession=get_async_client(hass, verify_ssl=False),
                logger=_LOGGER,
                debug=development_mode,
            )
        case _:
            _LOGGER.error(f"Unexpected error, no meter type matching for entry {entry}. Meter type: {entry.data[CONF_METER_TYPE]}")

    entry.runtime_data = Data(
        client=client,
        integration=async_get_loaded_integration(hass, entry.domain),
        coordinator=coordinator,
    )

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
