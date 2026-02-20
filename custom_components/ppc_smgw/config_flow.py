import logging
from typing import Any, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    CONF_DEBUG,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_METER_TYPE,
    DEFAULT_DEBUG,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EMH_DEFAULT_NAME,
    EMH_URL,
    PPC_DEFAULT_NAME,
    PPC_URL,
    REPO_URL,
    THEBEN_DEFAULT_NAME,
    THEBEN_URL,
)
from .gateways.vendors import Vendor

_LOGGER = logging.getLogger(__name__)

SCHEMA_VENDOR = vol.Schema(
    {
        vol.Required(CONF_METER_TYPE): vol.In(Vendor.__members__),
    }
)


def build_username_password_schema(
    default_name: str, default_url: str, allow_debugging: bool = False
) -> vol.Schema:
    schema = {
        vol.Required(CONF_NAME, default=default_name): str,
        vol.Required(CONF_HOST, default=default_url): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.PASSWORD, autocomplete="current-password"
            )
        ),
        vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
    }

    if allow_debugging:
        schema[vol.Optional(CONF_DEBUG, default=False)] = bool

    return vol.Schema(schema)


@staticmethod
def configured_host_username_pairs(hass: HomeAssistant):
    """Return a list of host-username pairs that are configured."""
    configured_pairs = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        if hasattr(entry, "options") and CONF_HOST in entry.options:
            configured_pairs.append(entry.options[CONF_HOST])
        else:
            configured_pairs.append((entry.data[CONF_HOST], entry.data[CONF_USERNAME]))
    return configured_pairs


@staticmethod
def _host_username_combination_exists(
    host: str, username: str, hass: HomeAssistant
) -> bool:
    """Check if the combination of host and username already exists in configuration."""
    if (host, username) in configured_host_username_pairs(hass):
        return True
    return False


class PPC_SMGLocalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2
    MINOR_VERSION = 2

    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    data: Optional[dict[str, Any]]
    _errors: dict[str, str] = {}

    async def _test_connection(self, host, username, password):
        self._errors = {}
        # TODO: Implement connection check
        return True

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            if not self._errors:
                self.data = user_input
                self.data[CONF_METER_TYPE]: Vendor = Vendor(
                    user_input.get(CONF_METER_TYPE)
                )

                return await self.async_step_connection_info(user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=SCHEMA_VENDOR,
            errors=self._errors,
            description_placeholders={"repo_url": REPO_URL},
        )

    async def async_step_connection_details(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        pass

    async def async_step_connection_info(
        self, user_input: dict[str, Any] | None = None
    ):
        if all(
            k in user_input
            for k in (
                CONF_NAME,
                CONF_HOST,
                CONF_USERNAME,
                CONF_PASSWORD,
                CONF_SCAN_INTERVAL,
            )
        ):
            if self.data[CONF_METER_TYPE] == Vendor("Theben"):
                self.data[CONF_NAME] = user_input.get(CONF_NAME, THEBEN_DEFAULT_NAME)
            elif self.data[CONF_METER_TYPE] == Vendor("EMH"):
                self.data[CONF_NAME] = user_input.get(CONF_NAME, EMH_DEFAULT_NAME)
            else:
                self.data[CONF_NAME] = user_input.get(CONF_NAME, PPC_DEFAULT_NAME)
                self.data[CONF_DEBUG] = user_input.get(CONF_DEBUG, DEFAULT_DEBUG)
            self.data[CONF_HOST] = user_input.get(CONF_HOST, "")
            self.data[CONF_USERNAME] = user_input.get(CONF_USERNAME, "")
            self.data[CONF_PASSWORD] = user_input.get(CONF_PASSWORD, "")
            self.data[CONF_SCAN_INTERVAL] = user_input.get(
                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
            )

            if _host_username_combination_exists(
                self.data[CONF_HOST], self.data[CONF_USERNAME], self.hass
            ):
                self._errors[CONF_HOST] = "already_configured"
            elif await self._test_connection(
                self.data[CONF_HOST], self.data[CONF_USERNAME], self.data[CONF_PASSWORD]
            ):
                _LOGGER.debug(f"user_input: {user_input}")

                return self.async_create_entry(
                    title=self.data[CONF_NAME], data=self.data
                )

            else:
                _LOGGER.error(
                    "Could not connect to SMGW at %s. Check connection manually",
                    self.data[CONF_HOST],
                )

        data_schema = build_username_password_schema(PPC_DEFAULT_NAME, PPC_URL, True)
        if self.data[CONF_METER_TYPE] == Vendor.Theben:
            data_schema = build_username_password_schema(
                THEBEN_DEFAULT_NAME, THEBEN_URL
            )
        elif self.data[CONF_METER_TYPE] == Vendor.EMH:
            data_schema = build_username_password_schema(EMH_DEFAULT_NAME, EMH_URL)

        return self.async_show_form(
            step_id="connection_info",
            data_schema=data_schema,
            last_step=True,
            errors=self._errors,
            description_placeholders={"repo_url": REPO_URL},
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
            _LOGGER.debug(f"Data: {self.data}")
            self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None):  # pylint: disable=unused-argument
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        self._errors = {}
        if user_input is not None:
            self.options.update(user_input)
            if self.data.get(CONF_HOST) != self.options.get(CONF_HOST) or self.data.get(
                CONF_USERNAME
            ) != self.options.get(CONF_USERNAME):
                # ok looks like the host or username has been changed... we need to do some things...
                if _host_username_combination_exists(
                    self.options.get(CONF_HOST),
                    self.options.get(CONF_USERNAME),
                    self.hass,
                ):
                    self._errors[CONF_HOST] = "already_configured"
                else:
                    return self._update_options()
            else:
                # host did not change...
                return self._update_options()

        data_schema = build_username_password_schema(PPC_DEFAULT_NAME, PPC_URL, True)
        if self.data[CONF_METER_TYPE] == Vendor.Theben:
            data_schema = build_username_password_schema(
                THEBEN_DEFAULT_NAME, THEBEN_URL
            )
        elif self.data[CONF_METER_TYPE] == Vendor.EMH:
            data_schema = build_username_password_schema(EMH_DEFAULT_NAME, EMH_URL)

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            description_placeholders={"repo_url": REPO_URL},
        )

    def _update_options(self):
        """Update config entry options."""
        return self.async_create_entry(data=self.options)
