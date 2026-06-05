"""OBIS code parser and measurement catalog for smart meter gateways.

Supports three wire formats used by the supported gateways:
  - String format (PPC): "1-0:1.8.0" or "1-0:1.8.0*255"
  - COSEM hex (EMH, Theben): "0100010800ff" (12 hex chars)
  - Dot-separated hex: "01.00.01.08.00.FF"
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
)

_OBIS_STRING_RE = re.compile(r"^(\d+)-(\d+):(\d+)\.(\d+)\.(\d+)(?:\*(\d+))?$")
_OBIS_DOT_HEX_RE = re.compile(
    r"^([0-9a-fA-F]{2})\.([0-9a-fA-F]{2})\.([0-9a-fA-F]{2})\."
    r"([0-9a-fA-F]{2})\.([0-9a-fA-F]{2})\.([0-9a-fA-F]{2})$"
)

# Phase angle sub-identifiers (C=81, D=7): E encodes a specific angle pair
PHASE_ANGLE_NAMES: dict[int, str] = {
    1: "Phase angle U(L2)-U(L1)",
    2: "Phase angle U(L3)-U(L1)",
    4: "Phase angle I(L1)-U(L1)",
    15: "Phase angle I(L2)-U(L2)",
    26: "Phase angle I(L3)-U(L3)",
}


@dataclass(frozen=True)
class ParsedOBIS:
    a: int  # medium (1 = electricity)
    b: int  # channel (0 = default, 1+ = sub-meter)
    c: int  # measurement type
    d: int  # measurement detail
    e: int  # tariff/period
    f: int | None = None

    def to_obis_string(self) -> str:
        base = f"{self.a}-{self.b}:{self.c}.{self.d}.{self.e}"
        if self.f is not None and self.f != 255:
            base += f"*{self.f}"
        return base


@dataclass(frozen=True)
class OBISMeasurementInfo:
    name: str
    device_class: SensorDeviceClass | None
    state_class: SensorStateClass | None
    unit: str | None
    icon: str
    suggested_display_precision: int | None = None


OBIS_CATALOG: dict[tuple[int, int], OBISMeasurementInfo] = {
    # Energy cumulative (D=8)
    (1, 8): OBISMeasurementInfo(
        "Active import energy",
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL_INCREASING,
        UnitOfEnergy.KILO_WATT_HOUR,
        "mdi:home-import-outline",
        5,
    ),
    (2, 8): OBISMeasurementInfo(
        "Active export energy",
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL_INCREASING,
        UnitOfEnergy.KILO_WATT_HOUR,
        "mdi:home-export-outline",
        5,
    ),
    (3, 8): OBISMeasurementInfo(
        "Reactive import energy",
        None,
        SensorStateClass.TOTAL_INCREASING,
        "kvarh",
        "mdi:flash",
    ),
    (4, 8): OBISMeasurementInfo(
        "Reactive export energy",
        None,
        SensorStateClass.TOTAL_INCREASING,
        "kvarh",
        "mdi:flash-outline",
    ),
    # Power instantaneous (D=7)
    (1, 7): OBISMeasurementInfo(
        "Active import power",
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
        UnitOfPower.WATT,
        "mdi:flash",
        1,
    ),
    (2, 7): OBISMeasurementInfo(
        "Active export power",
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
        UnitOfPower.WATT,
        "mdi:flash-outline",
        1,
    ),
    (16, 7): OBISMeasurementInfo(
        "Total active power",
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
        UnitOfPower.WATT,
        "mdi:flash",
        1,
    ),
    (36, 7): OBISMeasurementInfo(
        "Active power L1",
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
        UnitOfPower.WATT,
        "mdi:flash",
    ),
    (56, 7): OBISMeasurementInfo(
        "Active power L2",
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
        UnitOfPower.WATT,
        "mdi:flash",
    ),
    (76, 7): OBISMeasurementInfo(
        "Active power L3",
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
        UnitOfPower.WATT,
        "mdi:flash",
    ),
    (3, 7): OBISMeasurementInfo(
        "Reactive import power",
        None,
        SensorStateClass.MEASUREMENT,
        "var",
        "mdi:flash",
    ),
    (4, 7): OBISMeasurementInfo(
        "Reactive export power",
        None,
        SensorStateClass.MEASUREMENT,
        "var",
        "mdi:flash-outline",
    ),
    (9, 7): OBISMeasurementInfo(
        "Total apparent power",
        SensorDeviceClass.APPARENT_POWER,
        SensorStateClass.MEASUREMENT,
        "VA",
        "mdi:flash",
    ),
    # Voltage (D=7)
    (32, 7): OBISMeasurementInfo(
        "Voltage L1",
        SensorDeviceClass.VOLTAGE,
        SensorStateClass.MEASUREMENT,
        UnitOfElectricPotential.VOLT,
        "mdi:sine-wave",
        1,
    ),
    (52, 7): OBISMeasurementInfo(
        "Voltage L2",
        SensorDeviceClass.VOLTAGE,
        SensorStateClass.MEASUREMENT,
        UnitOfElectricPotential.VOLT,
        "mdi:sine-wave",
        1,
    ),
    (72, 7): OBISMeasurementInfo(
        "Voltage L3",
        SensorDeviceClass.VOLTAGE,
        SensorStateClass.MEASUREMENT,
        UnitOfElectricPotential.VOLT,
        "mdi:sine-wave",
        1,
    ),
    # Current (D=7)
    (31, 7): OBISMeasurementInfo(
        "Current L1",
        SensorDeviceClass.CURRENT,
        SensorStateClass.MEASUREMENT,
        UnitOfElectricCurrent.AMPERE,
        "mdi:current-ac",
        2,
    ),
    (51, 7): OBISMeasurementInfo(
        "Current L2",
        SensorDeviceClass.CURRENT,
        SensorStateClass.MEASUREMENT,
        UnitOfElectricCurrent.AMPERE,
        "mdi:current-ac",
        2,
    ),
    (71, 7): OBISMeasurementInfo(
        "Current L3",
        SensorDeviceClass.CURRENT,
        SensorStateClass.MEASUREMENT,
        UnitOfElectricCurrent.AMPERE,
        "mdi:current-ac",
        2,
    ),
    # Frequency / Power factor
    (14, 7): OBISMeasurementInfo(
        "Frequency",
        SensorDeviceClass.FREQUENCY,
        SensorStateClass.MEASUREMENT,
        UnitOfFrequency.HERTZ,
        "mdi:sine-wave",
        2,
    ),
    (13, 7): OBISMeasurementInfo(
        "Power factor",
        SensorDeviceClass.POWER_FACTOR,
        SensorStateClass.MEASUREMENT,
        None,
        "mdi:angle-acute",
        3,
    ),
    # Phase angles (D=7, C=81) - E is a sub-identifier, handled specially
    (81, 7): OBISMeasurementInfo(
        "Phase angle",
        None,
        SensorStateClass.MEASUREMENT,
        "\u00b0",
        "mdi:angle-acute",
        1,
    ),
    # Interval energy / TAF-10 (D=29)
    (1, 29): OBISMeasurementInfo(
        "Active import interval energy",
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL_INCREASING,
        UnitOfEnergy.KILO_WATT_HOUR,
        "mdi:home-import-outline",
        5,
    ),
    (2, 29): OBISMeasurementInfo(
        "Active export interval energy",
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL_INCREASING,
        UnitOfEnergy.KILO_WATT_HOUR,
        "mdi:home-export-outline",
        5,
    ),
    # Max demand (D=6)
    (1, 6): OBISMeasurementInfo(
        "Active import max demand",
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
        UnitOfPower.WATT,
        "mdi:flash-alert",
    ),
    (16, 6): OBISMeasurementInfo(
        "Total active max demand",
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
        UnitOfPower.WATT,
        "mdi:flash-alert",
    ),
}


def parse_obis(code: str) -> ParsedOBIS | None:
    """Parse an OBIS code from string, COSEM hex, or dot-separated hex format."""
    if not code:
        return None

    # Try standard string format: A-B:C.D.E or A-B:C.D.E*F
    m = _OBIS_STRING_RE.match(code)
    if m:
        return ParsedOBIS(
            a=int(m.group(1)),
            b=int(m.group(2)),
            c=int(m.group(3)),
            d=int(m.group(4)),
            e=int(m.group(5)),
            f=int(m.group(6)) if m.group(6) is not None else None,
        )

    # Try dot-separated hex: AA.BB.CC.DD.EE.FF
    m = _OBIS_DOT_HEX_RE.match(code)
    if m:
        return ParsedOBIS(
            a=int(m.group(1), 16),
            b=int(m.group(2), 16),
            c=int(m.group(3), 16),
            d=int(m.group(4), 16),
            e=int(m.group(5), 16),
            f=int(m.group(6), 16),
        )

    # Try 12-character COSEM hex: AABBCCDDEEFF
    stripped = code.strip()
    if len(stripped) == 12 and all(c in "0123456789abcdefABCDEF" for c in stripped):
        return ParsedOBIS(
            a=int(stripped[0:2], 16),
            b=int(stripped[2:4], 16),
            c=int(stripped[4:6], 16),
            d=int(stripped[6:8], 16),
            e=int(stripped[8:10], 16),
            f=int(stripped[10:12], 16),
        )

    return None


def get_obis_info(parsed: ParsedOBIS) -> OBISMeasurementInfo | None:
    """Look up measurement metadata from the OBIS catalog by (C, D)."""
    return OBIS_CATALOG.get((parsed.c, parsed.d))


def build_obis_name(parsed: ParsedOBIS, info: OBISMeasurementInfo | None) -> str:
    """Build a human-readable entity name from a parsed OBIS code."""
    # Special case: phase angles (C=81) use E as a sub-identifier
    if parsed.c == 81 and parsed.d == 7:
        base = PHASE_ANGLE_NAMES.get(parsed.e, f"Phase angle (E={parsed.e})")
    elif info is not None:
        base = info.name
    else:
        return f"OBIS {parsed.to_obis_string()}"

    qualifiers: list[str] = []
    if parsed.b != 0:
        qualifiers.append(f"Ch {parsed.b}")

    # Tariff qualifier: skip for C=81 (E is sub-identifier) and for E=0/255 (total)
    if parsed.c != 81 and parsed.e not in (0, 255):
        qualifiers.append(f"Tariff {parsed.e}")

    # Billing period qualifier from F value (TAF-7)
    if parsed.f is not None and 1 <= parsed.f <= 254:
        qualifiers.append(f"Period -{parsed.f}")

    if qualifiers:
        base += f" ({', '.join(qualifiers)})"

    return base
