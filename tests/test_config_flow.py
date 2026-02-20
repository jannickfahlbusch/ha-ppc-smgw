"""Tests for the PPC SMGW config flow - simplified version."""

from unittest.mock import patch

import pytest
from homeassistant.const import CONF_HOST
from homeassistant.const import (
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_DEBUG,
)
from homeassistant.const import CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ppc_smgw.config_flow import (
    PPCSMGWLocalOptionsFlowHandler,
)
from custom_components.ppc_smgw.config_flow import PPC_SMGLocalConfigFlow
from custom_components.ppc_smgw.const import CONF_METER_TYPE
from custom_components.ppc_smgw.gateways.vendors import Vendor
from tests.conftest import create_mock_config_entry


@pytest.mark.asyncio
class TestConfigFlow:
    """Test the config flow for PPC SMGW integration."""

    async def test_user_flow_shows_vendor_selection(self, hass: HomeAssistant):
        """Test that the initial flow shows vendor selection."""
        flow = PPC_SMGLocalConfigFlow()
        flow.hass = hass

        result = await flow.async_step_user(user_input=None)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        assert CONF_METER_TYPE in result["data_schema"].schema

    async def test_user_flow_progresses_to_connection_info(
        self, hass: HomeAssistant, vendor
    ):
        """Test that selecting a vendor progresses to connection info (parametrized)."""
        flow = PPC_SMGLocalConfigFlow()
        flow.hass = hass

        result = await flow.async_step_user(user_input={CONF_METER_TYPE: vendor})

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "connection_info"

    async def test_connection_info_creates_entry(
        self, hass: HomeAssistant, vendor, vendor_config_data, vendor_expected_name
    ):
        """Test that valid connection info creates entry (parametrized for all vendors)."""
        flow = PPC_SMGLocalConfigFlow()
        flow.hass = hass
        flow.data = {CONF_METER_TYPE: vendor}

        user_input = {
            k: vendor_config_data[k]
            for k in [
                CONF_NAME,
                CONF_HOST,
                CONF_USERNAME,
                CONF_PASSWORD,
                CONF_SCAN_INTERVAL,
            ]
        }
        if CONF_DEBUG in vendor_config_data:
            user_input[CONF_DEBUG] = vendor_config_data[CONF_DEBUG]

        with patch.object(flow, "_test_connection", return_value=True):
            result = await flow.async_step_connection_info(user_input=user_input)

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == vendor_expected_name

    async def test_duplicate_host_username_rejected(
        self, hass: HomeAssistant, ppc_config_data
    ):
        """Test that duplicate host/username combinations are rejected."""

        flow = PPC_SMGLocalConfigFlow()
        flow.hass = hass
        flow.data = {CONF_METER_TYPE: Vendor.PPC}

        with patch(
            "custom_components.ppc_smgw.config_flow._host_username_combination_exists",
            return_value=True,
        ):
            result = await flow.async_step_connection_info(
                user_input={
                    k: ppc_config_data[k]
                    for k in [
                        "name",
                        CONF_HOST,
                        CONF_USERNAME,
                        "password",
                        "scan_interval",
                        "debug",
                    ]
                }
            )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {CONF_HOST: "already_configured"}

    async def test_connection_failure_shows_form_again(
        self, hass: HomeAssistant, ppc_config_data
    ):
        """Test that connection failure shows the form again."""

        flow = PPC_SMGLocalConfigFlow()
        flow.hass = hass
        flow.data = {CONF_METER_TYPE: Vendor.PPC}

        with patch.object(flow, "_test_connection", return_value=False):
            result = await flow.async_step_connection_info(
                user_input={
                    k: ppc_config_data[k]
                    for k in [
                        "name",
                        "host",
                        "username",
                        "password",
                        "scan_interval",
                        "debug",
                    ]
                }
            )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "connection_info"


@pytest.mark.asyncio
class TestOptionsFlow:
    """Test the options flow for PPC SMGW integration."""

    async def test_options_flow_updates_config(
        self, hass: HomeAssistant, ppc_config_data
    ):
        """Test that options flow successfully updates configuration."""

        entry = create_mock_config_entry(data=ppc_config_data)
        options_flow = PPCSMGWLocalOptionsFlowHandler(entry)
        options_flow.hass = hass

        # Update scan interval and debug
        result = await options_flow.async_step_user(
            user_input={
                k: ppc_config_data[k] for k in ["name", "host", "username", "password"]
            }
            | {"scan_interval": 10, "debug": True}
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"]["scan_interval"] == 10
        assert result["data"]["debug"] is True

    async def test_options_flow_rejects_duplicate_host_change(
        self, hass: HomeAssistant, ppc_config_data
    ):
        """Test that changing to duplicate host/username is rejected."""

        entry = create_mock_config_entry(data=ppc_config_data)
        options_flow = PPCSMGWLocalOptionsFlowHandler(entry)
        options_flow.hass = hass

        with patch(
            "custom_components.ppc_smgw.config_flow._host_username_combination_exists",
            return_value=True,
        ):
            result = await options_flow.async_step_user(
                user_input={
                    k: ppc_config_data[k]
                    for k in ["name", "username", "password", "scan_interval", "debug"]
                }
                | {CONF_HOST: "https://192.168.1.201/cgi-bin/hanservice.cgi"}
            )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {CONF_HOST: "already_configured"}
