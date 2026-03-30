"""Tests for the EMH CASA client."""

import logging
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from custom_components.ppc_smgw.gateways.emh.emhcasa.emh_client import EMHCasaClient

# ---------------------------------------------------------------------------
# Anonymised fixture data matching real device response shapes
# ---------------------------------------------------------------------------

_CONTRACT_ID = "0100aabbccdd00.test_contract_taf01000014000000000001.sm"

_DERIVED_LIST = [_CONTRACT_ID]

_DERIVED_CONTRACT = {
    "active_tariff": -1,
    "capture_period": 900,
    "emt_channel_name": "testp01100001v3",
    "logical_name": _CONTRACT_ID,
    "metering_point_id": "DE0000000000000000000000000000001",
    "sensor_domains": ["1test000000001"],
    "taf_identifier": "test_contract_taf01000014000000000001.sm",
    "taf_name": "test_contract_taf01000014000000000001",
    "taf_state": "archive",
    "taf_type": "TAF-1",
    "user_domain": "0000000000000000000001",
    "validity_end": 1762124400,
    "validity_start": 1759984200,
}

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


class TestDiscoverMeterId:
    async def test_returns_first_sensor_domain(self):
        c = _make_client()
        c.httpx_client.get = AsyncMock(
            side_effect=[
                _make_response(_DERIVED_LIST),
                _make_response(_DERIVED_CONTRACT),
            ]
        )
        meter_id = await c._discover_meter_id()
        assert meter_id == _METER_ID

    async def test_returns_none_on_connection_error(self):
        c = _make_client()
        c.httpx_client.get = AsyncMock(side_effect=Exception("connection refused"))
        meter_id = await c._discover_meter_id()
        assert meter_id is None

    async def test_returns_none_when_no_sensor_domains(self):
        contract_without_domains = {**_DERIVED_CONTRACT, "sensor_domains": []}
        c = _make_client()
        c.httpx_client.get = AsyncMock(
            side_effect=[
                _make_response(_DERIVED_LIST),
                _make_response(contract_without_domains),
            ]
        )
        meter_id = await c._discover_meter_id()
        assert meter_id is None


# ---------------------------------------------------------------------------
# _get_readings / get_data
# ---------------------------------------------------------------------------


class TestGetReadings:
    async def test_parses_readings_correctly(self):
        c = _make_client()
        c.httpx_client.get = AsyncMock(
            side_effect=[
                _make_response(_DERIVED_LIST),
                _make_response(_DERIVED_CONTRACT),
                _make_response(_ORIGIN_EXTENDED),
            ]
        )
        readings = await c._get_readings()

        assert "1-0:1.8.0" in readings
        assert "1-0:2.8.0" in readings
        assert "1-0:16.7.0" in readings

    def test_import_value_converted_from_wh_to_kwh(self):
        """value=12345678, scaler=-1, unit=30 → 12345678 * 0.1 / 1000 = 1234.5678"""
        c = _make_client()
        c.meter_id = _METER_ID
        c.httpx_client.get = AsyncMock(return_value=_make_response(_ORIGIN_EXTENDED))

        import asyncio

        readings = asyncio.get_event_loop().run_until_complete(c._get_readings())
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
                _make_response(_DERIVED_LIST),
                _make_response(_DERIVED_CONTRACT),
                _make_response(_ORIGIN_EXTENDED),
            ]
        )
        info = await c.get_data()
        assert info.name == "EMH SMGW"
        assert len(info.readings) == 3
