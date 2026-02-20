"""Fixtures for PPC SMGW integration tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    CONF_DEBUG,
)
from custom_components.ppc_smgw.const import (
    CONF_METER_TYPE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from custom_components.ppc_smgw.gateways.emh import const as emh_const
from custom_components.ppc_smgw.gateways.theben import const as theben_const
from custom_components.ppc_smgw.gateways.ppc import const as ppc_const
from custom_components.ppc_smgw.gateways.vendors import Vendor


@pytest.fixture
def mock_gateway():
    """Mock a Gateway instance.

    This fixture provides a basic mock gateway that works for all vendor types.
    Vendor-specific behavior can be added in tests as needed.
    """
    gateway = MagicMock()
    gateway.check_connection = AsyncMock(return_value=True)
    gateway.get_data = AsyncMock(return_value=None)
    gateway.reboot = AsyncMock()
    return gateway


def create_mock_config_entry(
    data: dict,
    entry_id: str = "test_entry_id",
    options: dict | None = None,
) -> config_entries.ConfigEntry:
    """Factory function to create ConfigEntry objects for testing.

    Args:
        data: Configuration data for the entry
        entry_id: Unique identifier for the entry (default: "test_entry_id")
        options: Optional options dictionary (default: empty dict)

    Returns:
        A properly configured ConfigEntry for testing
    """
    return config_entries.ConfigEntry(
        version=2,
        minor_version=2,
        domain=DOMAIN,
        title=data.get(CONF_NAME, "Test Entry"),
        data=data,
        source=config_entries.SOURCE_USER,
        entry_id=entry_id,
        discovery_keys={},
        options=options or {},
        unique_id=None,
        subentries_data={},
    )


@pytest.fixture
def ppc_config_data():
    """Return mock config data for PPC vendor."""
    return {
        CONF_METER_TYPE: Vendor.PPC,
        CONF_NAME: ppc_const.DEFAULT_NAME,
        CONF_HOST: "https://192.168.1.200/cgi-bin/hanservice.cgi",
        CONF_USERNAME: "testuser",
        CONF_PASSWORD: "testpass",
        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
        CONF_DEBUG: False,
    }


@pytest.fixture
def theben_config_data():
    """Return mock config data for Theben vendor."""
    return {
        CONF_METER_TYPE: Vendor.Theben,
        CONF_NAME: theben_const.DEFAULT_NAME,
        CONF_HOST: "https://192.168.1.100/smgw/m2m/test.sm/json",
        CONF_USERNAME: "testuser",
        CONF_PASSWORD: "testpass",
        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
    }


@pytest.fixture
def emh_config_data():
    """Return mock config data for EMH vendor."""
    return {
        CONF_METER_TYPE: Vendor.EMH,
        CONF_NAME: emh_const.DEFAULT_NAME,
        CONF_HOST: "https://192.168.1.150",
        CONF_USERNAME: "testuser",
        CONF_PASSWORD: "testpass",
        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
    }


@pytest.fixture(params=list(Vendor))
def vendor(request):
    """Parametrized fixture that yields each Vendor enum value."""
    return request.param


@pytest.fixture
def vendor_config_data(vendor, ppc_config_data, theben_config_data, emh_config_data):
    """Return config data for the parametrized vendor.

    Maps each Vendor enum to its corresponding config data fixture.
    """
    vendor_map = {
        Vendor.PPC: ppc_config_data,
        Vendor.Theben: theben_config_data,
        Vendor.EMH: emh_config_data,
    }
    return vendor_map[vendor]


@pytest.fixture
def vendor_expected_name(vendor):
    """Return the expected default name for the parametrized vendor."""
    name_map = {
        Vendor.PPC: ppc_const.DEFAULT_NAME,
        Vendor.Theben: theben_const.DEFAULT_NAME,
        Vendor.EMH: emh_const.DEFAULT_NAME,
    }
    return name_map[vendor]
