"""Home Assistant mapping for OBIS metadata.

This is the only OBIS layer that imports Home Assistant. It converts the plain
strings from ``obis.py`` into HA enums/unit constants and bundles the
translation key + placeholders that the sensor entity applies.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfReactiveEnergy,
    UnitOfReactivePower,
)
from homeassistant.helpers.entity import EntityCategory
from obis_parser import OBIS

_DEVICE_CLASS_MAP = {
    "current": SensorDeviceClass.CURRENT,
    "energy": SensorDeviceClass.ENERGY,
    "power": SensorDeviceClass.POWER,
    "voltage": SensorDeviceClass.VOLTAGE,
    "reactive_energy": SensorDeviceClass.REACTIVE_ENERGY,
    "reactive_power": SensorDeviceClass.REACTIVE_POWER,
    "apparent_power": SensorDeviceClass.APPARENT_POWER,
    "power_factor": SensorDeviceClass.POWER_FACTOR,
    "frequency": SensorDeviceClass.FREQUENCY,
}

_STATE_CLASS_MAP = {
    "measurement": SensorStateClass.MEASUREMENT,
    "total_increasing": SensorStateClass.TOTAL_INCREASING,
}

_UNIT_MAP = {
    "A": UnitOfElectricCurrent.AMPERE,
    "kWh": UnitOfEnergy.KILO_WATT_HOUR,
    "V": UnitOfElectricPotential.VOLT,
    "W": UnitOfPower.WATT,
    "var": UnitOfReactivePower.VOLT_AMPERE_REACTIVE,
    "kvarh": UnitOfReactiveEnergy.KILO_VOLT_AMPERE_REACTIVE_HOUR,
    "VA": UnitOfApparentPower.VOLT_AMPERE,
    "Hz": UnitOfFrequency.HERTZ,
    # "kVAh" intentionally omitted — no HA constant; passed through as a raw string.
}


@dataclass
class OBISSensorSpec:
    """Everything a sensor entity needs to represent one OBIS code.

    ``translation_key``/``translation_placeholders`` drive the localized name.
    ``name_fallback`` is used only for codes without a translation slug
    (unknown / unparseable), where the entity sets a plain ``_attr_name``.
    """

    description: SensorEntityDescription
    translation_key: str | None = None
    translation_placeholders: dict[str, str] = field(default_factory=dict)
    name_fallback: str | None = None


def build_obis_sensor_description(key: str) -> OBISSensorSpec:
    """Build a sensor spec for a canonical OBIS key."""
    parsed = OBIS.parse(key)
    if parsed is None:
        return OBISSensorSpec(
            description=SensorEntityDescription(
                key=key,
                icon="mdi:gauge",
                entity_category=EntityCategory.DIAGNOSTIC,
                entity_registry_enabled_default=False,
            ),
            translation_key="unknown_code",
            translation_placeholders={"code": key},
            name_fallback=f"OBIS {key}",
        )

    info = parsed.info
    descriptor = parsed.describe()
    if info is None:
        return OBISSensorSpec(
            description=SensorEntityDescription(
                key=key,
                icon="mdi:gauge",
                entity_category=EntityCategory.DIAGNOSTIC,
                entity_registry_enabled_default=False,
            ),
            translation_key=descriptor.translation_key,
            translation_placeholders=descriptor.placeholders,
            name_fallback=descriptor.fallback_name,
        )

    return OBISSensorSpec(
        description=SensorEntityDescription(
            key=key,
            suggested_display_precision=info.suggested_display_precision,
            entity_registry_enabled_default=True,
            native_unit_of_measurement=_UNIT_MAP.get(info.unit, info.unit),
            icon=info.icon,
            device_class=_DEVICE_CLASS_MAP.get(info.device_class),
            state_class=_STATE_CLASS_MAP.get(info.state_class),
        ),
        translation_key=descriptor.translation_key,
        translation_placeholders=descriptor.placeholders,
    )
