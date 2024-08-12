
from bs4 import BeautifulSoup
import urllib3
from typing import List
import httpx

from .reading import Reading
from .errors import SessionCookieStillPresentError


# Needed as the PPC SMGW uses a self-signed certificate
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class PPC_SMGW:
    def __init__(self,
                 hass,
                 host: str,
                 username: str,
                 password: str,
                 websession,
                 logger) -> None:
        self.host = host
        self.username = username
        self.password = password
        self.websession = websession
        self.logger = logger
        self.hass = hass
        self._readings: List[Reading] = []

    async def async_update(self) -> None:
        self.logger.info("Updating data")
        return self.update()

    async def update(self) -> None:
        self.logger.info("Updating data")

        await self.get_data()

    async def check_connection(self) -> bool:
        # ToDo: Implement a basic connection check?
        return True

    # ToDo: This should be split into multiple smaller functions
    async def get_data(self) -> List[Reading]:
        self.logger.info("Getting data")

        auth = httpx.DigestAuth(username=self.username, password=self.password)
        self.websession.auth = auth

        # ToDo: Find a way to remove the cookie here!
        # See https://github.com/encode/httpx/pull/3065
        if 'session' in self.websession.cookies:
            self.logger.debug(f"Session cookie still present, trying to delete it")

            self.websession.cookies.delete("session")
            self.logger.debug(f"Deleted session cookie")

            if 'session' in self.websession.cookies:
                self.logger.error(f"Session cookie still present after deletion")
                raise SessionCookieStillPresentError

        try:
            response = await self.websession.get(self.host, timeout=10, auth=auth)
        except Exception as e:
            self.logger.error(f"Error connecting to {self.host}: {e}")
            return []

        cookies = { 'Cookie' : response.cookies['session']}

        self.logger.info(f"Got cookie response, assuming we are logged in")

        soup = BeautifulSoup(response.content, 'html.parser')
        tags = soup.find_all('input')
        token = tags[0].get('value')
        action = 'meterform'
        post_data = "tkn=" + token + "&action=" + action

        self.logger.info("Requesting meter readings")

        try:
            response = await self.websession.post(self.host, data=post_data, cookies=cookies, timeout=10, auth=auth)
        except Exception as e:
            self.logger.error(f"Error getting meter readings: {e}")
            return []

        self.logger.info("Got meter readings, parsing...")

        soup = BeautifulSoup(response.content, 'html.parser')
        sel = soup.find(id='meterform_select_meter')
        meter_val = sel.findChild()
        meter_id = meter_val.attrs.get('value')
        post_data = "tkn=" + token + "&action=showMeterProfile&mid=" + meter_id

        try:
            response = await self.websession.post(self.host, data=post_data, cookies=cookies, timeout=10, auth=auth)
        except Exception as e:
            self.logger.error(f"Error getting meter profile: {e}")
            return []

        soup = BeautifulSoup(response.content, 'html.parser')

        table_data = soup.find('table', id="metervalue")
        rows = table_data.find_all('tr')

        self.logger.info(f"Found {len(rows)} rows")

        timestamp = ""
        readings: List[Reading] = []

        for row in rows:
            obis_code = row.find(id="table_metervalues_col_obis")

            if obis_code is not None:

                self.logger.debug(f"Parsing row: {row}")

                # The SMGW returns the meter values in two rows, one for the consumption and one for the feed-in
                # We need to store the timestamp of the first row and use it for the second row
                current_timestamp = row.find(id="table_metervalues_col_timestamp")
                if current_timestamp is None:
                    current_timestamp = timestamp
                else:
                    timestamp = current_timestamp.string

                readings.append(Reading(
                    value = row.find(id="table_metervalues_col_wert").string,
                    unit = row.find(id="table_metervalues_col_einheit").string,
                    timestamp = current_timestamp,
                    isvalid = row.find(id="table_metervalues_col_istvalide").string,
                    name = row.find(id="table_metervalues_col_name").string,
                    obis = row.find(id="table_metervalues_col_obis").string
                ))

        # The PPC SMGW only allows a single session to be active at a time
        # Since we don't know the lifetime of the session, we should log out so that we are able to log back in later
        self.logger.info("trying to log out")
        action = 'logout'
        post_data = "tkn=" + token + "&action=" + action
        try:
            response= await self.websession.post(self.host, data=post_data, cookies=cookies, timeout=10, auth=auth)
            self.logger.debug(f"Got response: {response}")
            self.logger.debug(f"Got content: {response.content}")
        except Exception as e:
            self.logger.error(f"Error logging out: {e}")
            return []


        self.logger.info(f"Found {len(readings)} readings: {readings}")
        self._readings = readings
        return readings

    def get_reading_for_obis_code(self, obis_code: str) -> Reading | None:
        for reading in self._readings:
            if reading.obis == obis_code:
                return reading
        return None
