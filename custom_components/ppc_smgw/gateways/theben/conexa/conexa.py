import httpx

from custom_components.ppc_smgw.const import (
    THEBEN_DEFAULT_NAME,
    THEBEN_MANUFACTURER,
    THEBEN_DEFAULT_MODEL,
)
from custom_components.ppc_smgw.gateways.reading import Information, OBISCode, Reading
from datetime import datetime, timezone


class ThebenConexaClient:
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
            name=THEBEN_DEFAULT_NAME,
            model=THEBEN_DEFAULT_MODEL,
            manufacturer=THEBEN_MANUFACTURER,
            firmware_version=await self._get_firmware_version(),
            last_update=datetime.now(timezone.utc),
            readings=await self._get_readings(),
        )

        self.logger.debug(f"Returning information: {information}")

        return information

    # Retrieve list of usage point IDs
    async def _get_usage_point_ids(self) -> list[str]:
        self.logger.debug(f"Getting user info from {self.base_url}")

        try:
            response = await self.httpx_client.post(
                self.base_url,
                auth=self._get_auth(),
                timeout=10,
                json={"method": "user-info"},
            )
            self.logger.debug(
                f"Got user info: \nStatus code: {response.status_code}\nRaw response: {response.text}"
            )
            usage_json = response.json()
        except Exception as e:
            self.logger.error(f"Failed to fetch usage point ID: {e}")
            return ""

        usage_points_json = usage_json["user-info"]["usage-points"]
        self.logger.debug(f"Received {len(usage_points_json)} usage points.")
        usage_point_ids = []
        # If there are multiple, prefer the ones with
        # "taf-state": "running" and "taf-number": "7"
        for x in usage_points_json:
            if x["taf-state"] == "running" and x["taf-number"] == "7":
                usage_point_ids.append(x["usage-point-id"])

        if len(usage_point_ids) == 0:
            for x in usage_points_json:
                if x["taf-state"] == "running":
                    usage_point_ids.append(x["usage-point-id"])

        if len(usage_point_ids) == 0:
            self.logger.error("No usage point found with state 'running'")
            return ""

        self.logger.debug(
            f"Using {len(usage_point_ids)} usage point ids: {usage_point_ids}"
        )
        return usage_point_ids

    async def _get_readings(self) -> dict[OBISCode, Reading]:
        self.logger.debug(f"Getting readings from {self.base_url}")

        usage_point_ids = await self._get_usage_point_ids()
        if usage_point_ids is None or len(usage_point_ids) == 0:
            self.logger.error("No usage point ID found")
            return {}

        readings: dict[OBISCode, Reading] = {}

        for id in usage_point_ids:
            try:
                response = await self.httpx_client.post(
                    self.base_url,
                    auth=self._get_auth(),
                    timeout=10,
                    json={
                        "method": "readings",
                        "database": "origin",
                        "usage-point-id": id,
                        "last-reading": "true",
                    },
                )
                self.logger.debug(
                    f"Got readings for usage point id '{id}': \nStatus code: {response.status_code}\nRaw response: {response.text}"
                )
                res_json = response.json()
            except Exception as e:
                self.logger.error(f"Failed to fetch reading: {e}")

            for channel in res_json["readings"]["channels"]:
                ch_readings = channel["readings"]
                if len(ch_readings) == 0:
                    self.logger.error("No reading found.")
                elif len(ch_readings) > 1:
                    self.logger.error(
                        "Too many readings found. Only support one at a time right now."
                    )

                obis_hex = channel["obis"]
                if obis_hex == "0100010800ff":
                    obis_code = "1-0:1.8.0"
                elif obis_hex == "0100020800ff":
                    obis_code = "1-0:2.8.0"
                else:
                    self.logger.error("No or unknown OBIS code.")

                # So far, this logic only supports one reading per channel at once
                reading = ch_readings[0]
                readings[obis_code] = Reading(
                    value=(
                        float(reading["value"]) / 10000
                    ),  # Watts of value? deciWatts!
                    timestamp=reading["capture-time"],
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
            fw_version = smgw_info["smgw-info"]["firmware-info"]["version"]
            fw_hash = smgw_info["smgw-info"]["firmware-info"]["hash"]
            # It's not necessary to render the 64 characters long hash. For comparison the first 8 letters are sufficient.
            return f"{fw_version}-{fw_hash:.8}"
        except KeyError as e:
            self.logger.error(
                f"Failed to get firmware info: {e}.\nReponse from SMGW: {response.json()}"
            )

        return "Unknown"
