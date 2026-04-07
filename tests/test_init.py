"""Tests for PPC SMGW integration initialization - simplified version."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytz
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)

from custom_components.ppc_smgw import async_setup_entry, async_unload_entry
from custom_components.ppc_smgw.const import (
    CONF_METER_TYPE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from custom_components.ppc_smgw.coordinator import (
    SMGwDataUpdateCoordinator,
    Data,
)
from custom_components.ppc_smgw.gateways.reading import Information, Reading
from custom_components.ppc_smgw.gateways.vendors import Vendor
from tests.conftest import create_mock_config_entry


@pytest.mark.asyncio
class TestInit:
    """Test the integration initialization."""

    async def test_setup_entry_succeeds(
        self, hass: HomeAssistant, vendor, vendor_config_data, mock_gateway
    ):
        """Test that setup succeeds for all vendors (parametrized)."""
        entry = create_mock_config_entry(data=vendor_config_data)

        # Mock the minimal dependencies needed for setup
        mock_integration = MagicMock()
        mock_integration.domain = DOMAIN
        mock_coordinator = MagicMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()

        with (
            patch("custom_components.ppc_smgw.PPC_SMGW", return_value=mock_gateway),
            patch("custom_components.ppc_smgw.ThebenConexa", return_value=mock_gateway),
            patch("custom_components.ppc_smgw.EMHGateway", return_value=mock_gateway),
            patch("custom_components.ppc_smgw.create_async_httpx_client"),
            patch(
                "custom_components.ppc_smgw.async_get_loaded_integration",
                return_value=mock_integration,
            ),
            patch.object(hass.config_entries, "async_forward_entry_setups"),
            patch(
                "custom_components.ppc_smgw.SMGwDataUpdateCoordinator",
                return_value=mock_coordinator,
            ),
        ):
            result = await async_setup_entry(hass, entry)

        # Simple assertion: setup succeeded
        assert result is True

    async def test_unload_entry_succeeds(self, hass: HomeAssistant, ppc_config_data):
        """Test that unload succeeds."""
        entry = create_mock_config_entry(data=ppc_config_data)

        with patch.object(
            hass.config_entries, "async_unload_platforms", return_value=True
        ):
            result = await async_unload_entry(hass, entry)

        assert result is True

    async def test_setup_entry_fails_on_connection_error(
        self, hass: HomeAssistant, ppc_config_data, mock_gateway
    ):
        """Test that setup raises ConfigEntryNotReady when initial connection fails."""
        entry = create_mock_config_entry(data=ppc_config_data)

        mock_integration = MagicMock()
        mock_integration.domain = DOMAIN
        mock_coordinator = MagicMock()
        # Simulate connection failure during first refresh
        mock_coordinator.async_config_entry_first_refresh = AsyncMock(
            side_effect=Exception("Connection timeout")
        )

        with (
            patch("custom_components.ppc_smgw.PPC_SMGW", return_value=mock_gateway),
            patch("custom_components.ppc_smgw.create_async_httpx_client"),
            patch(
                "custom_components.ppc_smgw.async_get_loaded_integration",
                return_value=mock_integration,
            ),
            patch(
                "custom_components.ppc_smgw.SMGwDataUpdateCoordinator",
                return_value=mock_coordinator,
            ),
        ):
            # Setup should raise ConfigEntryNotReady, enabling HA's automatic retry
            with pytest.raises(ConfigEntryNotReady) as exc_info:
                await async_setup_entry(hass, entry)

            # Verify the error message contains the host
            assert ppc_config_data["host"] in str(exc_info.value)

    async def test_setup_entry_uses_configured_scan_interval(
        self, hass: HomeAssistant, mock_gateway
    ):
        """Regression test for issue #94: coordinator must use the configured scan interval."""
        custom_interval = 42
        config_data = {
            CONF_METER_TYPE: Vendor.PPC,
            CONF_HOST: "https://192.168.1.1",
            CONF_USERNAME: "u",
            CONF_PASSWORD: "p",
            CONF_SCAN_INTERVAL: custom_interval,
        }
        entry = create_mock_config_entry(data=config_data)

        mock_integration = MagicMock()
        mock_integration.domain = DOMAIN
        mock_coordinator = MagicMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()

        coordinator_cls = MagicMock(return_value=mock_coordinator)

        with (
            patch("custom_components.ppc_smgw.PPC_SMGW", return_value=mock_gateway),
            patch("custom_components.ppc_smgw.create_async_httpx_client"),
            patch(
                "custom_components.ppc_smgw.async_get_loaded_integration",
                return_value=mock_integration,
            ),
            patch.object(hass.config_entries, "async_forward_entry_setups"),
            patch(
                "custom_components.ppc_smgw.SMGwDataUpdateCoordinator",
                coordinator_cls,
            ),
        ):
            await async_setup_entry(hass, entry)

        coordinator_cls.assert_called_once_with(
            hass=hass,
            update_interval=timedelta(minutes=custom_interval),
        )

    async def test_setup_entry_options_override_data_scan_interval(
        self, hass: HomeAssistant, mock_gateway
    ):
        """Regression test: entry.options scan_interval must take precedence over entry.data."""
        data_interval = 5
        options_interval = 99
        config_data = {
            CONF_METER_TYPE: Vendor.PPC,
            CONF_HOST: "https://192.168.1.1",
            CONF_USERNAME: "u",
            CONF_PASSWORD: "p",
            CONF_SCAN_INTERVAL: data_interval,
        }
        entry = create_mock_config_entry(
            data=config_data,
            options={CONF_SCAN_INTERVAL: options_interval},
        )

        mock_integration = MagicMock()
        mock_integration.domain = DOMAIN
        mock_coordinator = MagicMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()

        coordinator_cls = MagicMock(return_value=mock_coordinator)

        with (
            patch("custom_components.ppc_smgw.PPC_SMGW", return_value=mock_gateway),
            patch("custom_components.ppc_smgw.create_async_httpx_client"),
            patch(
                "custom_components.ppc_smgw.async_get_loaded_integration",
                return_value=mock_integration,
            ),
            patch.object(hass.config_entries, "async_forward_entry_setups"),
            patch(
                "custom_components.ppc_smgw.SMGwDataUpdateCoordinator",
                coordinator_cls,
            ),
        ):
            await async_setup_entry(hass, entry)

        coordinator_cls.assert_called_once_with(
            hass=hass,
            update_interval=timedelta(minutes=options_interval),
        )



