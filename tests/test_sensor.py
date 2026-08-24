from dataclasses import replace
from datetime import UTC, datetime
import json
from pathlib import Path
import re
from unittest.mock import MagicMock

from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from obis_parser import OBIS, OBIS_CATALOG
import pytest

from custom_components.ppc_smgw import sensor as sensor_module
from custom_components.ppc_smgw.const import (
    SENSOR_TYPES,
    FirmwareVersionSensorDescription,
    LastUpdatedSensorDescription,
)
from custom_components.ppc_smgw.coordinator import Data
from custom_components.ppc_smgw.gateways.reading import Information, Reading
from custom_components.ppc_smgw.obis_ha import OBISSensorSpec
from custom_components.ppc_smgw.sensor import (
    FirmwareSensor,
    LastUpdatedSensor,
    OBISSensor,
    async_setup_entry,
)
from tests.conftest import create_mock_config_entry


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.data = None
    coordinator.async_add_listener = MagicMock(return_value=MagicMock())
    return coordinator


def _reading(value: str | float, obis: str | OBIS) -> Reading:
    if isinstance(obis, str):
        obis = OBIS.parse(obis)
    return Reading(
        value=value,
        timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        obis=obis,
    )


def _information(readings: dict) -> Information:
    norm_readings: dict[OBIS, Reading] = {}
    for k, v in readings.items():
        if isinstance(k, str):
            norm_readings[OBIS.parse(k)] = v
        else:
            norm_readings[k] = v
    return Information(
        name="Test Gateway",
        model="Test Model",
        manufacturer="Test Manufacturer",
        firmware_version="1.0.0",
        last_update=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        readings=norm_readings,
    )


def _entry_with_runtime_data(ppc_config_data, coordinator, client):
    entry = create_mock_config_entry(data=ppc_config_data)
    entry.async_on_unload = MagicMock()
    coordinator.config_entry = entry
    entry.runtime_data = Data(
        client=client,
        coordinator=coordinator,
        integration=MagicMock(),
    )
    return entry


class _FakeEntityRegistry:
    def __init__(self, entity_ids_by_unique_id: dict[str, str | None]) -> None:
        self.entity_ids_by_unique_id = entity_ids_by_unique_id
        self.looked_up_unique_ids: list[str] = []
        self.removed_entities: list[str] = []

    def async_get_entity_id(self, domain, platform, unique_id):
        self.looked_up_unique_ids.append(unique_id)
        assert domain == "sensor"
        assert platform == "ppc_smgw"
        return self.entity_ids_by_unique_id.get(unique_id)

    def async_remove(self, entity_id):
        self.removed_entities.append(entity_id)


