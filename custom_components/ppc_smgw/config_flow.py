import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant, callback

from .const import (
    DOMAIN,
    DEFAULT_NAME,
    DEFAULT_HOST,
    DEFAULT_USERNAME,
    DEFAULT_PASSWORD,
    DEFAULT_SCAN_INTERVAL,
)

from .ppc_smgw import PPC_SMGW

_LOGGER = logging.getLogger(__name__)


@staticmethod
def ppc_smgw_entries(hass: HomeAssistant):
    conf_hosts = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        if hasattr(entry, "options") and CONF_HOST in entry.options:
            conf_hosts.append(entry.options[CONF_HOST])
        else:
            conf_hosts.append(entry.data[CONF_HOST])
    return conf_hosts


@staticmethod
def _host_in_configuration_exists(host: str, hass: HomeAssistant) -> bool:
    if host in ppc_smgw_entries(hass):
        return True
    return False


class PPC_SMGLocalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        self._errors = {}

    async def _test_connection(self, host, username, password):
        self._errors = {}
        # ToDo: Implement connection check
        return True

    async def async_step_user(self, user_input=None):
        self._errors = {}
        if user_input is not None:
            name = user_input.get(CONF_NAME, DEFAULT_NAME)
            host = user_input.get(CONF_HOST, DEFAULT_HOST)
            username = user_input.get(CONF_USERNAME, "")
            password = user_input.get(CONF_PASSWORD, "")
            scan = user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

            if _host_in_configuration_exists(host, self.hass):
                self._errors[CONF_HOST] = "already_configured"
            else:
                if await self._test_connection(host, username, password):
                    a_data = {
                        CONF_NAME: name,
                        CONF_HOST: host,
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_SCAN_INTERVAL: scan,
                    }

                    return self.async_create_entry(title=name, data=a_data)

                else:
                    _LOGGER.error(
                        "Could not connect to SMGW at %s. Check connection manually",
                        host,
                    )
        else:
            user_input = {}
            user_input[CONF_NAME] = DEFAULT_NAME
            user_input[CONF_HOST] = DEFAULT_HOST
            user_input[CONF_USERNAME] = DEFAULT_USERNAME
            user_input[CONF_PASSWORD] = DEFAULT_PASSWORD
            user_input[CONF_SCAN_INTERVAL] = DEFAULT_SCAN_INTERVAL

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME, default=user_input.get(CONF_NAME, DEFAULT_NAME)
                    ): str,
                    vol.Required(
                        CONF_HOST, default=user_input.get(CONF_HOST, DEFAULT_HOST)
                    ): str,
                    vol.Required(
                        CONF_USERNAME,
                        default=user_input.get(CONF_USERNAME, DEFAULT_USERNAME),
                    ): str,
                    vol.Required(
                        CONF_PASSWORD,
                        default=user_input.get(CONF_PASSWORD, DEFAULT_PASSWORD),
                    ): str,
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=user_input.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): int,
                }
            ),
            last_step=True,
            errors=self._errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return PPCSMGWLocalOptionsFlowHandler(config_entry)


class PPCSMGWLocalOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        """Initialize HACS options flow."""
        self.data = dict(config_entry.data)
        if len(dict(config_entry.options)) == 0:
            self.options = {}
        else:
            self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None):  # pylint: disable=unused-argument
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        self._errors = {}
        if user_input is not None:
            self.options.update(user_input)
            if self.data.get(CONF_HOST) != self.options.get(CONF_HOST):
                # ok looks like the host has been changed... we need to do some things...
                if _host_in_configuration_exists(
                    self.options.get(CONF_HOST), self.hass
                ):
                    self._errors[CONF_HOST] = "already_configured"
                else:
                    return self._update_options()
            else:
                # host did not change...
                return self._update_options()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME,
                        default=self.options.get(
                            CONF_NAME, self.data.get(CONF_NAME, DEFAULT_NAME)
                        ),
                    ): str,
                    vol.Required(
                        CONF_HOST,
                        default=self.options.get(
                            CONF_HOST, self.data.get(CONF_HOST, DEFAULT_HOST)
                        ),
                    ): str,
                    vol.Required(
                        CONF_USERNAME,
                        default=self.options.get(
                            CONF_USERNAME,
                            self.data.get(CONF_USERNAME, DEFAULT_USERNAME),
                        ),
                    ): str,
                    vol.Required(
                        CONF_PASSWORD,
                        default=self.options.get(
                            CONF_PASSWORD,
                            self.data.get(CONF_PASSWORD, DEFAULT_PASSWORD),
                        ),
                    ): str,
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self.options.get(
                            CONF_SCAN_INTERVAL,
                            self.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                        ),
                    ): int,
                }
            ),
        )

    def _update_options(self):
        """Update config entry options."""
        return self.async_create_entry(data=self.options)
