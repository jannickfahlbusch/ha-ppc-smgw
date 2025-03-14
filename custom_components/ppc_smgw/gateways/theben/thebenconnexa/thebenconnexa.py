import httpx

from custom_components.ppc_smgw.gateways.reading import Information


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

    def get_data(self) -> Information:
        # ToDO: Implement me
        self.logger.debug(
            f"Would fetch data from {self.base_url} if this would be implemented"
        )
        return Information()
