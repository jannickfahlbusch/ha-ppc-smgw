"""Tests for the PPC adapter's built-in vs library data paths."""

import logging
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ppc_smgw.gateways.ppc.ppc_smgw import PPC_SMGW
from custom_components.ppc_smgw.gateways.ppc.const import (
    DEFAULT_MODEL,
    MANUFACTURER,
)
from custom_components.ppc_smgw.gateways.reading import Information, Reading

from py_ppc_smgw.types import FirmwareVersion, Meter, Reading as LibReading

_ADAPTER = "custom_components.ppc_smgw.gateways.ppc.ppc_smgw"


def _make_adapter(use_library: bool) -> PPC_SMGW:
    """Build a real PPC_SMGW adapter with a stub websession/logger."""
    return PPC_SMGW(
        host="https://192.168.1.200/cgi-bin/hanservice.cgi",
        username="testuser",
        password="testpass",
        websession=MagicMock(),
        logger=logging.getLogger("test.ppc_adapter"),
        use_library=use_library,
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
    """get_data() must pick the right client based on use_library."""

    async def test_builtin_path_returns_client_data_untouched(self):
        """use_library=False delegates to the built-in client, unchanged."""
        adapter = _make_adapter(use_library=False)
        canned = Information(
            name="N",
            model="M",
            manufacturer="Mfr",
            firmware_version="1-2",
            last_update=datetime(2024, 1, 1, tzinfo=timezone.utc),
            readings={},
        )
        adapter.ppc_smgw_client.get_data = AsyncMock(return_value=canned)

        with patch(f"{_ADAPTER}.PPCSMGWClient") as lib_cls:
            result = await adapter.get_data()

        assert result is canned
        lib_cls.assert_not_called()

    async def test_library_path_maps_readings_and_firmware(self):
        """use_library=True reads first meter, maps readings, joins firmware."""
        adapter = _make_adapter(use_library=True)

        naive = datetime(2024, 12, 20, 16, 0, 1)  # tz-naive on purpose
        older = datetime(2024, 12, 20, 15, 0, 0)
        readings = {
            "1-0:1.8.0": LibReading(
                value="724.9204", timestamp=naive, obis="1-0:1.8.0"
            ),
            "1-0:2.8.0": LibReading(value="3.0557", timestamp=older, obis="1-0:2.8.0"),
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
        assert isinstance(result.readings["1-0:1.8.0"], Reading)
        assert result.readings["1-0:1.8.0"].timestamp.tzinfo is not None
        # last_update is the newest reading timestamp.
        assert result.last_update == adapter._as_aware(naive)
        # Only the first meter is read (parity with built-in client).
        factory.client.get_meter_reading.assert_awaited_once()

    async def test_library_path_no_meters_gives_empty_readings(self):
        """No meters → empty readings and a tz-aware now() fallback."""
        adapter = _make_adapter(use_library=True)
        factory = _library_client_mock(meters=[], firmware=[])

        with patch(f"{_ADAPTER}.PPCSMGWClient", factory):
            result = await adapter.get_data()

        assert result.readings == {}
        assert result.last_update.tzinfo is not None
        assert result.firmware_version == "-"
        factory.client.get_meter_reading.assert_not_awaited()


@pytest.mark.asyncio
class TestPPCAdapterReboot:
    """reboot() must target the right client based on use_library."""

    async def test_builtin_reboot_delegates_to_builtin_client(self):
        adapter = _make_adapter(use_library=False)
        adapter.ppc_smgw_client.reboot = AsyncMock()

        with patch(f"{_ADAPTER}.PPCSMGWClient") as lib_cls:
            await adapter.reboot()

        adapter.ppc_smgw_client.reboot.assert_awaited_once()
        lib_cls.assert_not_called()

    async def test_library_reboot_delegates_to_library_client(self):
        adapter = _make_adapter(use_library=True)
        adapter.ppc_smgw_client.reboot = AsyncMock()
        factory = _library_client_mock()

        with patch(f"{_ADAPTER}.PPCSMGWClient", factory):
            await adapter.reboot()

        factory.client.reboot.assert_awaited_once()
        adapter.ppc_smgw_client.reboot.assert_not_awaited()
