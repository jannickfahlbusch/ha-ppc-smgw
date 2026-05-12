"""Tests for the PPC SMGW sensor platform."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.ppc_smgw.sensor import (
    OBISSensor,
    LastUpdatedSensor,
    async_setup_entry,
    build_entity_description,
    _migrate_sensor_unique_ids,
)
from custom_components.ppc_smgw.const import (
    LastUpdatedSensorDescription,
)
from custom_components.ppc_smgw.gateways.reading import Information, Reading
from custom_components.ppc_smgw.coordinator import Data
from tests.conftest import create_mock_config_entry


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
        last_update=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        readings={
            "1-0:1.8.0": Reading(
                value="1234.5",
                timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                obis="1-0:1.8.0",
            ),
            "1-0:2.8.0": Reading(
                value="567.8",
                timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                obis="1-0:2.8.0",
            ),
        },
    )


@pytest.mark.asyncio
class TestSensorPlatformSetup:
    """Test the sensor platform setup."""

    async def test_async_setup_entry_creates_entities_from_data(
        self, hass: HomeAssistant, ppc_config_data, valid_information
    ):
        """Test that async_setup_entry creates entities from coordinator data."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = valid_information
        mock_coordinator.async_add_listener = MagicMock(return_value=lambda: None)
        mock_add_entities = MagicMock()

        entry = create_mock_config_entry(data=ppc_config_data)
        entry.runtime_data = Data(
            client=MagicMock(),
            coordinator=mock_coordinator,
            integration=MagicMock(),
        )
        entry.async_on_unload = MagicMock()

        await async_setup_entry(hass, entry, mock_add_entities)

        # Should be called twice: once for OBIS sensors, once for LastUpdatedSensor
        assert mock_add_entities.call_count == 2

        # First call: OBIS sensors from coordinator data
        obis_entities = mock_add_entities.call_args_list[0][0][0]
        assert len(obis_entities) == 2  # Two readings in valid_information
        assert all(isinstance(e, OBISSensor) for e in obis_entities)

        # Second call: LastUpdatedSensor
        last_update_entities = mock_add_entities.call_args_list[1][0][0]
        assert len(last_update_entities) == 1
        assert isinstance(last_update_entities[0], LastUpdatedSensor)

    async def test_async_setup_entry_no_obis_entities_when_no_data(
        self, hass: HomeAssistant, ppc_config_data
    ):
        """Test that no OBIS entities are created when coordinator data is None."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = None
        mock_coordinator.async_add_listener = MagicMock(return_value=lambda: None)
        mock_add_entities = MagicMock()

        entry = create_mock_config_entry(data=ppc_config_data)
        entry.runtime_data = Data(
            client=MagicMock(),
            coordinator=mock_coordinator,
            integration=MagicMock(),
        )
        entry.async_on_unload = MagicMock()

        await async_setup_entry(hass, entry, mock_add_entities)

        # Only the LastUpdatedSensor should be added
        assert mock_add_entities.call_count == 1
        entities = mock_add_entities.call_args_list[0][0][0]
        assert len(entities) == 1
        assert isinstance(entities[0], LastUpdatedSensor)

    async def test_async_setup_entry_uses_coordinator(
        self, hass: HomeAssistant, ppc_config_data, valid_information
    ):
        """Test that created entities use the coordinator from runtime_data."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = valid_information
        mock_coordinator.async_add_listener = MagicMock(return_value=lambda: None)
        mock_add_entities = MagicMock()

        entry = create_mock_config_entry(data=ppc_config_data)
        entry.runtime_data = Data(
            client=MagicMock(),
            coordinator=mock_coordinator,
            integration=MagicMock(),
        )
        entry.async_on_unload = MagicMock()

        await async_setup_entry(hass, entry, mock_add_entities)

        # All OBIS entities should use the same coordinator
        obis_entities = mock_add_entities.call_args_list[0][0][0]
        for entity in obis_entities:
            assert entity.coordinator is mock_coordinator

    async def test_registers_coordinator_listener(
        self, hass: HomeAssistant, ppc_config_data, valid_information
    ):
        """Test that a coordinator listener is registered for future discovery."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = valid_information
        unsub = MagicMock()
        mock_coordinator.async_add_listener = MagicMock(return_value=unsub)
        mock_add_entities = MagicMock()

        entry = create_mock_config_entry(data=ppc_config_data)
        entry.runtime_data = Data(
            client=MagicMock(),
            coordinator=mock_coordinator,
            integration=MagicMock(),
        )
        entry.async_on_unload = MagicMock()

        await async_setup_entry(hass, entry, mock_add_entities)

        # Listener should be registered
        mock_coordinator.async_add_listener.assert_called_once()
        # Unsubscribe should be passed to async_on_unload
        entry.async_on_unload.assert_called_with(unsub)


class TestOBISSensor:
    """Test the OBISSensor class."""

    def test_returns_none_when_data_invalid(self, mock_coordinator):
        """Test that sensor returns None when coordinator data is not Information."""
        mock_coordinator.data = None

        entity_description = SensorEntityDescription(
            key="1-0:1.8.0",
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
            key="1-0:1.8.0",
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
            key="1-0:99.99.0",
            name="Test Missing",
        )

        sensor = OBISSensor(
            coordinator=mock_coordinator,
            entity_description=entity_description,
        )

        assert sensor.native_value is None

    def test_unique_id_has_no_platform_prefix(self, mock_coordinator):
        """Test that unique_id does not contain sensor. prefix."""
        entity_description = SensorEntityDescription(
            key="1-0:1.8.0",
            name="Test",
        )
        sensor = OBISSensor(
            coordinator=mock_coordinator,
            entity_description=entity_description,
        )
        assert not sensor.unique_id.startswith("sensor.")


class TestBuildEntityDescription:
    """Test the build_entity_description function."""

    def test_known_import_energy(self):
        desc = build_entity_description("1-0:1.8.0")
        assert desc.key == "1-0:1.8.0"
        assert desc.name == "Active import energy"
        assert desc.entity_registry_enabled_default is True

    def test_known_export_energy(self):
        desc = build_entity_description("1-0:2.8.0")
        assert desc.key == "1-0:2.8.0"
        assert desc.name == "Active export energy"

    def test_known_active_power(self):
        desc = build_entity_description("1-0:16.7.0")
        assert desc.key == "1-0:16.7.0"
        assert desc.name == "Total active power"

    def test_unknown_obis_code_disabled_by_default(self):
        desc = build_entity_description("1-0:99.99.0")
        assert desc.entity_registry_enabled_default is False
        assert desc.name == "OBIS 1-0:99.99.0"

    def test_unparseable_obis_code(self):
        desc = build_entity_description("garbage")
        assert desc.entity_registry_enabled_default is False
        assert desc.name == "OBIS garbage"

    def test_channel_in_name(self):
        desc = build_entity_description("1-1:1.8.0")
        assert "Ch 1" in desc.name

    def test_tariff_in_name(self):
        desc = build_entity_description("1-0:1.8.2")
        assert "Tariff 2" in desc.name


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


class TestMigrateSensorUniqueIds:
    """Test the _migrate_sensor_unique_ids function."""

    def _make_entity_entry(self, entity_id, unique_id):
        entry = MagicMock()
        entry.entity_id = entity_id
        entry.unique_id = unique_id
        return entry

    def test_strips_sensor_prefix(self):
        ent_reg = MagicMock(spec=er.EntityRegistry)
        entry = self._make_entity_entry("sensor.test_abc", "sensor.abc_123")

        with patch.object(er, "async_entries_for_config_entry", return_value=[entry]):
            _migrate_sensor_unique_ids(ent_reg, "test_entry")

        ent_reg.async_update_entity.assert_called_once_with(
            "sensor.test_abc", new_unique_id="abc_123"
        )

    def test_leaves_non_prefixed_alone(self):
        ent_reg = MagicMock(spec=er.EntityRegistry)
        entry = self._make_entity_entry("sensor.test_abc", "abc_123")

        with patch.object(er, "async_entries_for_config_entry", return_value=[entry]):
            _migrate_sensor_unique_ids(ent_reg, "test_entry")

        ent_reg.async_update_entity.assert_not_called()

    def test_ignores_button_prefix(self):
        """sensor.py migration should not touch button. prefixed entities."""
        ent_reg = MagicMock(spec=er.EntityRegistry)
        entry = self._make_entity_entry("button.test_restart", "button.abc_restart")

        with patch.object(er, "async_entries_for_config_entry", return_value=[entry]):
            _migrate_sensor_unique_ids(ent_reg, "test_entry")

        ent_reg.async_update_entity.assert_not_called()

    def test_handles_collision_gracefully(self):
        """If target unique_id already exists, migration should not crash."""
        ent_reg = MagicMock(spec=er.EntityRegistry)
        ent_reg.async_update_entity.side_effect = ValueError("unique_id already exists")
        entry = self._make_entity_entry("sensor.test_abc", "sensor.abc_123")

        with patch.object(er, "async_entries_for_config_entry", return_value=[entry]):
            # Should not raise
            _migrate_sensor_unique_ids(ent_reg, "test_entry")

        ent_reg.async_update_entity.assert_called_once()
