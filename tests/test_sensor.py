"""Tests for the PPC SMGW sensor platform."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.core import HomeAssistant

from custom_components.ppc_smgw.sensor import (
    OBISSensor,
    LastUpdatedSensor,
    async_setup_entry,
)
from custom_components.ppc_smgw.const import (
    SENSOR_TYPES,
    LastUpdatedSensorDescription,
)
from custom_components.ppc_smgw.gateways.reading import Information, Reading
from custom_components.ppc_smgw.coordinator import Data
from tests.conftest import create_mock_config_entry
import pytz


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.data = None
    return coordinator


@pytest.fixture
def valid_information():
    """Create a real Information object with sample readings."""
    return Information(
        name="Test Gateway",
        model="Test Model",
        manufacturer="Test Manufacturer",
        firmware_version="1.0.0",
        last_update=datetime(2024, 1, 1, 12, 0, 0, tzinfo=pytz.UTC),
        readings={
            "1-0:1.8.0*255": Reading(
                value="1234.5",
                timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=pytz.UTC),
                obis="1-0:1.8.0*255",
            ),
            "1-0:2.8.0*255": Reading(
                value="567.8",
                timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=pytz.UTC),
                obis="1-0:2.8.0*255",
            ),
        },
    )


@pytest.mark.asyncio
class TestSensorPlatformSetup:
    """Test the sensor platform setup."""

    async def test_async_setup_entry_creates_entities(
        self, hass: HomeAssistant, ppc_config_data
    ):
        """Test that async_setup_entry creates the correct number of entities."""
        mock_coordinator = MagicMock()
        mock_add_entities = MagicMock()

        entry = create_mock_config_entry(data=ppc_config_data)
        entry.runtime_data = Data(
            client=MagicMock(),
            coordinator=mock_coordinator,
            integration=MagicMock(),
        )

        await async_setup_entry(hass, entry, mock_add_entities)

        # Should create len(SENSOR_TYPES) + 1 (LastUpdatedSensor)
        expected_count = len(SENSOR_TYPES) + 1
        mock_add_entities.assert_called_once()

        # Get the entities list that was passed
        entities_list = mock_add_entities.call_args[0][0]
        assert len(entities_list) == expected_count

        # Verify entity types
        obis_sensors = [e for e in entities_list if isinstance(e, OBISSensor)]
        last_update_sensors = [
            e for e in entities_list if isinstance(e, LastUpdatedSensor)
        ]

        assert len(obis_sensors) == len(SENSOR_TYPES)
        assert len(last_update_sensors) == 1

    async def test_async_setup_entry_uses_coordinator(
        self, hass: HomeAssistant, ppc_config_data
    ):
        """Test that created entities use the coordinator from runtime_data."""
        mock_coordinator = MagicMock()
        mock_add_entities = MagicMock()

        entry = create_mock_config_entry(data=ppc_config_data)
        entry.runtime_data = Data(
            client=MagicMock(),
            coordinator=mock_coordinator,
            integration=MagicMock(),
        )

        await async_setup_entry(hass, entry, mock_add_entities)

        entities_list = mock_add_entities.call_args[0][0]

        # All entities should use the same coordinator
        for entity in entities_list:
            assert entity.coordinator is mock_coordinator


class TestOBISSensor:
    """Test the OBISSensor class."""

    def test_returns_none_when_data_invalid(self, mock_coordinator):
        """Test that sensor returns None when coordinator data is not Information (issue #75)."""
        mock_coordinator.data = None

        entity_description = SensorEntityDescription(
            key="1-0:1.8.0*255",
            name="Test Energy",
        )

        sensor = OBISSensor(
            coordinator=mock_coordinator,
            entity_description=entity_description,
        )

        assert sensor.native_value is None

    def test_returns_correct_value_with_valid_data(
        self, mock_coordinator, valid_information
    ):
        """Test that sensor returns correct value when data is valid."""
        mock_coordinator.data = valid_information

        entity_description = SensorEntityDescription(
            key="1-0:1.8.0*255",
            name="Test Energy",
        )

        sensor = OBISSensor(
            coordinator=mock_coordinator,
            entity_description=entity_description,
        )

        assert sensor.native_value == "1234.5"

    def test_returns_none_when_obis_key_missing(
        self, mock_coordinator, valid_information
    ):
        """Test that sensor returns None when OBIS key is not in readings."""
        mock_coordinator.data = valid_information

        entity_description = SensorEntityDescription(
            key="1-0:99.99.99*255",
            name="Test Missing",
        )

        sensor = OBISSensor(
            coordinator=mock_coordinator,
            entity_description=entity_description,
        )

        assert sensor.native_value is None


class TestLastUpdatedSensor:
    """Test the LastUpdatedSensor class."""

    def test_returns_none_when_data_invalid(self, mock_coordinator):
        """Test that LastUpdatedSensor returns None when coordinator data is not Information."""
        mock_coordinator.data = None
        sensor = LastUpdatedSensor(
            coordinator=mock_coordinator,
            entity_description=LastUpdatedSensorDescription,
        )

        assert sensor.native_value is None

    def test_returns_last_update_with_valid_data(
        self, mock_coordinator, valid_information
    ):
        """Test that LastUpdatedSensor returns last_update when data is valid."""
        mock_coordinator.data = valid_information
        sensor = LastUpdatedSensor(
            coordinator=mock_coordinator,
            entity_description=LastUpdatedSensorDescription,
        )

        assert sensor.native_value == valid_information.last_update
