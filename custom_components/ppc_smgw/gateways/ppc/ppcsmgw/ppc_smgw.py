"""PPC SMGW API."""

import asyncio
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from .errors import SessionCookieStillPresentError
from ..const import DEFAULT_NAME, DEFAULT_MODEL, MANUFACTURER
from custom_components.ppc_smgw.gateways.reading import Reading, Information, OBISCode

from homeassistant.util.dt import now


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

        self._cookies: dict | None = None
        self._token = ""
        self._use_digest_only = False

        self.firmware_version = None

    def _post_data(self, action):
        if self._use_digest_only and not self._token:
            return f"action={action}"
        return f"tkn={self._token}&action={action}"

    def _request_kwargs(self, timeout: int = 10) -> dict:
        """Build common kwargs for authenticated requests."""
        kwargs = {"timeout": timeout, "auth": self._auth}
        if self._cookies is not None:
            kwargs["cookies"] = self._cookies
        return kwargs

    async def _login(self):
        self.logger.info("Attempting to login to PPC SMGW")

        # Fresh DigestAuth per poll cycle — the gateway's CGI architecture has no
        # persistent nonce state, so reusing a stale nonce from 15 minutes ago fails.
        # Within a single get_data() session the nonce is reused (login→posts→logout).
        self._auth = httpx.DigestAuth(username=self.username, password=self.password)

        # Clear session state upfront so no stale credentials survive any failure path
        self._cookies = None
        self._token = ""
        self._use_digest_only = False

        # TODO: Find a way to remove the cookie here!
        # See https://github.com/encode/httpx/pull/3065
        if self.httpx_client.cookies.get(name="session") is not None:
            self.logger.debug("Session cookie still present, trying to delete it")

            self.httpx_client.cookies.delete(name="session")
            self.logger.debug("Deleted session cookie")

            if "session" in self.httpx_client.cookies:
                self.logger.error("Session cookie still present after deletion")
                raise SessionCookieStillPresentError

        try:
            response = await self.httpx_client.get(
                self.host,
                timeout=10,
                auth=self._auth,
            )
        except Exception as e:
            msg = f"Error connecting to {self.host}: {e}"
            self.logger.error(msg)
            raise ConnectionError(msg) from e

        # Some gateways (e.g. SMGW-K-2B-111-10) use pure Digest auth without
        # issuing a session cookie. If we got HTTP 200, auth succeeded regardless.
        if response.status_code != 200:
            msg = f"Login to {self.host} failed: HTTP {response.status_code}"
            self.logger.error(msg)
            raise ConnectionError(msg)

        if "session" in response.cookies:
            self._cookies = {"Cookie": response.cookies["session"]}
            self._use_digest_only = False
        else:
            # Stateless Digest auth — no cookie, rely on self._auth for requests
            self.logger.info(
                "No session cookie returned (HTTP 200); using stateless Digest auth"
            )
            self._cookies = None
            self._use_digest_only = True

        soup = await asyncio.to_thread(BeautifulSoup, response.content, "html.parser")
        tags = soup.find_all("input")
        if not tags:
            if not self._use_digest_only:
                # Cookie-based gateways must provide a CSRF token
                msg = f"Login to {self.host} failed: no CSRF token found in response"
                self.logger.error(msg)
                raise ConnectionError(msg)
            # Stateless Digest gateways may not use CSRF tokens
            self._token = ""
        else:
            self._token = tags[0].get("value")

        self.logger.info("Login successful")

        return response

    def _set_firwmware_version(self, soup) -> None:
        self.firmware_version = soup.find(id="div_fwversion").get_text().strip()

    async def get_data(self) -> Information:
        await self._login()

        self.logger.info("Requesting meter readings")

        try:
            response = await self.httpx_client.post(
                self.host,
                data=self._post_data("meterform"),
                **self._request_kwargs(),
            )
        except Exception as e:
            self.logger.error(f"Error getting meter readings: {e}")
            return []

        self.logger.info("Got meter readings, parsing...")

        soup = await asyncio.to_thread(BeautifulSoup, response.content, "html.parser")

        self._set_firwmware_version(soup)

        sel = soup.find(id="meterform_select_meter")
        if sel is None:
            self.logger.error(
                "Meter form not found in response — the gateway may have rejected the request. "
                f"Response length: {len(response.content)} bytes"
            )
            self.logger.debug(f"Response content: {response.content}")
            await self._logout()
            raise ConnectionError(
                f"Unexpected response from {self.host}: meter form not found"
            )
        meter_val = sel.findChild()
        meter_id = meter_val.attrs.get("value")
        post_data = self._post_data("showMeterProfile") + f"&mid={meter_id}"

        try:
            response = await self.httpx_client.post(
                self.host,
                data=post_data,
                **self._request_kwargs(),
            )
        except Exception as e:
            self.logger.error(f"Error getting meter profile: {e}")
            return []

        soup = await asyncio.to_thread(BeautifulSoup, response.content, "html.parser")

        table_data = soup.find("table", id="metervalue")
        rows = table_data.find_all("tr")

        self.logger.info(f"Found {len(rows)} rows")

        timestamp = ""

        readings: dict[OBISCode, Reading] = {}

        for row in rows:
            obis_code = row.find(id="table_metervalues_col_obis")

            if obis_code is not None:
                self.logger.debug(f"Parsing row: {row}")

                # The SMGW returns the meter values in two rows, one for the consumption and one for the feed-in
                # We need to store the timestamp of the first row and use it for the second row
                row_timestamp = row.find(id="table_metervalues_col_timestamp")
                if row_timestamp is None:
                    current_timestamp = timestamp

                    self.logger.debug(
                        f"Timestamp not found, using previous: {current_timestamp}"
                    )
                else:
                    self.logger.debug(f"Found timestamp: {row_timestamp.string}")
                    current_timestamp = datetime.strptime(
                        row_timestamp.string, "%Y-%m-%d %H:%M:%S"
                    ).replace(tzinfo=now().tzinfo)
                    timestamp = current_timestamp

                obis_code = row.find(id="table_metervalues_col_obis").string

                readings[obis_code] = Reading(
                    value=row.find(id="table_metervalues_col_wert").string,
                    timestamp=current_timestamp,
                    obis=obis_code,
                )

        await self._logout()

        self.logger.info(f"Found {len(readings)} readings")
        self.logger.debug(f"Readings:\n{readings}")

        information: Information = Information(
            name=DEFAULT_NAME,
            model=DEFAULT_MODEL,
            manufacturer=MANUFACTURER,
            firmware_version=self.firmware_version,
            last_update=timestamp,
            readings=readings,
        )

        return information

    async def _logout(self):
        # The PPC SMGW only allows a single session to be active at a time
        # Since we don't know the lifetime of the session, we should log out so that we are able to log back in later
        self.logger.info("trying to log out")

        try:
            response = await self.httpx_client.post(
                self.host,
                data=self._post_data("logout"),
                **self._request_kwargs(),
            )
            self.logger.debug(f"Got response: {response}\nContent: {response.content}")

        except Exception as e:
            self._cookies = None
            self._token = ""

            self.logger.error(f"Error logging out: {e}")
            return []

    async def selftest(self):
        """Call the self-test of the SMWG. This reboots the SMGW."""
        self.logger.info("Running self-test")
        await self._login()

        self.logger.info("Requesting self-test")

        self.logger.debug(f"Post data: {self._post_data('selftest')}")
        response = await self.httpx_client.post(
            self.host,
            data=self._post_data("selftest"),
            **self._request_kwargs(),
        )

        self.logger.debug(f"Got response: {response}\nContent: {response.content}")

    async def reboot(self):
        """Reboots the SMGW through a Self-Test."""
        return await self.selftest()
