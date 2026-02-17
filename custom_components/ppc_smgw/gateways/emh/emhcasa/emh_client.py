import httpx

from custom_components.ppc_smgw.const import (
    EMH_DEFAULT_NAME,
    EMH_MANUFACTURER,
    EMH_DEFAULT_MODEL,
)
from custom_components.ppc_smgw.gateways.reading import Information, OBISCode, Reading
from datetime import datetime, timezone


class EMHCasaClient:
    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        httpx_client: httpx.AsyncClient,
        logger,
    ):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.meter_id: str | None = None

        self.httpx_client = httpx_client
        self.logger = logger

        self.httpx_client.headers.setdefault("Content-Type", "application/json")
        self.httpx_client.follow_redirects = True

    def _get_auth(self) -> httpx.DigestAuth:
        return httpx.DigestAuth(self.username, self.password)

    async def get_data(self) -> Information:
        information = Information(
            name=EMH_DEFAULT_NAME,
            model=EMH_DEFAULT_MODEL,
            manufacturer=EMH_MANUFACTURER,
            firmware_version="Unknown",
            last_update=datetime.now(timezone.utc),
            readings=await self._get_readings(),
        )

        self.logger.debug(f"Returning information: {information}")

        return information

    async def _discover_meter_id(self) -> str | None:
        self.logger.debug(f"Discovering meter ID from {self.base_url}")

        try:
            response = await self.httpx_client.get(
                f"{self.base_url}/json/metering/derived",
                auth=self._get_auth(),
                timeout=10,
            )
            self.logger.debug(
                f"Got contract list: \nStatus code: {response.status_code}\nRaw response: {response.text}"
            )
            contract_ids = response.json()
        except Exception as e:
            self.logger.error(f"Failed to fetch contract list: {e}")
            return None

        for contract_id in contract_ids:
            try:
                response = await self.httpx_client.get(
                    f"{self.base_url}/json/metering/derived/{contract_id}",
                    auth=self._get_auth(),
                    timeout=10,
                )
                contract = response.json()
                self.logger.debug(f"Contract {contract_id}: {contract}")

                sensor_domains = contract.get("sensor_domains", [])
                if sensor_domains:
                    self.logger.debug(
                        f"Found meter ID: {sensor_domains[0]} from contract {contract_id}"
                    )
                    return sensor_domains[0]
            except Exception as e:
                self.logger.error(f"Failed to fetch contract {contract_id}: {e}")

        self.logger.error("No meter ID found in any contract")
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
            logical_name = meter_value.get("logical_name", "")
            if len(logical_name) != 12:
                continue

            # Convert hex logical name to OBIS code (e.g. '0100010800FF' -> '1-0:1.8.0')
            c = int(logical_name[4:6], 16)
            d = int(logical_name[6:8], 16)
            e = int(logical_name[8:10], 16)
            obis_code = f"1-0:{c}.{d}.{e}"

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
