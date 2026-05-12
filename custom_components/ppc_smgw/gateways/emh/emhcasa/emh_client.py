from __future__ import annotations

from datetime import datetime, timezone

import httpx

from custom_components.ppc_smgw.gateways.reading import Information, OBISCode, Reading
from custom_components.ppc_smgw.obis import parse_obis

from ..const import DEFAULT_MODEL, DEFAULT_NAME, MANUFACTURER


class EMHCasaClient:
    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        httpx_client: httpx.AsyncClient,
        logger,
        meter_id: str | None = None,
    ):
        if not base_url.startswith(("http://", "https://")):
            base_url = f"https://{base_url}"
        if base_url.endswith("/") and not base_url.endswith("://"):
            base_url = base_url[:-1]
        self.base_url = base_url
        self.username = username
        self.password = password
        self.meter_id: str | None = meter_id or None

        self.httpx_client = httpx_client
        self.logger = logger

        self.httpx_client.headers.setdefault("Content-Type", "application/json")
        self.httpx_client.follow_redirects = True

    def _get_auth(self) -> httpx.DigestAuth:
        return httpx.DigestAuth(self.username, self.password)

    async def get_data(self) -> Information:
        information = Information(
            name=DEFAULT_NAME,
            model=DEFAULT_MODEL,
            manufacturer=MANUFACTURER,
            firmware_version="Unknown",
            last_update=datetime.now(timezone.utc),
            readings=await self._get_readings(),
        )

        self.logger.debug(f"Returning information: {information}")

        return information

    async def discover_all_meter_ids(self) -> list[str]:
        """Return all meter IDs available on this gateway via /json/metering/origin/."""
        self.logger.debug(f"Discovering all meter IDs from {self.base_url}")

        try:
            response = await self.httpx_client.get(
                f"{self.base_url}/json/metering/origin/",
                auth=self._get_auth(),
                timeout=10,
            )
            self.logger.debug(
                f"Got meter list: \nStatus code: {response.status_code}\nRaw response: {response.text}"
            )
            meter_ids: list[str] = response.json()
        except Exception as e:
            self.logger.error(f"Failed to fetch meter list: {e}")
            return []

        self.logger.debug(f"Discovered meter IDs: {meter_ids}")
        return meter_ids

    async def _discover_meter_id(self) -> str | None:
        meter_ids = await self.discover_all_meter_ids()
        if meter_ids:
            return meter_ids[0]
        self.logger.error("No meter ID found")
        return None

    async def _get_readings(self) -> dict[OBISCode, Reading]:
        self.logger.debug(f"Getting readings from {self.base_url}")

        if self.meter_id is None:
            self.meter_id = await self._discover_meter_id()
            if self.meter_id is None:
                self.logger.error("Could not discover meter ID")
                return {}

        try:
            response = await self.httpx_client.get(
                f"{self.base_url}/json/metering/origin/{self.meter_id}/extended",
                auth=self._get_auth(),
                timeout=10,
            )
            self.logger.debug(
                f"Got meter readings: \nStatus code: {response.status_code}\nRaw response: {response.text}"
            )
            meter_reading = response.json()
        except Exception as e:
            self.logger.error(f"Failed to fetch meter readings: {e}")
            return {}

        readings: dict[OBISCode, Reading] = {}
        now = datetime.now(timezone.utc)

        for meter_value in meter_reading.get("values", []):
            logical_name_hex = meter_value.get("logical_name", "").split(".")[0]
            parsed = parse_obis(logical_name_hex)
            if parsed is None:
                continue
            obis_code = parsed.to_obis_string()

            # Scale value and convert Wh (unit 30) to kWh
            scaler = meter_value.get("scaler", 0)
            unit = meter_value.get("unit", 0)
            value = float(meter_value["value"]) * (10**scaler)
            if unit == 30:
                value /= 1000

            readings[obis_code] = Reading(
                value=value,
                timestamp=now,
                obis=obis_code,
            )

        self.logger.debug(f"Parsed {len(readings)} readings: {list(readings.keys())}")
        return readings
