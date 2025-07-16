# ha-ppc-smgw

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=jannickfahlbusch&repository=ha-ppc-smgw)

HomeAssistant component to read SMGWs.

This custom integration allows you to integrate the following Smart Meter Gateways into HomeAssistant:
* PPC SMGW
* Theben Conexa

## Installation

This component is installable via [HACS](https://www.hacs.xyz/).

Add the repository as a custom repository using [this guide](https://www.hacs.xyz/docs/faq/custom_repositories/).

Click on the badge above or use this [link](https://my.home-assistant.io/redirect/hacs_repository/?owner=jannickfahlbusch&repository=ha-ppc-smgw) to get redirected to the HACS store from where you can install the component.

Restart your instance and head over to the integration overview (Or use [this link](https://my.home-assistant.io/redirect/config_flow_start/?domain=ppc_smgw) to directly go to the configuration of this component) to start configuring the integration.

## Requirements

In order to connect to your Gateway, you need at least the following information:

* IP address of the SMGW within your home network
* Credentials (Username and Password) for the Gateway

## Configuration

| Option | Description |
|--------|-------------|
| Display Name | The Name of the resulting device |
| URL | URL to the SMGW. |
| Username | The username for authentication with the PPC Smart Meter Gateway. You should have received this from your electricity provider |
| Password | The password for authentication with the PPC Smart Meter Gateway. You should have received this from your electricity provider |
| Update Interval | The interval in minutes for updating the data from the PPC Smart Meter Gateway. Defaults to 5 minutes. |

Please note that most providers have configured the SMGW to update the values only every 15 to 20 minutes.
You should choose an interval that is reasonably large as polling too frequently might lead to a lockdown of the SMGW after a yet to be clarified amount of polls.
