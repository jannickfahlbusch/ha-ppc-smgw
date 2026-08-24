from __future__ import annotations

import asyncio
from datetime import datetime
import logging

from homeassistant.util.dt import now
import httpx
from obis_parser import OBIS
from py_ppc_smgw import PPCSMGWClient
from py_ppc_smgw.types import FirmwareVersion, Meter
import urllib3

from custom_components.ppc_smgw.gateways.gateway import Gateway
from custom_components.ppc_smgw.gateways.ppc.const import (
    DEFAULT_MODEL,
    DEFAULT_NAME,
    MANUFACTURER,
)
from custom_components.ppc_smgw.gateways.reading import (
    Information,
    Reading,
    build_fake_information,
)

# Needed as the PPC SMGW uses a self-signed certificate
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class PPC_SMGW(Gateway):
    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        websession: httpx.AsyncClient,
        logger: logging.Logger,
        debug: bool = False,
    ) -> None:
        super().__init__(host, username, password, websession, logger, debug)

        self.dynamic_obis_discovery_enabled = True

    async def get_data(self) -> Information:
        self.logger.info("Fetching data from Gateway")

        if self.debug:
            self.logger.debug("Debugging enabled, returning fake data")

            # It takes around 15 seconds for the GW to respond to all calls
            # We should emulate this here to avoid timing issues
            await asyncio.sleep(15)
            self.data = build_fake_information()
        else:
            self.logger.debug("Using py-ppc-smgw library for data fetching")
            self.data = await self._get_data()

        return self.data

    async def _get_data(self) -> Information:
        """Fetch data through the py-ppc-smgw library.

        Reads only the first meter to keep parity with the built-in client.
        The firmware string is reconstructed in the built-in client's
        "<bootstream>-<services>" format so the device info stays identical.
        """
        async with PPCSMGWClient(
            host=self.host,
            username=self.username,
            password=self.password,
            httpx_client=self.websession,
            logger=self.logger,
        ) as client:
            readings: dict[OBIS, Reading] = {}
            last_ts: datetime | None = None

            meters: list[Meter] = await client.get_meters()
            if meters:
                meter_readings = await client.get_meter_reading(meters[0])
                for obis, reading in meter_readings.items():
                    ts = self._as_aware(reading.timestamp)
                    readings[obis] = Reading(
                        value=self._coerce_reading_value(reading.value),
                        timestamp=ts,
                        obis=obis,
                    )
                    if ts is not None and (last_ts is None or ts > last_ts):
                        last_ts = ts

            firmware = self._construct_firmware_version(
                await client.get_firmware_versions()
            )

        return Information(
            name=DEFAULT_NAME,
            model=DEFAULT_MODEL,
            manufacturer=MANUFACTURER,
            firmware_version=firmware,
            last_update=last_ts or now(),
            readings=readings,
        )

    @staticmethod
    def _as_aware(dt: datetime | None) -> datetime | None:
        """Make a datetime tz-aware, mirroring the built-in client's behaviour.

        The last_update sensor is a TIMESTAMP device class, so naive values
        would be rejected by Home Assistant.
        """
        if dt is None:
            return None
        return dt.replace(tzinfo=now().tzinfo) if dt.tzinfo is None else dt

    @staticmethod
    def _coerce_reading_value(value: str | float) -> str | float:
        """Return numeric gateway values as numbers when possible."""
        try:
            return float(value)
        except (TypeError, ValueError):
            return value

    @staticmethod
    def _construct_firmware_version(firmware_versions: list[FirmwareVersion]) -> str:
        """Rebuild the built-in client's firmware string.

        Format is "<smgw-bootstream>-<smgw-services>"; missing components
        collapse to an empty segment.
        """
        by_component = {fw.component: fw.version for fw in firmware_versions}
        bootstream = by_component.get("smgw-bootstream", "")
        services = by_component.get("smgw-services", "")
        return f"{bootstream}-{services}"

    async def reboot(self):
        """Reboot the gateway."""
        self.logger.info("Rebooting Gateway")

        async with PPCSMGWClient(
            host=self.host,
            username=self.username,
            password=self.password,
            httpx_client=self.websession,
            logger=self.logger,
        ) as client:
            return await client.reboot()
