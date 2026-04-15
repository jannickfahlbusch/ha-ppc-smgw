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
from homeassistant.helpers.httpx_client import create_async_httpx_client
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_METER_TYPE,
    DEFAULT_DEBUG,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    REPO_URL,
)
from .gateways.emh import const as emh_const
from .gateways.theben import const as theben_const
from .gateways.ppc import const as ppc_const
from .gateways.vendors import Vendor

_LOGGER = logging.getLogger(__name__)

SCHEMA_VENDOR = vol.Schema(
    {
        vol.Required(CONF_METER_TYPE): vol.In(Vendor.__members__),
    }
)


def build_username_password_schema(
    default_name: str,
    default_url: str,
    allow_debugging: bool = False,
    default_username: str = "",
    default_scan_interval: int = DEFAULT_SCAN_INTERVAL,
    default_debug: bool = False,
    optional_password: bool = False,
    default_meter_id: str | None = None,
) -> vol.Schema:
    """Build a schema for username/password configuration.

    Args:
        default_name: Default value for the name field.
        default_url: Default value for the host/URL field.
        allow_debugging: Whether to include the debug option (PPC only).
        default_username: Default value for the username field.
        default_scan_interval: Default value for the scan interval field.
        default_debug: Default value for the debug field (if allowed).
        optional_password: If True, password can be left blank (for options flow).
        default_meter_id: If not None, include an optional meter_id field (EMH only).

    Returns:
        A voluptuous Schema for the configuration form.
    """
    password_selector = TextSelector(
        TextSelectorConfig(
            type=TextSelectorType.PASSWORD, autocomplete="current-password"
        )
    )
    if optional_password:
        password_key = vol.Optional(CONF_PASSWORD, default="")
    else:
        password_key = vol.Required(CONF_PASSWORD)

    schema = {
        vol.Required(CONF_NAME, default=default_name): str,
        vol.Required(CONF_HOST, default=default_url): str,
        vol.Required(CONF_USERNAME, default=default_username): str,
        password_key: password_selector,
        vol.Required(CONF_SCAN_INTERVAL, default=default_scan_interval): int,
    }

    if allow_debugging:
        schema[vol.Optional(CONF_DEBUG, default=default_debug)] = bool

    if default_meter_id is not None:
        schema[vol.Optional(emh_const.CONF_METER_ID, default=default_meter_id)] = str

    return vol.Schema(schema)


