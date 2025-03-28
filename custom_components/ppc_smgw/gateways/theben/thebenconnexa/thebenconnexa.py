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

    async def _get_readings(self) -> dict[OBISCode, Reading]:
        # ToDo: Implement me
        return {}

    async def _get_firmware_version(self) -> str:
        self.logger.debug(f"Getting firmware version from {self.base_url}")

        try:
            response = await self.httpx_client.post(
                self.base_url,
                auth=self._get_auth(),
                timeout=10,
                data={"method": "smgw-info"},
            )
        except Exception as e:
            self.logger.error(f"Failed to fetch firmware version: {e}")
            return "Unknown"

        smgw_info = response.json()

        self.logger.debug(
            f"Got firmware info response: \nStatus code: {response.status_code}\nRaw response: {response.text}"
        )

        try:
            return f"{smgw_info['smgw-info']['firmware-info']['version']}-{smgw_info['smgw-info']['firmware-info']['hash']}"
        except KeyError as e:
            self.logger.error(
                f"Failed to get firmware info: {e}.\nReponse from SMGW: {response.json()}"
            )

        return "Unknown"
