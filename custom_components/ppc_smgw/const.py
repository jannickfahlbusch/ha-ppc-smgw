from typing import Final
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)

from homeassistant.const import (
    UnitOfEnergy,
)

DOMAIN: Final = "ppc_smgw"
MANUFACTURER: Final = "Power Plus Communications AG"
DEFAULT_NAME = "PPC SMGW"
DEFAULT_HOST = "https://192.168.1.200/cgi-bin/hanservice.cgi"
DEFAULT_USERNAME = ""
DEFAULT_PASSWORD = ""
DEFAULT_SCAN_INTERVAL = 5

@dataclass
class ExtSensorEntityDescription(SensorEntityDescription):
    aliases: list[str] | None = None

SENSOR_TYPES = [
    SensorEntityDescription(
        key="1-0:1.8.0",
        name="Import total",
        suggested_display_precision=5,
        entity_registry_enabled_default=True,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:home-import-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="1-0:2.8.0",
        name="Export total (kWh)",
        suggested_display_precision=5,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:home-export-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
]

LastUpdatedSensorDescription = SensorEntityDescription(
        key="last_update",
        name="Last Update",
        icon="mdi:clock-time-eight",
        native_unit_of_measurement=None,
        device_class=SensorDeviceClass.TIMESTAMP,
        state_class=SensorStateClass.MEASUREMENT
)
