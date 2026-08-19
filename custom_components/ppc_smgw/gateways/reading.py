from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import math
import random

from obis_parser import OBIS


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
    last_update=datetime(2024, 12, 20, 16, 0, 1, tzinfo=UTC),
    readings={
        OBIS(1, 0, 1, 8, 0): Reading(
            value="724.9204",
            timestamp=datetime(2024, 12, 20, 16, 0, 1, tzinfo=UTC),
            obis=OBIS(1, 0, 1, 8, 0),
        ),
        OBIS(1, 0, 2, 8, 0): Reading(
            value="3.0557",
            timestamp=datetime(2024, 12, 20, 16, 0, 1, tzinfo=UTC),
            obis=OBIS(1, 0, 2, 8, 0),
        ),
    },
)


def build_fake_information() -> Information:
    now = datetime.now(UTC)
    rnd = random.SystemRandom()

    v_l1 = round(rnd.uniform(228.0, 232.0), 2)
    v_l2 = round(rnd.uniform(228.0, 232.0), 2)
    v_l3 = round(rnd.uniform(228.0, 232.0), 2)
    v_avg = round((v_l1 + v_l2 + v_l3) / 3, 2)

    p_l1 = round(rnd.uniform(50.0, 1200.0), 1)
    p_l2 = round(rnd.uniform(50.0, 1200.0), 1)
    p_l3 = round(rnd.uniform(50.0, 1200.0), 1)
    p_tot = round(p_l1 + p_l2 + p_l3, 1)

    i_l1 = round(p_l1 / v_l1, 2)
    i_l2 = round(p_l2 / v_l2, 2)
    i_l3 = round(p_l3 / v_l3, 2)
    i_tot = round(i_l1 + i_l2 + i_l3, 2)

    q_tot = round(rnd.uniform(10.0, 80.0), 1)
    s_tot = round(math.hypot(p_tot, q_tot), 1)
    pf = round(p_tot / s_tot if s_tot else 1.0, 3)
    freq = round(rnd.uniform(49.95, 50.05), 2)

    e_import = round(724.9204 + rnd.uniform(0.01, 0.05), 4)
    e_t1 = round(500.0000 + rnd.uniform(0.01, 0.03), 4)
    e_t2 = round(224.9204 + rnd.uniform(0.00, 0.02), 4)
    e_export = round(3.0557 + rnd.uniform(0.001, 0.005), 4)
    e_q_import = round(12.345 + rnd.uniform(0.001, 0.005), 3)
    e_q_export = round(1.234 + rnd.uniform(0.001, 0.003), 3)
    e_s = round(730.0 + rnd.uniform(0.01, 0.05), 1)

    return Information(
        name="TestName",
        model="TestModel",
        manufacturer="TestManufacturer",
        firmware_version="1337-version",
        last_update=now,
        readings={
            OBIS(1, 0, 1, 8, 0): Reading(
                value=e_import, timestamp=now, obis=OBIS(1, 0, 1, 8, 0)
            ),
            OBIS(1, 0, 1, 8, 1): Reading(
                value=e_t1, timestamp=now, obis=OBIS(1, 0, 1, 8, 1)
            ),
            OBIS(1, 0, 1, 8, 2): Reading(
                value=e_t2, timestamp=now, obis=OBIS(1, 0, 1, 8, 2)
            ),
            OBIS(1, 0, 2, 8, 0): Reading(
                value=e_export, timestamp=now, obis=OBIS(1, 0, 2, 8, 0)
            ),
            OBIS(1, 0, 3, 8, 0): Reading(
                value=e_q_import, timestamp=now, obis=OBIS(1, 0, 3, 8, 0)
            ),
            OBIS(1, 0, 4, 8, 0): Reading(
                value=e_q_export, timestamp=now, obis=OBIS(1, 0, 4, 8, 0)
            ),
            OBIS(1, 0, 9, 8, 0): Reading(
                value=e_s, timestamp=now, obis=OBIS(1, 0, 9, 8, 0)
            ),
            OBIS(1, 0, 1, 7, 0): Reading(
                value=p_tot, timestamp=now, obis=OBIS(1, 0, 1, 7, 0)
            ),
            OBIS(1, 0, 2, 7, 0): Reading(
                value=0.0, timestamp=now, obis=OBIS(1, 0, 2, 7, 0)
            ),
            OBIS(1, 0, 3, 7, 0): Reading(
                value=q_tot, timestamp=now, obis=OBIS(1, 0, 3, 7, 0)
            ),
            OBIS(1, 0, 4, 7, 0): Reading(
                value=0.0, timestamp=now, obis=OBIS(1, 0, 4, 7, 0)
            ),
            OBIS(1, 0, 9, 7, 0): Reading(
                value=s_tot, timestamp=now, obis=OBIS(1, 0, 9, 7, 0)
            ),
            OBIS(1, 0, 11, 7, 0): Reading(
                value=i_tot, timestamp=now, obis=OBIS(1, 0, 11, 7, 0)
            ),
            OBIS(1, 0, 12, 7, 0): Reading(
                value=v_avg, timestamp=now, obis=OBIS(1, 0, 12, 7, 0)
            ),
            OBIS(1, 0, 13, 7, 0): Reading(
                value=pf, timestamp=now, obis=OBIS(1, 0, 13, 7, 0)
            ),
            OBIS(1, 0, 14, 7, 0): Reading(
                value=freq, timestamp=now, obis=OBIS(1, 0, 14, 7, 0)
            ),
            OBIS(1, 0, 15, 7, 0): Reading(
                value=p_tot, timestamp=now, obis=OBIS(1, 0, 15, 7, 0)
            ),
            OBIS(1, 0, 16, 7, 0): Reading(
                value=p_tot, timestamp=now, obis=OBIS(1, 0, 16, 7, 0)
            ),
            OBIS(1, 0, 21, 7, 0): Reading(
                value=p_l1, timestamp=now, obis=OBIS(1, 0, 21, 7, 0)
            ),
            OBIS(1, 0, 22, 7, 0): Reading(
                value=0.0, timestamp=now, obis=OBIS(1, 0, 22, 7, 0)
            ),
            OBIS(1, 0, 31, 7, 0): Reading(
                value=i_l1, timestamp=now, obis=OBIS(1, 0, 31, 7, 0)
            ),
            OBIS(1, 0, 32, 7, 0): Reading(
                value=v_l1, timestamp=now, obis=OBIS(1, 0, 32, 7, 0)
            ),
            OBIS(1, 0, 36, 7, 0): Reading(
                value=p_l1, timestamp=now, obis=OBIS(1, 0, 36, 7, 0)
            ),
            OBIS(1, 0, 41, 7, 0): Reading(
                value=p_l2, timestamp=now, obis=OBIS(1, 0, 41, 7, 0)
            ),
            OBIS(1, 0, 42, 7, 0): Reading(
                value=0.0, timestamp=now, obis=OBIS(1, 0, 42, 7, 0)
            ),
            OBIS(1, 0, 51, 7, 0): Reading(
                value=i_l2, timestamp=now, obis=OBIS(1, 0, 51, 7, 0)
            ),
            OBIS(1, 0, 52, 7, 0): Reading(
                value=v_l2, timestamp=now, obis=OBIS(1, 0, 52, 7, 0)
            ),
            OBIS(1, 0, 56, 7, 0): Reading(
                value=p_l2, timestamp=now, obis=OBIS(1, 0, 56, 7, 0)
            ),
            OBIS(1, 0, 61, 7, 0): Reading(
                value=p_l3, timestamp=now, obis=OBIS(1, 0, 61, 7, 0)
            ),
            OBIS(1, 0, 62, 7, 0): Reading(
                value=0.0, timestamp=now, obis=OBIS(1, 0, 62, 7, 0)
            ),
            OBIS(1, 0, 71, 7, 0): Reading(
                value=i_l3, timestamp=now, obis=OBIS(1, 0, 71, 7, 0)
            ),
            OBIS(1, 0, 72, 7, 0): Reading(
                value=v_l3, timestamp=now, obis=OBIS(1, 0, 72, 7, 0)
            ),
            OBIS(1, 0, 76, 7, 0): Reading(
                value=p_l3, timestamp=now, obis=OBIS(1, 0, 76, 7, 0)
            ),
            OBIS(1, 1, 1, 8, 0): Reading(
                value=150.0, timestamp=now, obis=OBIS(1, 1, 1, 8, 0)
            ),
        },
    )
