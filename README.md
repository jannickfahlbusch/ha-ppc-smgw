# ha-ppc-smgw

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=jannickfahlbusch&repository=ha-ppc-smgw)

HomeAssistant component to read PPC SMGWs

This custom integration allows you to integrate a PPC Smart Meter Gateway into HomeAssistant.

## Installation

This component is installable via [HACS](https://www.hacs.xyz/).

Add the repository as a custom repository using [this guide](https://www.hacs.xyz/docs/faq/custom_repositories/).

Click on the badge above or use this [link](https://my.home-assistant.io/redirect/hacs_repository/?owner=jannickfahlbusch&repository=ha-ppc-smgw) to get redirected to the HACS store from where you can install the component.

Restart your instance and head over to the integration overview (Or use [this link](https://my.home-assistant.io/redirect/config_flow_start/?domain=ppc_smgw) to directly go to the configuration of this component) to start configuring the integration.

## Configuration

| Option | Description |
|--------|-------------|
| Display Name | The Name of the resulting device |
| URL | URL to the SMGW. This defaults to `http://192.168.188.1:8080/cgi-bin/hanservice.cgi` |
| Username | The username for authentication with the PPC Smart Meter Gateway. You should have received this from your electricity provider |
| Password | The password for authentication with the PPC Smart Meter Gateway. You should have received this from your electricity provider |
| Update Interval | The interval in minutes for updating the data from the PPC Smart Meter Gateway. Defaults to 5 minutes. |

Please note that most providers have configured the SMGW to update the values only every 15 to 20 minutes.
You should choose an interval that is reasonably large as polling too frequently might lead to a lockdown of the SMGW after a yet to be clarified amount of polls.

## Available sensor values

This component exposes the following sensor values from the SmartMeterGateway:

| Name | OBIS Code |
|------|-----------|
| Import total (kWh) | `1-0:1.8.0` |
| Export total (kWh) | `1-0:2.8.0` |
| Current power import (kW) | `1-1:1.7.0` |
| Current power export (kW) | `1-1:2.7.0` |

More sensor values based on [OBIS codes](https://de.wikipedia.org/wiki/OBIS-Kennzahlen) can be added as needed.

## Development

To bootstrap the development environment, use the following commands:

```sh
python3 -m venv venv
source venv/bin/activate
python3 -m ensurepip
pip install -r requirements.txt
```

Then run a local HomeAssistant instance with:

```sh
scripts/run.sh
```

Access it at http://localhost:8123 and follow the setup guide.
Then head to `Settings` > `Integrations` > `Add Integration` and search for `SMGW` to add enable the custom component.
