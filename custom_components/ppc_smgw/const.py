from homeassistant.components.button import ButtonDeviceClass, ButtonEntityDescription
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
)

DOMAIN = "ppc_smgw"
DEFAULT_NAME = "SMGW"
DEFAULT_USERNAME = ""
DEFAULT_PASSWORD = ""
DEFAULT_SCAN_INTERVAL = 5
DEFAULT_DEBUG = False

REPO_URL = "https://github.com/jannickfahlbusch/ha-ppc-smgw"

CONF_METER_TYPE = "meter_type"

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
