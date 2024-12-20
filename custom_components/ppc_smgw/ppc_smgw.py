import logging

import httpx
import urllib3

from .ppcsmgw.ppc_smgw import PPCSmgw
from .ppcsmgw.reading import Information, FakeInformation

# Needed as the PPC SMGW uses a self-signed certificate
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class PPC_SMGW:
    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        websession: httpx.AsyncClient,
        logger: logging.Logger,
        debug: bool = False,
    ) -> None:
        self.host = host
        self.username = username
        self.password = password
        self.websession = websession
        self.logger = logger
        self.debug = debug
        self.data: Information

        self.ppc_smgw_client = PPCSmgw(
            host=host,
            username=username,
            password=password,
            httpx_client=websession,
            logger=logger,
        )

    async def check_connection(self) -> bool:
        # TODO: Implement a basic connection check?
        return True

    # TODO: This should be split into multiple smaller functions
    async def get_data(self) -> Information:
        self.logger.info("Getting data")

        if self.debug:
            self.logger.debug("Debugging enabled, returning fake data")
            self.data = FakeInformation
        else:
            self.data = await self.ppc_smgw_client.get_data()

        return self.data
