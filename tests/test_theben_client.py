"""Tests for the Theben Conexa client and MD5 DigestAuth."""

import logging
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from obis_parser import OBIS

from custom_components.ppc_smgw.gateways.theben.conexa.conexa import (
    ThebenConexaClient,
    ThebenMD5DigestAuth,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(json_data, status_code=200, text=None):
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.text = text if text is not None else str(json_data)
    response.json.return_value = json_data
    return response


def _make_client(base_url="https://192.168.0.1", username="user", password="pass"):
    httpx_client = MagicMock(spec=httpx.AsyncClient)
    httpx_client.headers = {}
    httpx_client.follow_redirects = True
    logger = logging.getLogger("test")
    return ThebenConexaClient(
        base_url=base_url,
        username=username,
        password=password,
        httpx_client=httpx_client,
        logger=logger,
    )


# ---------------------------------------------------------------------------
# ThebenMD5DigestAuth tests
# ---------------------------------------------------------------------------


class TestThebenMD5DigestAuth:
    def test_overrides_sha256_to_md5(self):
        auth = ThebenMD5DigestAuth("testuser", "testpass")
        req = httpx.Request("POST", "https://192.168.0.1/smgw/m2m/test.sm/json")
        resp = httpx.Response(
            401,
            headers={
                "www-authenticate": (
                    'Digest realm="Conexa", nonce="d2b3c4d5e6", '
                    'algorithm="SHA-256", qop="auth"'
                )
            },
        )
        challenge = auth._parse_challenge(req, resp, resp.headers["www-authenticate"])
        assert challenge.algorithm == "MD5"
        assert challenge.realm == b"Conexa"
        assert challenge.nonce == b"d2b3c4d5e6"

    def test_preserves_md5(self):
        auth = ThebenMD5DigestAuth("testuser", "testpass")
        req = httpx.Request("POST", "https://192.168.0.1/smgw/m2m/test.sm/json")
        resp = httpx.Response(
            401,
            headers={
                "www-authenticate": (
                    'Digest realm="Conexa", nonce="d2b3c4d5e6", '
                    'algorithm="MD5", qop="auth"'
                )
            },
        )
        challenge = auth._parse_challenge(req, resp, resp.headers["www-authenticate"])
        assert challenge.algorithm == "MD5"

    def test_defaults_to_md5_when_no_algorithm_specified(self):
        auth = ThebenMD5DigestAuth("testuser", "testpass")
        req = httpx.Request("POST", "https://192.168.0.1/smgw/m2m/test.sm/json")
        resp = httpx.Response(
            401,
            headers={
                "www-authenticate": 'Digest realm="Conexa", nonce="d2b3c4d5e6", qop="auth"'
            },
        )
        challenge = auth._parse_challenge(req, resp, resp.headers["www-authenticate"])
        assert challenge.algorithm == "MD5"

    def test_builds_auth_header_with_md5(self):
        auth = ThebenMD5DigestAuth("testuser", "testpass")
        req = httpx.Request("POST", "https://192.168.0.1/smgw/m2m/test.sm/json")
        resp = httpx.Response(
            401,
            headers={
                "www-authenticate": (
                    'Digest realm="Conexa", nonce="d2b3c4d5e6", '
                    'algorithm="SHA-256", qop="auth"'
                )
            },
        )
        challenge = auth._parse_challenge(req, resp, resp.headers["www-authenticate"])
        auth_header = auth._build_auth_header(req, challenge)
        assert "algorithm=MD5" in auth_header
        assert 'username="testuser"' in auth_header
        assert 'realm="Conexa"' in auth_header


# ---------------------------------------------------------------------------
# ThebenConexaClient tests
# ---------------------------------------------------------------------------


class TestThebenConexaClient:
    def test_get_auth_returns_theben_md5_digest_auth(self):
        client = _make_client(username="myuser", password="mypassword")
        auth = client._get_auth()
        assert isinstance(auth, ThebenMD5DigestAuth)
        assert auth._username == b"myuser"
        assert auth._password == b"mypassword"

    async def test_get_firmware_version_success(self):
        client = _make_client()
        mock_smgw_info = {
            "smgw-info": {
                "firmware-info": {
                    "version": "3.0.12",
                    "hash": "abcdef0123456789abcdef0123456789",
                }
            }
        }
        client.httpx_client.post = AsyncMock(
            return_value=_make_response(mock_smgw_info)
        )
        fw = await client._get_firmware_version()
        assert fw == "3.0.12-abcdef01"

    async def test_get_usage_point_ids_prefers_running_taf7(self):
        client = _make_client()
        mock_user_info = {
            "user-info": {
                "usage-points": [
                    {
                        "usage-point-id": "UP001",
                        "taf-state": "stopped",
                        "taf-number": "7",
                    },
                    {
                        "usage-point-id": "UP002",
                        "taf-state": "running",
                        "taf-number": "7",
                    },
                    {
                        "usage-point-id": "UP003",
                        "taf-state": "running",
                        "taf-number": "1",
                    },
                ]
            }
        }
        client.httpx_client.post = AsyncMock(
            return_value=_make_response(mock_user_info)
        )
        up_ids = await client._get_usage_point_ids()
        assert up_ids == ["UP002"]

    async def test_get_readings_success(self):
        client = _make_client()
        mock_user_info = {
            "user-info": {
                "usage-points": [
                    {
                        "usage-point-id": "UP001",
                        "taf-state": "running",
                        "taf-number": "7",
                    }
                ]
            }
        }
        mock_readings = {
            "readings": {
                "channels": [
                    {
                        "obis": "0100010800ff",
                        "readings": [
                            {
                                "value": "12345678",
                                "capture-time": "2026-08-14T12:00:00Z",
                            }
                        ],
                    },
                    {
                        "obis": "0100020800ff",
                        "readings": [
                            {
                                "value": "87654321",
                                "capture-time": "2026-08-14T12:00:00Z",
                            }
                        ],
                    },
                ]
            }
        }
        client.httpx_client.post = AsyncMock(
            side_effect=[
                _make_response(mock_user_info),
                _make_response(mock_readings),
            ]
        )
        readings = await client._get_readings()
        obis_import = OBIS(1, 0, 1, 8, 0, 255)
        obis_export = OBIS(1, 0, 2, 8, 0, 255)
        assert obis_import in readings
        assert readings[obis_import].value == pytest.approx(1234.5678)
        assert obis_export in readings
        assert readings[obis_export].value == pytest.approx(8765.4321)