@pytest.fixture
def valid_information():
    """Create a real Information object with sample readings."""
    return Information(
        name="Test Gateway",
        model="Test Model",
        manufacturer="Test Manufacturer",
        firmware_version="1.0.0",
        last_update=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        readings={
            OBIS(1, 0, 1, 8, 0): Reading(
                value="1234.5",
                timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
                obis=OBIS(1, 0, 1, 8, 0),
            ),
            OBIS(1, 0, 2, 8, 0): Reading(
                value="567.8",
                timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
                obis=OBIS(1, 0, 2, 8, 0),
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
        mock_coordinator.async_add_listener = MagicMock()
        mock_add_entities = MagicMock()

        entry = _entry_with_runtime_data(ppc_config_data, mock_coordinator, MagicMock())

        await async_setup_entry(hass, entry, mock_add_entities)

        # Should create len(SENSOR_TYPES) + 1 (LastUpdatedSensor) + 1 (FirmwareSensor)
        expected_count = len(SENSOR_TYPES) + 2
        mock_add_entities.assert_called_once()

        # Get the entities list that was passed
        entities_list = mock_add_entities.call_args[0][0]
        assert len(entities_list) == expected_count

        # Verify entity types
        obis_sensors = [e for e in entities_list if isinstance(e, OBISSensor)]
        last_update_sensors = [
            e for e in entities_list if isinstance(e, LastUpdatedSensor)
        ]
        firmware_sensors = [e for e in entities_list if isinstance(e, FirmwareSensor)]

        assert len(obis_sensors) == len(SENSOR_TYPES)
        assert len(last_update_sensors) == 1
        assert len(firmware_sensors) == 1
        mock_coordinator.async_add_listener.assert_not_called()

    async def test_async_setup_entry_uses_coordinator(
        self, hass: HomeAssistant, ppc_config_data
    ):
        """Test that created entities use the coordinator from runtime_data."""
        mock_coordinator = MagicMock()
        mock_add_entities = MagicMock()

        entry = _entry_with_runtime_data(ppc_config_data, mock_coordinator, MagicMock())

        await async_setup_entry(hass, entry, mock_add_entities)

        entities_list = mock_add_entities.call_args[0][0]

        # All entities should use the same coordinator
        for entity in entities_list:
            assert entity.coordinator is mock_coordinator

    async def test_magicmock_rollout_flag_keeps_static_path(
        self, hass: HomeAssistant, ppc_config_data
    ):
        """A truthy MagicMock attribute must not accidentally enable discovery."""
        mock_coordinator = MagicMock()
        mock_coordinator.async_add_listener = MagicMock()
        mock_add_entities = MagicMock()

        entry = _entry_with_runtime_data(ppc_config_data, mock_coordinator, MagicMock())

        await async_setup_entry(hass, entry, mock_add_entities)

        entities_list = mock_add_entities.call_args[0][0]
        assert len(entities_list) == len(SENSOR_TYPES) + 2
        mock_coordinator.async_add_listener.assert_not_called()

    async def test_false_rollout_flag_keeps_static_path(
        self, hass: HomeAssistant, ppc_config_data
    ):
        """dynamic_obis_discovery_enabled=False keeps existing static sensors."""
        mock_coordinator = MagicMock()
        mock_coordinator.async_add_listener = MagicMock()
        mock_add_entities = MagicMock()
        client = MagicMock()
        client.dynamic_obis_discovery_enabled = False

        entry = _entry_with_runtime_data(ppc_config_data, mock_coordinator, client)

        await async_setup_entry(hass, entry, mock_add_entities)

        entities_list = mock_add_entities.call_args[0][0]
        assert len(entities_list) == len(SENSOR_TYPES) + 2
        mock_coordinator.async_add_listener.assert_not_called()

    async def test_dynamic_path_creates_only_delivered_obis_sensors(
        self, hass: HomeAssistant, ppc_config_data
    ):
        """Dynamic discovery starts from delivered readings, not SENSOR_TYPES."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = _information(
            {"1-0:1.8.0": _reading("1234.5", "1-0:1.8.0")}
        )
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_add_entities = MagicMock()
        client = MagicMock()
        client.dynamic_obis_discovery_enabled = True

        entry = _entry_with_runtime_data(ppc_config_data, mock_coordinator, client)

        await async_setup_entry(hass, entry, mock_add_entities)

        entities_list = mock_add_entities.call_args[0][0]
        obis_sensors = [e for e in entities_list if isinstance(e, OBISSensor)]
        last_update_sensors = [
            e for e in entities_list if isinstance(e, LastUpdatedSensor)
        ]

        assert [sensor.entity_description.key for sensor in obis_sensors] == [
            "1-0:1.8.0"
        ]
        assert len(last_update_sensors) == 1
        assert obis_sensors[0]._attr_translation_key == "active_energy_import"
        mock_coordinator.async_add_listener.assert_called_once()
        entry.async_on_unload.assert_called_once()

    async def test_dynamic_path_removes_stale_static_obis_entities(
        self, hass: HomeAssistant, ppc_config_data, monkeypatch: pytest.MonkeyPatch
    ):
        """Static import/export entities absent from dynamic readings are cleaned up."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = _information(
            {"1-0:1.8.0": _reading("1234.5", "1-0:1.8.0")}
        )
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_add_entities = MagicMock()
        client = MagicMock()
        client.dynamic_obis_discovery_enabled = True
        registry = _FakeEntityRegistry(
            {"sensor.test_entry_id_1_0_2_8_0": "sensor.export_total"}
        )

        monkeypatch.setattr(
            sensor_module.er, "async_get", MagicMock(return_value=registry)
        )
        entry = _entry_with_runtime_data(ppc_config_data, mock_coordinator, client)

        await async_setup_entry(hass, entry, mock_add_entities)

        assert registry.looked_up_unique_ids == ["sensor.test_entry_id_1_0_2_8_0"]
        assert registry.removed_entities == ["sensor.export_total"]

    async def test_dynamic_path_skips_stale_cleanup_without_initial_readings(
        self, hass: HomeAssistant, ppc_config_data, monkeypatch: pytest.MonkeyPatch
    ):
        """Empty first refresh is not enough evidence to delete registry entries."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = _information({})
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_add_entities = MagicMock()
        client = MagicMock()
        client.dynamic_obis_discovery_enabled = True
        registry = _FakeEntityRegistry(
            {
                "sensor.test_entry_id_1_0_1_8_0": "sensor.import_total",
                "sensor.test_entry_id_1_0_2_8_0": "sensor.export_total",
            }
        )

        monkeypatch.setattr(
            sensor_module.er, "async_get", MagicMock(return_value=registry)
        )
        entry = _entry_with_runtime_data(ppc_config_data, mock_coordinator, client)

        await async_setup_entry(hass, entry, mock_add_entities)

        assert registry.looked_up_unique_ids == []
        assert registry.removed_entities == []

    async def test_dynamic_path_skips_stale_cleanup_for_invalid_data(
        self, hass: HomeAssistant, ppc_config_data, monkeypatch: pytest.MonkeyPatch
    ):
        """Invalid coordinator data must not trigger registry cleanup."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = None
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_add_entities = MagicMock()
        client = MagicMock()
        client.dynamic_obis_discovery_enabled = True
        registry = _FakeEntityRegistry(
            {
                "sensor.test_entry_id_1_0_1_8_0": "sensor.import_total",
                "sensor.test_entry_id_1_0_2_8_0": "sensor.export_total",
            }
        )

        monkeypatch.setattr(
            sensor_module.er, "async_get", MagicMock(return_value=registry)
        )
        entry = _entry_with_runtime_data(ppc_config_data, mock_coordinator, client)

        await async_setup_entry(hass, entry, mock_add_entities)

        assert registry.looked_up_unique_ids == []
        assert registry.removed_entities == []

    async def test_non_electricity_code_is_skipped(
        self, hass: HomeAssistant, ppc_config_data
    ):
        """Non-electricity mediums (A != 1) create no sensor; electricity does."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = _information(
            {
                "1-0:1.8.0": _reading("1234.5", "1-0:1.8.0"),
                "7-0:3.0.0": _reading("42", "7-0:3.0.0"),  # gas — must be skipped
            }
        )
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_add_entities = MagicMock()
        client = MagicMock()
        client.dynamic_obis_discovery_enabled = True

        entry = _entry_with_runtime_data(ppc_config_data, mock_coordinator, client)

        await async_setup_entry(hass, entry, mock_add_entities)

        obis_sensors = [
            e for e in mock_add_entities.call_args[0][0] if isinstance(e, OBISSensor)
        ]
        assert [s.entity_description.key for s in obis_sensors] == ["1-0:1.8.0"]

    async def test_unknown_electricity_code_registers_generic(
        self, hass: HomeAssistant, ppc_config_data
    ):
        """An A=1 code with no catalog entry becomes a generic diagnostic sensor."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = _information(
            {"1-0:99.99.99": _reading("7", "1-0:99.99.99")}
        )
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_add_entities = MagicMock()
        client = MagicMock()
        client.dynamic_obis_discovery_enabled = True

        entry = _entry_with_runtime_data(ppc_config_data, mock_coordinator, client)

        await async_setup_entry(hass, entry, mock_add_entities)

        obis_sensors = [
            e for e in mock_add_entities.call_args[0][0] if isinstance(e, OBISSensor)
        ]
        assert len(obis_sensors) == 1
        assert obis_sensors[0]._attr_translation_key == "unknown_code"

    async def test_dynamic_path_adds_later_obis_codes_via_listener(
        self, hass: HomeAssistant, ppc_config_data
    ):
        """Dynamic listener adds OBIS sensors that appear after setup."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = _information({})
        unsubscribe = MagicMock()
        mock_coordinator.async_add_listener = MagicMock(return_value=unsubscribe)
        mock_add_entities = MagicMock()
        client = MagicMock()
        client.dynamic_obis_discovery_enabled = True

        entry = _entry_with_runtime_data(ppc_config_data, mock_coordinator, client)

        await async_setup_entry(hass, entry, mock_add_entities)

        initial_entities = mock_add_entities.call_args_list[0][0][0]
        assert [type(entity) for entity in initial_entities] == [
            LastUpdatedSensor,
            FirmwareSensor,
        ]
        entry.async_on_unload.assert_called_once_with(unsubscribe)

        listener = mock_coordinator.async_add_listener.call_args[0][0]
        mock_coordinator.data = _information(
            {"1-0:16.7.0": _reading("42", "1-0:16.7.0")}
        )
        listener()

        added_entities = mock_add_entities.call_args_list[1][0][0]
        assert len(added_entities) == 1
        assert isinstance(added_entities[0], OBISSensor)
        assert added_entities[0].entity_description.key == "1-0:16.7.0"

    async def test_dynamic_path_deduplicates_repeated_obis_codes(
        self, hass: HomeAssistant, ppc_config_data
    ):
        """Repeated OBIS keys must not create duplicate entities."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = _information(
            {"1-0:1.8.0": _reading("1234.5", "1-0:1.8.0")}
        )
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_add_entities = MagicMock()
        client = MagicMock()
        client.dynamic_obis_discovery_enabled = True

        entry = _entry_with_runtime_data(ppc_config_data, mock_coordinator, client)

        await async_setup_entry(hass, entry, mock_add_entities)

        listener = mock_coordinator.async_add_listener.call_args[0][0]
        mock_coordinator.data = _information(
            {"1-0:1.8.0": _reading("1234.6", "1-0:1.8.0")}
        )
        listener()

        assert mock_add_entities.call_count == 1

    async def test_dynamic_path_reads_delivered_canonical_value(
        self, hass: HomeAssistant, ppc_config_data
    ):
        """Canonical entity keys resolve values from delivered readings."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = _information(
            {"1-0:1.8.0": _reading(1234.5, "1-0:1.8.0")}
        )
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_add_entities = MagicMock()
        client = MagicMock()
        client.dynamic_obis_discovery_enabled = True

        entry = _entry_with_runtime_data(ppc_config_data, mock_coordinator, client)

        await async_setup_entry(hass, entry, mock_add_entities)

        obis_sensor = next(
            entity
            for entity in mock_add_entities.call_args[0][0]
            if isinstance(entity, OBISSensor)
        )

        assert obis_sensor.entity_description.key == "1-0:1.8.0"
        assert obis_sensor.native_value == 1234.5

    async def test_existing_import_export_unique_ids_are_preserved(
        self, hass: HomeAssistant, ppc_config_data
    ):
        """Dynamic discovery must keep current import/export entity identity."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = _information(
            {
                "1-0:1.8.0": _reading("1234.5", "1-0:1.8.0"),
                "1-0:2.8.0": _reading("567.8", "1-0:2.8.0"),
            }
        )
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_add_entities = MagicMock()
        client = MagicMock()
        client.dynamic_obis_discovery_enabled = True

        entry = _entry_with_runtime_data(ppc_config_data, mock_coordinator, client)

        await async_setup_entry(hass, entry, mock_add_entities)

        obis_sensors = [
            entity
            for entity in mock_add_entities.call_args[0][0]
            if isinstance(entity, OBISSensor)
        ]

        assert {
            sensor.entity_description.key: sensor._attr_unique_id
            for sensor in obis_sensors
        } == {
            "1-0:1.8.0": "sensor.test_entry_id_1_0_1_8_0",
            "1-0:2.8.0": "sensor.test_entry_id_1_0_2_8_0",
        }
        # In dynamic mode import/export are catalog-resolved (translatable),
        # not the static English SENSOR_TYPES names.
        assert {
            sensor.entity_description.key: sensor._attr_translation_key
            for sensor in obis_sensors
        } == {
            "1-0:1.8.0": "active_energy_import",
            "1-0:2.8.0": "active_energy_export",
        }

    async def test_unknown_obis_codes_are_disabled_diagnostics(
        self, hass: HomeAssistant, ppc_config_data
    ):
        """Unknown delivered OBIS codes are safe, disabled diagnostic entities."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = _information(
            {"1-0:99.99.99": _reading("7", "1-0:99.99.99")}
        )
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_add_entities = MagicMock()
        client = MagicMock()
        client.dynamic_obis_discovery_enabled = True

        entry = _entry_with_runtime_data(ppc_config_data, mock_coordinator, client)

        await async_setup_entry(hass, entry, mock_add_entities)

        obis_sensor = next(
            entity
            for entity in mock_add_entities.call_args[0][0]
            if isinstance(entity, OBISSensor)
        )

        assert obis_sensor._attr_translation_key == "unknown_code"
        assert obis_sensor._attr_translation_placeholders == {"code": "1-0:99.99.99"}
        assert (
            obis_sensor.entity_description.entity_category is EntityCategory.DIAGNOSTIC
        )
        assert obis_sensor.entity_description.entity_registry_enabled_default is False

    async def test_dynamic_entity_sets_translation_key(
        self, hass: HomeAssistant, ppc_config_data
    ):
        """Dynamic entity names come from translation_key, not a hardcoded name."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = _information(
            {"1-0:16.7.0": _reading("42", "1-0:16.7.0")}
        )
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_add_entities = MagicMock()
        client = MagicMock()
        client.dynamic_obis_discovery_enabled = True

        entry = _entry_with_runtime_data(ppc_config_data, mock_coordinator, client)

        await async_setup_entry(hass, entry, mock_add_entities)

        obis_sensor = next(
            entity
            for entity in mock_add_entities.call_args[0][0]
            if isinstance(entity, OBISSensor)
        )

        assert obis_sensor._attr_translation_key == "active_power_total"
        # No qualifiers → no placeholders set (avoids overriding the base default).
        assert getattr(obis_sensor, "_attr_translation_placeholders", None) in (
            None,
            {},
        )
        # _attr_name must NOT be set at all — HA's _name_internal returns
        # self._attr_name first if the attribute exists, suppressing translation.
        assert not hasattr(obis_sensor, "_attr_name")