@pytest.mark.asyncio
class TestCoordinator:
    """Test the data update coordinator."""

    async def test_coordinator_fetches_data(
        self, hass: HomeAssistant, ppc_config_data, mock_gateway
    ):
        """Test that coordinator successfully fetches data from gateway."""

        # Create realistic mock data
        mock_data = Information(
            name="Test Gateway",
            model="Test Model",
            manufacturer="Test Manufacturer",
            firmware_version="1.0.0",
            last_update=datetime(2024, 1, 1, 12, 0, 0, tzinfo=pytz.UTC),
            readings={
                "1-0:1.8.0": Reading(
                    value="1234.56",
                    timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=pytz.UTC),
                    obis="1-0:1.8.0",
                ),
            },
        )
        mock_gateway.get_data.return_value = mock_data

        coordinator = SMGwDataUpdateCoordinator(
            hass=hass, update_interval=timedelta(minutes=5)
        )
        entry = create_mock_config_entry(data=ppc_config_data)
        entry.runtime_data = Data(
            client=mock_gateway,
            coordinator=coordinator,
            integration=MagicMock(),
        )
        coordinator.config_entry = entry

        # Test: coordinator returns the data from gateway
        result = await coordinator._async_update_data()
        assert result == mock_data

    async def test_coordinator_propagates_errors(
        self, hass: HomeAssistant, ppc_config_data, mock_gateway
    ):
        """Test that coordinator propagates errors from gateway."""

        mock_gateway.get_data.side_effect = Exception("Connection error")

        coordinator = SMGwDataUpdateCoordinator(
            hass=hass, update_interval=timedelta(minutes=5)
        )
        entry = create_mock_config_entry(data=ppc_config_data)
        entry.runtime_data = Data(
            client=mock_gateway,
            coordinator=coordinator,
            integration=MagicMock(),
        )
        coordinator.config_entry = entry

        # Test: errors are propagated, not swallowed
        with pytest.raises(Exception, match="Connection error"):
            await coordinator._async_update_data()

    async def test_coordinator_returns_none_for_invalid_data_type(
        self, hass: HomeAssistant, ppc_config_data, mock_gateway
    ):
        """Test that coordinator returns None when gateway returns invalid type (issue #75)."""

        # Gateway returns invalid type (dict instead of Information)
        mock_gateway.get_data.return_value = {"invalid": "dict"}

        coordinator = SMGwDataUpdateCoordinator(
            hass=hass, update_interval=timedelta(minutes=5)
        )
        entry = create_mock_config_entry(data=ppc_config_data)
        entry.runtime_data = Data(
            client=mock_gateway,
            coordinator=coordinator,
            integration=MagicMock(),
        )
        coordinator.config_entry = entry

        # Test: coordinator validates and returns None instead of invalid data
        result = await coordinator._async_update_data()
        assert result is None

    async def test_coordinator_returns_none_when_gateway_returns_none(
        self, hass: HomeAssistant, ppc_config_data, mock_gateway
    ):
        """Test that coordinator handles None from gateway (legitimate case)."""
        # Gateway legitimately returns None (e.g. no data available yet)
        mock_gateway.get_data.return_value = None

        coordinator = SMGwDataUpdateCoordinator(
            hass=hass, update_interval=timedelta(minutes=5)
        )
        entry = create_mock_config_entry(data=ppc_config_data)
        entry.runtime_data = Data(
            client=mock_gateway,
            coordinator=coordinator,
            integration=MagicMock(),
        )
        coordinator.config_entry = entry

        # Test: coordinator returns None without raising
        result = await coordinator._async_update_data()
        assert result is None
