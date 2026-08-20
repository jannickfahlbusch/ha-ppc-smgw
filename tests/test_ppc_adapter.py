"""Tests for the PPC adapter's built-in vs library data paths."""

from datetime import UTC, datetime
import logging
from unittest.mock import AsyncMock, MagicMock, patch

from obis_parser import OBIS
from py_ppc_smgw.types import FirmwareVersion, Meter, Reading as LibReading
import pytest

from custom_components.ppc_smgw.gateways.ppc.const import (
    DEFAULT_MODEL,
    MANUFACTURER,
)
from custom_components.ppc_smgw.gateways.ppc.ppc_smgw import PPC_SMGW
from custom_components.ppc_smgw.gateways.reading import Information, Reading

_ADAPTER = "custom_components.ppc_smgw.gateways.ppc.ppc_smgw"


def _make_adapter() -> PPC_SMGW:
    """Build a real PPC_SMGW adapter with a stub websession/logger."""
    return PPC_SMGW(
        host="https://192.168.1.200/cgi-bin/hanservice.cgi",
        username="testuser",
        password="testpass",
        websession=MagicMock(),
        logger=logging.getLogger("test.ppc_adapter"),
    )


def _library_client_mock(meters=None, readings=None, firmware=None) -> MagicMock:
    """Return a MagicMock that behaves as the PPCSMGWClient async context manager."""
    client = MagicMock()
    client.get_meters = AsyncMock(return_value=meters or [])
    client.get_meter_reading = AsyncMock(return_value=readings or {})
    client.get_firmware_versions = AsyncMock(return_value=firmware or [])
    client.reboot = AsyncMock()

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__ = AsyncMock(return_value=None)
    factory = MagicMock(return_value=cm)
    factory.client = client  # convenience handle for assertions
    return factory


@pytest.mark.asyncio
class TestPPCAdapterDataPath:
    """Tests for PPC adapter data retrieval and mapping."""

    async def test_dynamic_obis_discovery_activated(self):
        """PPC adapter enables dynamic OBIS discovery by default."""
        adapter = _make_adapter()

        assert adapter.dynamic_obis_discovery_enabled is True

    async def test_adapter_maps_canonical_readings_and_firmware(self):
        """Adapter maps library readings to canonical Information data."""
        adapter = _make_adapter()

        naive = datetime(2024, 12, 20, 16, 0, 1)  # tz-naive on purpose
        older = datetime(2024, 12, 20, 15, 0, 0)
        readings = {
            OBIS(1, 0, 1, 8, 0): LibReading(
                value="724.9204", timestamp=naive, obis=OBIS(1, 0, 1, 8, 0)
            ),
            OBIS(1, 0, 2, 8, 0): LibReading(
                value="3.0557", timestamp=older, obis=OBIS(1, 0, 2, 8, 0)
            ),
        }
        firmware = [
            FirmwareVersion(component="smgw-bootstream", version="33918", checksum="x"),
            FirmwareVersion(component="smgw-services", version="34868", checksum="y"),
        ]
        factory = _library_client_mock(
            meters=[Meter(mid="mid", name="n")],
            readings=readings,
            firmware=firmware,
        )

        with patch(f"{_ADAPTER}.PPCSMGWClient", factory):
            result = await adapter.get_data()

        assert isinstance(result, Information)
        assert result.model == DEFAULT_MODEL
        assert result.manufacturer == MANUFACTURER
        assert result.firmware_version == "33918-34868"
        # Readings mapped to the integration's own Reading type, tz-aware.
        assert isinstance(result.readings[OBIS(1, 0, 1, 8, 0)], Reading)
        assert result.readings[OBIS(1, 0, 1, 8, 0)].value == 724.9204
        assert result.readings[OBIS(1, 0, 1, 8, 0)].timestamp.tzinfo is not None
        assert result.readings[OBIS(1, 0, 1, 8, 0)].obis == OBIS(1, 0, 1, 8, 0)
        assert result.readings[OBIS(1, 0, 2, 8, 0)].value == 3.0557
        assert result.readings[OBIS(1, 0, 2, 8, 0)].obis == OBIS(1, 0, 2, 8, 0)
        assert all(isinstance(k, OBIS) for k in result.readings)
        # last_update is the newest reading timestamp.
        assert result.last_update == adapter._as_aware(naive)
        # Only the first meter is read (parity with built-in client).
        factory.client.get_meter_reading.assert_awaited_once()

    async def test_adapter_no_meters_gives_empty_readings(self):
        """No meters → empty readings and a tz-aware now() fallback."""
        adapter = _make_adapter()
        factory = _library_client_mock(meters=[], firmware=[])

        with patch(f"{_ADAPTER}.PPCSMGWClient", factory):
            result = await adapter.get_data()

        assert result.readings == {}
        assert result.last_update.tzinfo is not None
        assert result.firmware_version == "-"
        factory.client.get_meter_reading.assert_not_awaited()


def _fw(*components) -> list[FirmwareVersion]:
    """Build a FirmwareVersion list from (component, version) pairs."""
    return [
        FirmwareVersion(component=c, version=v, checksum="x") for c, v in components
    ]


class TestConstructFirmwareVersion:
    """_construct_firmware_version joins two known components, tolerating gaps.

    The firmware string is cosmetic (PPC exposes no changelog), so a missing
    component must degrade the string rather than raise and break the poll.
    """

    @pytest.mark.parametrize(
        ("firmware", "expected"),
        [
            (
                _fw(("smgw-bootstream", "33918"), ("smgw-services", "34868")),
                "33918-34868",
            ),
            (_fw(("smgw-bootstream", "33918")), "33918-"),  # services missing
            (_fw(("smgw-services", "34868")), "-34868"),  # bootstream missing
            (_fw(), "-"),  # nothing reported
            (_fw(("smgw-other", "1")), "-"),  # only unrelated components
        ],
    )
    def test_joins_and_tolerates_missing_components(self, firmware, expected):
        assert PPC_SMGW._construct_firmware_version(firmware) == expected


class TestAsAware:
    """_as_aware only touches naive datetimes; None and aware pass through."""

    def test_none_passes_through(self):
        assert PPC_SMGW._as_aware(None) is None

    def test_aware_datetime_is_returned_unchanged(self):
        aware = datetime(2024, 12, 20, 16, 0, 1, tzinfo=UTC)
        assert PPC_SMGW._as_aware(aware) is aware

    def test_naive_datetime_becomes_aware(self):
        result = PPC_SMGW._as_aware(datetime(2024, 12, 20, 16, 0, 1))
        assert result.tzinfo is not None


@pytest.mark.asyncio
class TestPPCAdapterReboot:
    async def test_library_reboot_calls_reboot(self):
        adapter = _make_adapter()
        factory = _library_client_mock()

        with patch(f"{_ADAPTER}.PPCSMGWClient", factory):
            await adapter.reboot()

        factory.client.reboot.assert_awaited_once()
