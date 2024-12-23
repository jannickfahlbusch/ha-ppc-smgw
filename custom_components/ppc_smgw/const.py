from homeassistant.components.button import ButtonDeviceClass, ButtonEntityDescription
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfPower,
)

DOMAIN = "ppc_smgw"
MANUFACTURER = "Power Plus Communications AG"
DEFAULT_NAME = "PPC SMGW"
DEFAULT_HOST = "https://192.168.1.200/cgi-bin/hanservice.cgi"
DEFAULT_USERNAME = ""
DEFAULT_PASSWORD = ""
DEFAULT_SCAN_INTERVAL = 5
DEFAULT_DEBUG = False

# https://developers.home-assistant.io/docs/core/entity/sensor/
SENSOR_TYPES = [
    SensorEntityDescription(
        key="1-0:1.8.0",
        name="Import total (kWh)",
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
    SensorEntityDescription(
        key="1-1:1.7.0",
        name="Current power import (kW)",
        suggested_display_precision=5,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        icon="mdi:power-from-grid",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="1-1:2.7.0",  # apparently on some models this value is also/instead available as `1-0:10.7.0`
        name="Current power export (kW)",
        suggested_display_precision=5,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        icon="mdi:power-to-grid",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
]

LastUpdatedSensorDescription = SensorEntityDescription(
    key="last_update",
    name="Last Update",
    icon="mdi:clock-time-eight",
    native_unit_of_measurement=None,
    device_class=SensorDeviceClass.TIMESTAMP,
)

RestartGatewayButtonDescription = ButtonEntityDescription(
    key="restart_gateway",
    name="Restart Gateway",
    icon="mdi:restart",
    device_class=ButtonDeviceClass.RESTART,
)
