"""Config flow for Sencor Vacuum integration."""

import logging
from typing import Any

import voluptuous as vol
import ipaddress

from homeassistant import config_entries, exceptions
from homeassistant.core import HomeAssistant

from homeassistant.const import CONF_HOST
from .const import DOMAIN, CONF_AUTH_CODE, CONF_DEVICE_ID
from .helpers import host_available

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_AUTH_CODE): str,
        vol.Required(CONF_DEVICE_ID): str
    }
)


async def validate_input(hass: HomeAssistant, data: dict) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """

    try:
        ipaddress.ip_address(data[CONF_HOST])
    except ValueError as err:
        raise InvalidHost from err

    return data


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sencor Vacuum."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)

                return self.async_create_entry(title="Sencor Vacuum", data=info)
            except InvalidHost:
                errors["host"] = "invalid_host"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # If there is no user input or there were errors, show the form again, including any errors that were found with the input.
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


class InvalidHost(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid hostname."""