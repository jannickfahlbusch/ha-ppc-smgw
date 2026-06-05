"""Tests for the EMH CASA client."""

import logging
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from custom_components.ppc_smgw.gateways.emh.emhcasa.emh_client import EMHCasaClient

# ---------------------------------------------------------------------------
# Anonymised fixture data matching real device response shapes
# ---------------------------------------------------------------------------

_METER_ID = "1test000000001"

_ORIGIN_EXTENDED = {
    "capture_time": "2026-01-01T00:00:00+01:00",
    "status": "a0000000000000",
    "timestamp": "2026-01-01T00:00:00+01:00",
    "values": [
        # Import total (Wh, unit=30, scaler=-1) → 1234.5678 kWh
        {
            "logical_name": f"0100010800ff.{_METER_ID}.sm",
            "scaler": -1,
            "signature": "-",
            "unit": 30,
            "value": "12345678",
        },
        # Export total (Wh, unit=30, scaler=-1) → 987.6543 kWh
        {
            "logical_name": f"0100020800ff.{_METER_ID}.sm",
            "scaler": -1,
            "signature": "-",
            "unit": 30,
            "value": "9876543",
        },
        # Active power (W, unit=27, scaler=0) → 500 W
        {
            "logical_name": f"0100100700ff.{_METER_ID}.sm",
            "scaler": 0,
            "signature": "-",
            "unit": 27,
            "value": "500",
        },
        # Invalid entry: logical_name too short → must be skipped
        {
            "logical_name": "short",
            "scaler": 0,
            "signature": "-",
            "unit": 27,
            "value": "1",
        },
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(json_data, status_code=200):
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.text = str(json_data)
    response.json.return_value = json_data
    return response


def _make_client(base_url="https://192.168.0.1", username="user", password="pass"):
    httpx_client = MagicMock(spec=httpx.AsyncClient)
    httpx_client.headers = {}
    httpx_client.follow_redirects = True
    logger = logging.getLogger("test")
    return EMHCasaClient(
        base_url=base_url,
        username=username,
        password=password,
        httpx_client=httpx_client,
        logger=logger,
    )


# ---------------------------------------------------------------------------
# base_url normalisation
# ---------------------------------------------------------------------------


class TestBaseUrlNormalisation:
    def test_bare_ip_gets_https(self):
        c = _make_client(base_url="192.168.0.1")
        assert c.base_url == "https://192.168.0.1"

    def test_http_scheme_preserved(self):
        c = _make_client(base_url="http://192.168.0.1")
        assert c.base_url == "http://192.168.0.1"

    def test_https_scheme_preserved(self):
        c = _make_client(base_url="https://192.168.0.1")
        assert c.base_url == "https://192.168.0.1"

    def test_trailing_slash_stripped(self):
        c = _make_client(base_url="https://192.168.0.1/")
        assert c.base_url == "https://192.168.0.1"

    def test_scheme_separator_not_stripped(self):
        # rstrip would have broken "https://" → "https:" — verify this can't happen
        c = _make_client(base_url="https://192.168.0.1")
        assert c.base_url.startswith("https://")


# ---------------------------------------------------------------------------
# _discover_meter_id
# ---------------------------------------------------------------------------


class TestDiscoverAllMeterIds:
    async def test_returns_all_meter_ids(self):
        c = _make_client()
        c.httpx_client.get = AsyncMock(
            return_value=_make_response([_METER_ID, "1test000000002"])
        )
        meter_ids = await c.discover_all_meter_ids()
        assert meter_ids == [_METER_ID, "1test000000002"]

    async def test_returns_empty_on_connection_error(self):
        c = _make_client()
        c.httpx_client.get = AsyncMock(side_effect=Exception("connection refused"))
        meter_ids = await c.discover_all_meter_ids()
        assert meter_ids == []

    async def test_returns_empty_when_no_meters(self):
        c = _make_client()
        c.httpx_client.get = AsyncMock(return_value=_make_response([]))
        meter_ids = await c.discover_all_meter_ids()
        assert meter_ids == []


# ---------------------------------------------------------------------------
# _get_readings / get_data
# ---------------------------------------------------------------------------


class TestGetReadings:
    async def test_parses_readings_correctly(self):
        c = _make_client()
        c.httpx_client.get = AsyncMock(
            side_effect=[
                _make_response([_METER_ID]),
                _make_response(_ORIGIN_EXTENDED),
            ]
        )
        readings = await c._get_readings()

        assert "1-0:1.8.0" in readings
        assert "1-0:2.8.0" in readings
        assert "1-0:16.7.0" in readings

    async def test_import_value_converted_from_wh_to_kwh(self):
        """value=12345678, scaler=-1, unit=30 → 12345678 * 0.1 / 1000 = 1234.5678"""
        c = _make_client()
        c.meter_id = _METER_ID
        c.httpx_client.get = AsyncMock(return_value=_make_response(_ORIGIN_EXTENDED))
        readings = await c._get_readings()
        assert readings["1-0:1.8.0"].value == pytest.approx(1234.5678)

    async def test_skips_invalid_logical_name(self):
        c = _make_client()
        c.meter_id = _METER_ID
        c.httpx_client.get = AsyncMock(return_value=_make_response(_ORIGIN_EXTENDED))
        readings = await c._get_readings()
        # "short" entry must be dropped
        assert all(len(k) > 5 for k in readings)
        assert len(readings) == 3

    async def test_returns_empty_on_http_error(self):
        c = _make_client()
        c.meter_id = _METER_ID
        c.httpx_client.get = AsyncMock(side_effect=Exception("timeout"))
        readings = await c._get_readings()
        assert readings == {}

    async def test_get_data_returns_information(self):
        c = _make_client()
        c.httpx_client.get = AsyncMock(
            side_effect=[
                _make_response([_METER_ID]),
                _make_response(_ORIGIN_EXTENDED),
            ]
        )
        info = await c.get_data()
        assert info.name == "EMH SMGW"
        assert len(info.readings) == 3

    async def test_nonzero_channel_byte_extracted(self):
        """Verify that A and B bytes from hex logical_name are parsed (not hardcoded to 1-0)."""
        meter_data = {
            "values": [
                {
                    "logical_name": f"0101010800ff.{_METER_ID}.sm",
                    "scaler": 0,
                    "signature": "-",
                    "unit": 30,
                    "value": "1000000",
                },
            ]
        }
        c = _make_client()
        c.meter_id = _METER_ID
        c.httpx_client.get = AsyncMock(return_value=_make_response(meter_data))
        readings = await c._get_readings()
        # A=01, B=01 should produce 1-1:1.8.0
        assert "1-1:1.8.0" in readings
