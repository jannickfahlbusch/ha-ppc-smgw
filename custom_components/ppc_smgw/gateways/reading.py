from dataclasses import dataclass
from datetime import datetime

from obis_parser import OBIS
import pytz


@dataclass
class Reading:
    value: str | float
    timestamp: datetime
    obis: OBIS


@dataclass
class Information:
    name: str
    model: str
    manufacturer: str
    firmware_version: str
    last_update: datetime
    readings: dict[OBIS, Reading]


# FakeInformation contains a sample response from the API for development purposes
FakeInformation: Information = Information(
    name="TestName",
    model="TestModel",
    manufacturer="TestManufacturer",
    firmware_version="1337-version",
    last_update=datetime(2024, 12, 20, 16, 0, 1, tzinfo=pytz.UTC),
    readings={
        OBIS(1, 0, 1, 8, 0): Reading(
            value="724.9204",
            timestamp=datetime(2024, 12, 20, 16, 0, 1, tzinfo=pytz.UTC),
            obis=OBIS(1, 0, 1, 8, 0),
        ),
        OBIS(1, 0, 2, 8, 0): Reading(
            value="3.0557",
            timestamp=datetime(2024, 12, 20, 16, 0, 1, tzinfo=pytz.UTC),
            obis=OBIS(1, 0, 2, 8, 0),
        ),
    },
)
