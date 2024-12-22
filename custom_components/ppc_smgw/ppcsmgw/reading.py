from dataclasses import dataclass
from datetime import datetime

type OBISCode = str


@dataclass
class Reading:
    value: str
    unit: str
    timestamp: datetime
    isvalid: str
    name: str
    obis: str


@dataclass
class Information:
    readings: dict[OBISCode, Reading]
    firmware_version: str
    last_update: datetime


# FakeInformation contains a sample response from the API for development purposes
FakeInformation: Information = Information(
    readings={
        "1-0:1.8.0": Reading(
            value="724.9204",
            unit="kWh",
            timestamp=datetime(2024, 12, 20, 16, 0, 1),
            isvalid="1",
            name="Elektro Wirkarbeit Verbrauch Zählerstand",
            obis="1-0:1.8.0",
        ),
        "1-0:2.8.0": Reading(
            value="3.0557",
            unit="kWh",
            timestamp=datetime(2024, 12, 20, 16, 0, 1),
            isvalid="1",
            name="Elektro Wirkarbeit Erzeugung Zählerstand",
            obis="1-0:2.8.0",
        ),
        "1-1:1.7.0": Reading(
            value="1.234",
            unit="kW",  # TODO: needs to be checked
            timestamp=datetime(2024, 12, 20, 16, 0, 1),
            isvalid="1",
            name="Elektro-Wirkleistung Verbrauch Momentanwert",
            obis="1-1:1.7.0",
        ),
        "1-1:2.7.0": Reading(
            value="1.234",
            unit="kW",  # TODO: needs to be checked
            timestamp=datetime(2024, 12, 20, 16, 0, 1),
            isvalid="1",
            name="Elektro-Wirkleistung Erzeugung Momentanwert",
            obis="1-1:2.7.0",
        ),
    },
    firmware_version="1337-version",
    last_update=datetime(2024, 12, 20, 16, 0, 1),
)
