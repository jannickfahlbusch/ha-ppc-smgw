"""PPC SMGW API."""

from datetime import datetime

from bs4 import BeautifulSoup
import httpx

from .errors import SessionCookieStillPresentError
from .reading import Reading


class PPCSmgw:
    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        httpx_client: httpx.AsyncClient,
        logger,
    ):
        self.host = host
        self.username = username
        self.password = password

        self.httpx_client = httpx_client
        self.logger = logger

        self._cookies = {}
        self._token = ""

    def _get_auth(self):
        auth = httpx.DigestAuth(username=self.username, password=self.password)
        self.httpx_client.auth = auth

        return auth

    def _post_data(self, action):
        return f"tkn={self._token}&action={action}"

    async def _login(self):
        self.logger.info("Getting data")

        auth = httpx.DigestAuth(username=self.username, password=self.password)
        self.httpx_client.auth = auth

        # ToDo: Find a way to remove the cookie here!
        # See https://github.com/encode/httpx/pull/3065
        if "session" in self.httpx_client.cookies:
            self.logger.debug("Session cookie still present, trying to delete it")

            self.httpx_client.cookies.delete("session")
            self.logger.debug("Deleted session cookie")

            if "session" in self.httpx_client.cookies:
                self.logger.error("Session cookie still present after deletion")
                raise SessionCookieStillPresentError

        try:
            response = await self.httpx_client.get(
                self.host,
                timeout=10,
                auth=self._get_auth(),
            )
        except Exception as e:
            self.logger.error(f"Error connecting to {self.host}: {e}")
            return []

        self._cookies = {"Cookie": response.cookies["session"]}

        soup = BeautifulSoup(response.content, "html.parser")
        tags = soup.find_all("input")
        self._token = tags[0].get("value")

        self.logger.info("Got cookie response, assuming we are logged in")

        return response

    async def get_data(self):
        await self._login()

        self.logger.info("Requesting meter readings")

        try:
            response = await self.httpx_client.post(
                self.host,
                data=self._post_data("meterform"),
                cookies=self._cookies,
                timeout=10,
                auth=self._get_auth(),
            )
        except Exception as e:
            self.logger.error(f"Error getting meter readings: {e}")
            return []

        self.logger.info("Got meter readings, parsing...")

        soup = BeautifulSoup(response.content, "html.parser")
        sel = soup.find(id="meterform_select_meter")
        meter_val = sel.findChild()
        meter_id = meter_val.attrs.get("value")
        post_data = self._post_data("showMeterProfile") + f"&mid={meter_id}"

        try:
            response = await self.httpx_client.post(
                self.host,
                data=post_data,
                cookies=self._cookies,
                timeout=10,
                auth=self._get_auth(),
            )
        except Exception as e:
            self.logger.error(f"Error getting meter profile: {e}")
            return []

        soup = BeautifulSoup(response.content, "html.parser")

        table_data = soup.find("table", id="metervalue")
        rows = table_data.find_all("tr")

        self.logger.info(f"Found {len(rows)} rows")

        timestamp = ""
        readings: list[Reading] = []

        for row in rows:
            obis_code = row.find(id="table_metervalues_col_obis")

            if obis_code is not None:
                self.logger.debug(f"Parsing row: {row}")

                # The SMGW returns the meter values in two rows, one for the consumption and one for the feed-in
                # We need to store the timestamp of the first row and use it for the second row
                row_timestamp = row.find(id="table_metervalues_col_timestamp")
                if row_timestamp is None:
                    current_timestamp = timestamp

                    self.logger.debug(f"Timestamp not found, using previous: {current_timestamp}")
                else:
                    self.logger.debug(f"Found timestamp: {row_timestamp.string}")
                    current_timestamp = datetime.strptime(
                        row_timestamp.string, "%Y-%m-%d %H:%M:%S"
                    )
                    timestamp = current_timestamp

                readings.append(
                    Reading(
                        value=row.find(id="table_metervalues_col_wert").string,
                        unit=row.find(id="table_metervalues_col_einheit").string,
                        timestamp=current_timestamp,
                        isvalid=row.find(id="table_metervalues_col_istvalide").string,
                        name=row.find(id="table_metervalues_col_name").string,
                        obis=row.find(id="table_metervalues_col_obis").string,
                    )
                )

        await self._logout()

        self.logger.info(f"Found {len(readings)} readings")
        self.logger.debug(f"Readings:\n{readings}")

        return readings

    async def _logout(self):
        # The PPC SMGW only allows a single session to be active at a time
        # Since we don't know the lifetime of the session, we should log out so that we are able to log back in later
        self.logger.info("trying to log out")

        try:
            response = await self.httpx_client.post(
                self.host,
                data=self._post_data("logout"),
                cookies=self._cookies,
                timeout=10,
                auth=self._get_auth(),
            )
            self.logger.debug(f"Got response: {response}\nContent: {response.content}")

        except Exception as e:
            self._cookies = {}
            self._token = ""

            self.logger.error(f"Error logging out: {e}")
            return []

    async def selftest(self):
        """Call the self-test of the SMWG. This reboots the SMGW."""

        self.logger.info("Running self-test")
        await self._login()

        self.logger.info("Requesting self-test")

        auth = self._get_auth()
        self.logger.debug(f"Post data: {self._post_data('selftest')}")
        response = await self.httpx_client.post(
            self.host,
            data=self._post_data("selftest"),
            cookies=self._cookies,
            timeout=10,
            auth=self._get_auth(),
        )

        self.logger.debug(f"Got response: {response}\nContent: {response.content}")

    async def reboot(self):
        """Reboots the SMGW through a Self-Test."""
        return await self.selftest()
