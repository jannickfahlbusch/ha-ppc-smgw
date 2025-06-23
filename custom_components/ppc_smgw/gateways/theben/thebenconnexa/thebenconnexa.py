import httpx

from custom_components.ppc_smgw.gateways.reading import Information, OBISCode, Reading
from datetime import datetime


class ThebenConnexaClient:
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

        self.httpx_client = httpx_client
        self.logger = logger

        self.httpx_client.headers.setdefault("Content-Type", "application/json")
        self.httpx_client.follow_redirects = True

    def _get_auth(self) -> httpx.DigestAuth:
        auth = httpx.DigestAuth(self.username, self.password)
        self.httpx_client.auth = auth

        return auth

    async def get_data(self) -> Information:
        information = Information(
            firmware_version=await self._get_firmware_version(),
            readings=await self._get_readings(),
            last_update=datetime.now(),
        )

        self.logger.debug(f"Returning information: {information}")

        return information

    # Retrieve 7-digit usage point ID
    async def _get_usage_point_id(self) -> str:
        self.logger.debug(f"Getting usage point ID from {self.base_url}")

        try:
            response = await self.httpx_client.post(
                self.base_url,
                auth=self._get_auth(),
                timeout=10,
                json={"method": "user-info"},
            )
            self.logger.debug(
                f"Got usage point ID: \nStatus code: {response.status_code}\nRaw response: {response.text}"
            )
            usage_json = response.json()
        except Exception as e:
            self.logger.error(f"Failed to fetch usage point ID: {e}")
            return ""
        
        usage_points = usage_json["user-info"]["usage-points"]

        # If there are multiple ones, find the one with "taf-state" being "running"
        usage_point = find(lambda x: x["taf-state"] == "running", usage_points)
        if usage_point is None:
            self.logger.error("No usage point found with state 'running'")
            return ""

        usage_point_id = usage_point["usage-point-id"]
        return usage_point_id

    async def _get_readings(self) -> dict[OBISCode, Reading]:
        self.logger.debug(f"Getting readings from {self.base_url}")

        usage_point_id = await self._get_usage_point_id()
        if usage_point_id is None or len(usage_point_id) == 0:
            self.logger.error("No usage point ID found")
            return {}

        try:
            response = await self.httpx_client.post(
                self.base_url,
                auth=self._get_auth(),
                timeout=10,
                json={
                    "method": "readings",
                    "database": "origin",
                    "usage-point-id": usage_point_id,
                    "last-reading": "true"
                },
            )
            self.logger.debug(
                f"Got readings: \nStatus code: {response.status_code}\nRaw response: {response.text}"
            )
            readings_json = response.json()
        except Exception as e:
            self.logger.error(f"Failed to fetch readings: {e}")
            return {}

        readings: dict[OBISCode, Reading] = {}
        for channel in readings_json["readings"]["channels"]:
            obis_code = channel["obis"]
            readings = channel["readings"]
            if obis_code is None or len(readings) == 0:
                self.logger.error("No OBIS code or no reading found.")
            elif len(readings) > 1:
                self.logger.error("Too many readings found. Only support one at a time right now.")
            else:
                # So far, this logic only supports one reading per channel at once
                reading = readings[0]
                readings[obis_code] = Reading(
                    value=reading["value"],
                    timestamp=reading["capture-time"],
                    unit="kWh",
                    isvalid="1",
                    # Only considering usage for the moment
                    name="Verbrauch",
                    obis=obis_code,
                )
        return readings

    async def _get_firmware_version(self) -> str:
        self.logger.debug(f"Getting firmware version from {self.base_url}")

        try:
            response = await self.httpx_client.post(
                self.base_url,
                auth=self._get_auth(),
                timeout=10,
                # TODO: Requires setting the header "X-Content-Length" manually (equals body length)
                json={"method": "smgw-info"},
            )

            self.logger.debug(
                f"Got firmware info response: \nStatus code: {response.status_code}\nRaw response: {response.text}"
            )

            smgw_info = response.json()
        except Exception as e:
            self.logger.error(f"Failed to fetch firmware version: {e}")
            return "Unknown"

        try:
            fw_version = smgw_info['smgw-info']['firmware-info']['version']
            fw_hash = smgw_info['smgw-info']['firmware-info']['hash']
            # It's not necessary to render the 64 characters long hash. For comparison the first 8 letters are sufficient.
            return f"{fw_version}-{fw_hash:.8}"
        except KeyError as e:
            self.logger.error(
                f"Failed to get firmware info: {e}.\nReponse from SMGW: {response.json()}"
            )

        return "Unknown"
