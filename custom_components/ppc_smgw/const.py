from homeassistant.components.button import ButtonDeviceClass, ButtonEntityDescription
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy

DOMAIN = "ppc_smgw"
DEFAULT_NAME = "SMGW"
DEFAULT_USERNAME = ""
DEFAULT_PASSWORD = ""
DEFAULT_SCAN_INTERVAL = 5
DEFAULT_DEBUG = False

PPC_DEFAULT_NAME = "PPC SMGW"
PPC_DEFAULT_MODEL= "LTE Smart Meter Gateway"
PPC_MANUFACTURER = "Power Plus Communications AG"
PPC_URL = "https://192.168.1.200/cgi-bin/hanservice.cgi"

THEBEN_DEFAULT_NAME = "Theben SMGW"
THEBEN_DEFAULT_MODEL= "Conexa 3.0"
THEBEN_MANUFACTURER = "Theben Smart Energy GmbH"
THEBEN_URL = "https://{{INSERT_IP}}/smgw/m2m/{{INSERT_ID}}.sm/json"

CONF_METER_TYPE = "meter_type"

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
        name="Export total",
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
)

RestartGatewayButtonDescription = ButtonEntityDescription(
    key="restart_gateway",
    name="Restart Gateway",
    icon="mdi:restart",
    device_class=ButtonDeviceClass.RESTART,
)
