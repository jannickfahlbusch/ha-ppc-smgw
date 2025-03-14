import logging
import asyncio

import httpx
import urllib3

from custom_components.ppc_smgw import Gateway
from custom_components.ppc_smgw.gateways.reading import Information, FakeInformation
from custom_components.ppc_smgw.gateways.theben.thebenconnexa.thebenconnexa import (
    ThebenConnexaClient,
)

# Needed as the SMGW uses a self-signed certificate
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ThebenConnexa(Gateway):
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

        self.client = ThebenConnexaClient(
            base_url=host,
            username=username,
            password=password,
            httpx_client=websession,
            logger=logger,
        )

    async def get_data(self) -> Information:
        self.logger.info("Getting data")

        if self.debug:
            self.logger.debug("Debugging enabled, returning fake data")

            # It takes around 15 seconds for the GW to respond to all calls
            # We should emulate this here to avoid timing issues
            await asyncio.sleep(15)
            self.data = FakeInformation
        else:
            self.data = await self.client.get_data()

        return self.data
