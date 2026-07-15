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

REPO_URL = "https://github.com/jannickfahlbusch/ha-ppc-smgw"

CONF_METER_TYPE = "meter_type"

# Opt-in toggle (PPC options flow only) to route data fetching through the
# standalone py-ppc-smgw library instead of the built-in client. Default keeps
# the built-in client so existing installations are unaffected.
CONF_USE_LIBRARY = "use_library"
DEFAULT_USE_LIBRARY = False

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