class TestOBISSensor:
    """Test the OBISSensor class."""

    def test_returns_none_when_data_invalid(self, mock_coordinator):
        """Test that sensor returns None when coordinator data is not Information (issue #75)."""
        mock_coordinator.data = None

        sensor = OBISSensor(
            coordinator=mock_coordinator,
            spec=OBISSensorSpec(
                description=SensorEntityDescription(
                    key="1-0:1.8.0*255", name="Test Energy"
                )
            ),
        )

        assert sensor.native_value is None

    def test_returns_correct_value_with_valid_data(
        self, mock_coordinator, valid_information
    ):
        """Test that sensor returns correct value when data is valid."""
        mock_coordinator.data = valid_information

        sensor = OBISSensor(
            coordinator=mock_coordinator,
            spec=OBISSensorSpec(
                description=SensorEntityDescription(key="1-0:1.8.0", name="Test Energy")
            ),
        )

        assert sensor.native_value == "1234.5"

    def test_returns_none_when_obis_key_missing(
        self, mock_coordinator, valid_information
    ):
        """Test that sensor returns None when OBIS key is not in readings."""
        mock_coordinator.data = valid_information

        sensor = OBISSensor(
            coordinator=mock_coordinator,
            spec=OBISSensorSpec(
                description=SensorEntityDescription(
                    key="1-0:99.99.99*255", name="Test Missing"
                )
            ),
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


class TestTranslations:
    """Guard the generated entity.sensor translation blocks."""

    _TR = Path(sensor_module.__file__).parent / "translations"

    def _entity_sensor(self, path: Path) -> dict:
        return json.loads(path.read_text())["entity"]["sensor"]

    def _entity_block(self, path: Path) -> dict:
        return json.loads(path.read_text())["entity"]

    def test_en_de_parity(self):
        """en and de must define the same entity keys across every platform."""
        en = self._entity_block(self._TR / "en.json")
        de = self._entity_block(self._TR / "de.json")
        assert set(en) == set(de)
        for platform in en:
            assert set(en[platform]) == set(de[platform]), platform

    def test_config_options_parity(self):
        """en and de must define matching config and options flow structure."""
        en = json.loads((self._TR / "en.json").read_text())
        de = json.loads((self._TR / "de.json").read_text())
        assert set(en["config"]["step"]) == set(de["config"]["step"])
        assert set(en["options"]["step"]) == set(de["options"]["step"])

    def test_system_entities_translated(self):
        """The non-OBIS entities must have translation entries in both languages."""
        for lang in ("en.json", "de.json"):
            ent = self._entity_block(self._TR / lang)
            assert ent["sensor"]["last_update"]["name"]
            assert ent["sensor"]["firmware_version"]["name"]
            assert ent["button"]["restart_gateway"]["name"]

    def test_all_catalog_slugs_and_variants_present(self):
        en = self._entity_sensor(self._TR / "en.json")
        for info in OBIS_CATALOG.values():
            for suffix in ("", "_channel", "_tariff", "_channel_tariff"):
                assert f"{info.translation_key}{suffix}" in en
        assert "unknown_code" in en

    def test_template_tokens_are_known(self):
        """Every {token} in a name must be one of channel/tariff/code."""
        allowed = {"channel", "tariff", "code"}
        for lang in ("en.json", "de.json"):
            block = self._entity_sensor(self._TR / lang)
            for key, entry in block.items():
                tokens = set(re.findall(r"\{(\w+)\}", entry["name"]))
                assert tokens <= allowed, f"{lang}:{key} has unexpected {tokens}"


class TestFirmwareSensor:
    """Test the FirmwareSensor class."""

    @pytest.mark.parametrize(
        ("poll_sequence", "expected"),
        [
            # (firmware value per poll; None means data is not an Information object)
            pytest.param([None], None, id="invalid_and_uncached"),
            pytest.param(["1.0.0"], "1.0.0", id="valid_data"),
            pytest.param(["1.0.0", "Unknown"], "1.0.0", id="caches_across_unknown"),
            pytest.param(["Unknown"], None, id="only_unknown_received"),
            pytest.param(["1.0.0", None], "1.0.0", id="caches_across_invalid"),
        ],
    )
    def test_native_value(
        self, mock_coordinator, valid_information, poll_sequence, expected
    ):
        sensor = FirmwareSensor(
            coordinator=mock_coordinator,
            entity_description=FirmwareVersionSensorDescription,
        )

        result = None
        for firmware in poll_sequence:
            if firmware is None:
                mock_coordinator.data = None
            else:
                mock_coordinator.data = replace(
                    valid_information, firmware_version=firmware
                )
            result = sensor.native_value

        assert result == expected
