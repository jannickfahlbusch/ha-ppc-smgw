import urllib3

from .ppcsmgw.ppc_smgw import PPCSmgw
from .ppcsmgw.reading import Reading

# Needed as the PPC SMGW uses a self-signed certificate
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class PPC_SMGW:
    def __init__(
        self, hass, host: str, username: str, password: str, websession, logger
    ) -> None:
        self.host = host
        self.username = username
        self.password = password
        self.websession = websession
        self.logger = logger
        self.hass = hass
        self._readings: list[Reading] = []

        self.ppc_smgw_client = PPCSmgw(
            host=host,
            username=username,
            password=password,
            httpx_client=websession,
            logger=logger,
        )

    async def async_update(self) -> None:
        self.logger.info("Updating data")
        return self.update()

    async def update(self) -> None:
        self.logger.info("Updating data")

        await self.ppc_smgw_client.get_data()

        await self.get_data()

    async def check_connection(self) -> bool:
        # ToDo: Implement a basic connection check?
        return True

    # ToDo: This should be split into multiple smaller functions
    async def get_data(self) -> list[Reading]:
        self.logger.info("Getting data")

        self._readings = await self.ppc_smgw_client.get_data()

        return self._readings

    def get_reading_for_obis_code(self, obis_code: str) -> Reading | None:
        for reading in self._readings:
            if reading.obis == obis_code:
                return reading
        return None

    def get_readings(self) -> list[Reading]:
        """Return all readings."""
        return self._readings
