from __future__ import annotations

import asyncio
from datetime import datetime
import logging
import time

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
    MAX_METERS_PER_POLL,
    METER_READ_TIME_BUDGET,
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

        Reads all meters (tariff/meter profiles) exposed by the gateway and
        merges their OBIS readings. Some gateways expose import (1.8.0) and
        export (2.8.0) as separate meter entries, so reading only the first
        one silently drops values. If the same OBIS code is reported by more
        than one meter, the first occurrence wins and a warning is logged.

        At most MAX_METERS_PER_POLL meters are read per poll, within a total
        budget of METER_READ_TIME_BUDGET seconds, to bound the request load on
        the gateway. A failing meter is logged and skipped so readings from the
        other meters are still returned; only if every meter fails is the last
        error raised, so the coordinator keeps its usual failure handling.
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
            if len(meters) > MAX_METERS_PER_POLL:
                self.logger.warning(
                    "Gateway reports %d meters, reading only the first %d",
                    len(meters),
                    MAX_METERS_PER_POLL,
                )
                meters = meters[:MAX_METERS_PER_POLL]

            deadline = time.monotonic() + METER_READ_TIME_BUDGET
            last_error: Exception | None = None
            read_ok = 0
            for meter in meters:
                if time.monotonic() > deadline:
                    self.logger.warning(
                        "Meter read time budget of %ss exceeded, skipping remaining meters",
                        METER_READ_TIME_BUDGET,
                    )
                    break
                try:
                    meter_readings = await client.get_meter_reading(meter)
                except Exception as err:  # one meter must not break the others
                    self.logger.warning("Reading meter %s failed: %s", meter.mid, err)
                    last_error = err
                    continue
                read_ok += 1
                for obis, reading in meter_readings.items():
                    ts = self._as_aware(reading.timestamp)
                    if ts is not None and (last_ts is None or ts > last_ts):
                        last_ts = ts
                    if obis in readings:
                        self.logger.warning(
                            "OBIS %s reported by more than one meter, "
                            "keeping the first value (ignored meter %s)",
                            obis,
                            meter.mid,
                        )
                        continue
                    readings[obis] = Reading(
                        value=self._coerce_reading_value(reading.value),
                        timestamp=ts,
                        obis=obis,
                    )

            if read_ok == 0 and last_error is not None:
                raise last_error

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
