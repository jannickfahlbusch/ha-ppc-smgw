"""
Standalone test script for EMHCasaClient - no Home Assistant needed.
Works with both absolute and relative import styles in emh_client.py.

Requirements:  pip install httpx

Usage:
    source .venv/bin/activate
    python scripts/test_emh_local.py <host> <username> <password>

Example:
    source .venv/bin/activate
    python scripts/test_emh_local.py https://192.168.33.2 admin secret
"""

import asyncio
import importlib.util
import logging
import os
import sys
import types
from dataclasses import dataclass
from datetime import datetime

# ---------------------------------------------------------------------------
# Inline stubs for HA-dependent types used by emh_client.py
# ---------------------------------------------------------------------------

OBISCode = str


@dataclass
class Reading:
    value: float
    timestamp: datetime
    obis: str


@dataclass
class Information:
    name: str
    model: str
    manufacturer: str
    firmware_version: str
    last_update: datetime
    readings: dict


# ---------------------------------------------------------------------------
# Build stub package tree so both absolute and relative imports resolve
# without executing any real HA __init__.py files.
# Each stub gets __path__ so Python treats it as a package.
# ---------------------------------------------------------------------------

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_STUB_PKGS = [
    ("custom_components", "custom_components"),
    ("custom_components.ppc_smgw", "custom_components/ppc_smgw"),
    ("custom_components.ppc_smgw.gateways", "custom_components/ppc_smgw/gateways"),
    (
        "custom_components.ppc_smgw.gateways.emh",
        "custom_components/ppc_smgw/gateways/emh",
    ),
    (
        "custom_components.ppc_smgw.gateways.emh.emhcasa",
        "custom_components/ppc_smgw/gateways/emh/emhcasa",
    ),
]

for mod_name, rel_path in _STUB_PKGS:
    mod = types.ModuleType(mod_name)
    mod.__path__ = [os.path.join(BASE, rel_path)]
    mod.__package__ = mod_name
    sys.modules[mod_name] = mod

_CONST_ATTRS = dict(
    # absolute import style:  from custom_components.ppc_smgw.const import ...
    EMH_DEFAULT_NAME="EMH CASA",
    EMH_MANUFACTURER="EMH Metering",
    EMH_DEFAULT_MODEL="CASA",
    # relative import style:  from ..const import ... (resolves to emh.const)
    DEFAULT_NAME="EMH CASA",
    DEFAULT_MODEL="CASA",
    MANUFACTURER="EMH Metering",
)

_READING_ATTRS = dict(OBISCode=OBISCode, Reading=Reading, Information=Information)

for stub_name, attrs in [
    ("custom_components.ppc_smgw.const", _CONST_ATTRS),
    ("custom_components.ppc_smgw.gateways.reading", _READING_ATTRS),
    # also register under relative-import-resolved paths
    ("custom_components.ppc_smgw.gateways.emh.const", _CONST_ATTRS),
    ("custom_components.ppc_smgw.gateways.emh.reading", _READING_ATTRS),
]:
    mod = types.ModuleType(stub_name)
    mod.__dict__.update(attrs)
    sys.modules[stub_name] = mod

# ---------------------------------------------------------------------------
# Load emh_client.py with the full dotted module name so relative imports work
# ---------------------------------------------------------------------------

_CLIENT_PATH = os.path.join(
    BASE, "custom_components", "ppc_smgw", "gateways", "emh", "emhcasa", "emh_client.py"
)
_FULL_NAME = "custom_components.ppc_smgw.gateways.emh.emhcasa.emh_client"

_spec = importlib.util.spec_from_file_location(_FULL_NAME, _CLIENT_PATH)
_client_mod = importlib.util.module_from_spec(_spec)
_client_mod.__package__ = "custom_components.ppc_smgw.gateways.emh.emhcasa"
sys.modules[_FULL_NAME] = _client_mod
_spec.loader.exec_module(_client_mod)

EMHCasaClient = _client_mod.EMHCasaClient

# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("emh_test")


async def main(host: str, username: str, password: str) -> None:
    import httpx

    async with httpx.AsyncClient(verify=False) as client:
        emh = EMHCasaClient(
            base_url=host,
            username=username,
            password=password,
            httpx_client=client,
            logger=logger,
        )
        info = await emh.get_data()
        print("\n=== Result ===")
        print(f"Name:     {info.name}")
        print(f"Model:    {info.model}")
        print(f"Firmware: {info.firmware_version}")
        print(f"Updated:  {info.last_update}")
        print(f"Readings ({len(info.readings)}):")
        for obis, reading in info.readings.items():
            print(f"  {obis}: {reading.value}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    asyncio.run(main(sys.argv[1], sys.argv[2], sys.argv[3]))