def _host_username_combination_exists(
    host: str,
    username: str,
    hass: HomeAssistant,
    exclude_entry_id: str | None = None,
    meter_id: str = "",
) -> bool:
    """Check if the combination of host, username (and meter_id) already exists.

    For EMH entries, meter_id is part of the unique key so that multiple instances
    of the same gateway with different meters are allowed.

    Args:
        host: The host/URL to check.
        username: The username to check.
        hass: Home Assistant instance.
        exclude_entry_id: Optional entry ID to exclude from the check (for updates).
        meter_id: Meter ID to include in the uniqueness check (EMH only, default "").

    Returns:
        True if the combination exists (excluding the specified entry), False otherwise.
    """
    for entry in hass.config_entries.async_entries(DOMAIN):
        # Skip the entry being updated
        if exclude_entry_id and entry.entry_id == exclude_entry_id:
            continue

        # Check options first (for updated entries), fall back to data
        entry_host = entry.options.get(CONF_HOST) or entry.data.get(CONF_HOST)
        entry_username = entry.options.get(CONF_USERNAME) or entry.data.get(
            CONF_USERNAME
        )

        if entry_host == host and entry_username == username:
            entry_meter_id = entry.data.get(emh_const.CONF_METER_ID, "")
            if entry_meter_id == meter_id:
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
                self.data[CONF_NAME] = user_input.get(
                    CONF_NAME, theben_const.DEFAULT_NAME
                )
            elif self.data[CONF_METER_TYPE] == Vendor("EMH"):
                self.data[CONF_NAME] = user_input.get(CONF_NAME, emh_const.DEFAULT_NAME)
            else:
                self.data[CONF_NAME] = user_input.get(CONF_NAME, ppc_const.DEFAULT_NAME)
                self.data[CONF_DEBUG] = user_input.get(CONF_DEBUG, DEFAULT_DEBUG)
            self.data[CONF_HOST] = user_input.get(CONF_HOST, "")
            self.data[CONF_USERNAME] = user_input.get(CONF_USERNAME, "")
            self.data[CONF_PASSWORD] = user_input.get(CONF_PASSWORD, "")
            self.data[CONF_SCAN_INTERVAL] = user_input.get(
                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
            )

            if self.data[CONF_METER_TYPE] == Vendor.EMH:
                if not await self._test_connection(
                    self.data[CONF_HOST],
                    self.data[CONF_USERNAME],
                    self.data[CONF_PASSWORD],
                ):
                    _LOGGER.error(
                        "Could not connect to SMGW at %s. Check connection manually",
                        self.data[CONF_HOST],
                    )
                else:
                    # Meter selection handled in the next step via gateway discovery
                    return await self.async_step_emh_meter_select()

            if _host_username_combination_exists(
                self.data[CONF_HOST],
                self.data[CONF_USERNAME],
                self.hass,
                meter_id=self.data.get(emh_const.CONF_METER_ID, ""),
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

        data_schema = build_username_password_schema(
            ppc_const.DEFAULT_NAME, ppc_const.DEFAULT_URL, True
        )
        if self.data[CONF_METER_TYPE] == Vendor.Theben:
            data_schema = build_username_password_schema(
                theben_const.DEFAULT_NAME, theben_const.DEFAULT_URL
            )
        elif self.data[CONF_METER_TYPE] == Vendor.EMH:
            data_schema = build_username_password_schema(
                emh_const.DEFAULT_NAME, emh_const.URL
            )

        return self.async_show_form(
            step_id="connection_info",
            data_schema=data_schema,
            last_step=True,
            errors=self._errors,
            description_placeholders={"repo_url": REPO_URL},
        )

    async def _discover_emh_meter_ids(self) -> list[str]:
        """Call the EMH gateway and return all available meter IDs."""
        from .gateways.emh.emhcasa.emh_client import EMHCasaClient

        client = EMHCasaClient(
            base_url=self.data[CONF_HOST],
            username=self.data[CONF_USERNAME],
            password=self.data[CONF_PASSWORD],
            httpx_client=create_async_httpx_client(self.hass, verify_ssl=False),
            logger=_LOGGER,
        )
        return await client.discover_all_meter_ids()

    async def async_step_emh_meter_select(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user pick which EMH meter to monitor."""
        errors: dict[str, str] = {}

        if user_input is not None:
            meter_id = user_input.get(emh_const.CONF_METER_ID, "")
            self.data[emh_const.CONF_METER_ID] = meter_id

            if _host_username_combination_exists(
                self.data[CONF_HOST],
                self.data[CONF_USERNAME],
                self.hass,
                meter_id=meter_id,
            ):
                errors[emh_const.CONF_METER_ID] = "already_configured"
            else:
                return self.async_create_entry(
                    title=self.data[CONF_NAME], data=self.data
                )

        meter_ids = await self._discover_emh_meter_ids()

        if not meter_ids:
            _LOGGER.warning(
                "EMH meter discovery returned no results, creating entry with auto-detect"
            )
            self.data[emh_const.CONF_METER_ID] = ""
            return self.async_create_entry(title=self.data[CONF_NAME], data=self.data)

        options = [
            {"value": "", "label": "Auto-detect (first available)"},
            *[{"value": m, "label": m} for m in meter_ids],
        ]

        return self.async_show_form(
            step_id="emh_meter_select",
            data_schema=vol.Schema(
                {
                    vol.Optional(emh_const.CONF_METER_ID, default=""): SelectSelector(
                        SelectSelectorConfig(options=options)
                    )
                }
            ),
            errors=errors,
            description_placeholders={"repo_url": REPO_URL},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return PPCSMGWLocalOptionsFlowHandler(config_entry)


class PPCSMGWLocalOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        """Initialize HACS options flow."""
        self._config_entry = config_entry
        self.data = dict(config_entry.data)
        if len(dict(config_entry.options)) == 0:
            self.options = {}
        else:
            self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None):  # pylint: disable=unused-argument
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle a flow initialized by the user."""
        self._errors = {}
        if user_input is not None:
            # If password is blank, keep the existing one
            if not user_input.get(CONF_PASSWORD):
                user_input[CONF_PASSWORD] = self.data.get(CONF_PASSWORD, "")
            self.options.update(user_input)
            if self.data.get(CONF_HOST) != self.options.get(CONF_HOST) or self.data.get(
                CONF_USERNAME
            ) != self.options.get(CONF_USERNAME):
                # ok looks like the host or username has been changed... we need to do some things...
                if _host_username_combination_exists(
                    self.options.get(CONF_HOST),
                    self.options.get(CONF_USERNAME),
                    self.hass,
                    exclude_entry_id=self._config_entry.entry_id,
                    meter_id=self.options.get(emh_const.CONF_METER_ID, ""),
                ):
                    self._errors[CONF_HOST] = "already_configured"
                else:
                    return self._update_options()
            else:
                # host did not change...
                return self._update_options()

        # Build schema with current values based on vendor type
        data_schema = self._build_options_schema()

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=self._errors,
            description_placeholders={"repo_url": REPO_URL},
        )

    def _build_options_schema(self) -> vol.Schema:
        """Build the options schema with current values as defaults.

        Returns:
            A voluptuous Schema populated with current configuration values.
        """
        # Determine vendor type and appropriate defaults
        vendor = self.data.get(CONF_METER_TYPE)

        # Get vendor-specific default name
        if vendor == Vendor.Theben:
            default_name = theben_const.DEFAULT_NAME
            default_url = theben_const.DEFAULT_URL
        elif vendor == Vendor.EMH:
            default_name = emh_const.DEFAULT_NAME
            default_url = emh_const.DEFAULT_URL
        else:  # PPC or unspecified
            default_name = ppc_const.DEFAULT_NAME
            default_url = ppc_const.DEFAULT_URL

        # Get current values, preferring options over data, then vendor-specific defaults
        current_name = self.options.get(
            CONF_NAME, self.data.get(CONF_NAME, default_name)
        )
        current_host = self.options.get(
            CONF_HOST, self.data.get(CONF_HOST, default_url)
        )
        current_username = self.options.get(
            CONF_USERNAME, self.data.get(CONF_USERNAME, "")
        )
        current_scan_interval = self.options.get(
            CONF_SCAN_INTERVAL, self.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )

        # Determine if this is a PPC device (only vendor with debug option)
        is_ppc = vendor == Vendor.PPC
        current_debug = DEFAULT_DEBUG
        if is_ppc:
            current_debug = self.options.get(
                CONF_DEBUG, self.data.get(CONF_DEBUG, DEFAULT_DEBUG)
            )

        # For EMH, include the meter_id field
        is_emh = vendor == Vendor.EMH
        current_meter_id = None
        if is_emh:
            current_meter_id = self.options.get(
                emh_const.CONF_METER_ID, self.data.get(emh_const.CONF_METER_ID, "")
            )

        return build_username_password_schema(
            default_name=current_name,
            default_url=current_host,
            allow_debugging=is_ppc,
            default_username=current_username,
            default_scan_interval=current_scan_interval,
            default_debug=current_debug,
            optional_password=True,
            default_meter_id=current_meter_id,
        )

    def _update_options(self):
        """Update config entry data and close the options flow.

        Merges all changed values into entry.data (the single source of truth
        read by __init__.py). Options are kept empty to avoid dual-write
        inconsistency.
        """
        new_data = {**self._config_entry.data, **self.options}
        self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)
        return self.async_create_entry(data={})
