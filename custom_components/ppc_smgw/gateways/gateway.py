from __future__ import annotations

from abc import ABC, abstractmethod
import logging

import httpx

from custom_components.ppc_smgw.gateways.reading import Information


class Gateway(ABC):
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
        self.dynamic_obis_discovery_enabled = False
        self.data: Information | None = None

    async def check_connection(self) -> bool:
        # ToDO: Implement a basic connection check
        return True

    @abstractmethod
    async def get_data(self) -> Information:
        """Fetch data from the gateway."""

    async def reboot(self) -> None:
        """Reboot the gateway if supported."""
        raise NotImplementedError(
            f"Reboot is not supported on {self.__class__.__name__}"
        )
