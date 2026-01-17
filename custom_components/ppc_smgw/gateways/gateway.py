from custom_components.ppc_smgw.gateways.reading import Information
import logging

import httpx


class Gateway:
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

    async def check_connection(self) -> bool:
        # ToDO: Implement a basic connection check
        return True

    async def get_data(self) -> Information:
        pass

    async def reboot(self):
        pass
