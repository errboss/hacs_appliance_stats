"""Config flow for Appliance Stats."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.selector import selector

from .const import (
    CONF_DELAY_OFF,
    CONF_DELAY_ON,
    CONF_ENERGY_ENTITY,
    CONF_POWER_THRESHOLD,
    CONF_SOURCE_ENTITY,
    CONF_UPDATE_INTERVAL,
    DEFAULT_DELAY_OFF,
    DEFAULT_DELAY_ON,
    DEFAULT_POWER_THRESHOLD,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): str,
        vol.Required(CONF_SOURCE_ENTITY): selector(
            {
                "entity": {
                    "filter": [
                        {
                            "domain": "sensor",
                            "device_class": "power",
                        }
                    ]
                }
            }
        ),
        vol.Required(CONF_ENERGY_ENTITY): selector(
            {
                "entity": {
                    "filter": [
                        {
                            "domain": "sensor",
                            "device_class": "energy",
                        }
                    ]
                }
            }
        ),
        vol.Optional(CONF_POWER_THRESHOLD, default=DEFAULT_POWER_THRESHOLD): vol.Coerce(
            float
        ),
        vol.Optional(CONF_DELAY_ON, default=DEFAULT_DELAY_ON): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=3600)
        ),
        vol.Optional(CONF_DELAY_OFF, default=DEFAULT_DELAY_OFF): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=3600)
        ),
        vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=5, max=3600)
        ),
    }
)


class ApplianceStatsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Appliance Stats."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None):
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            source_entity = user_input[CONF_SOURCE_ENTITY].strip()
            energy_entity = user_input[CONF_ENERGY_ENTITY].strip()
            name = user_input[CONF_NAME].strip()

            source_state = self.hass.states.get(source_entity)
            energy_state = self.hass.states.get(energy_entity)

            if not name:
                errors[CONF_NAME] = "name_required"
            elif source_state is None:
                errors[CONF_SOURCE_ENTITY] = "entity_not_found"
            elif energy_state is None:
                errors[CONF_ENERGY_ENTITY] = "entity_not_found"
            elif source_entity.split(".", 1)[0] != "sensor":
                errors[CONF_SOURCE_ENTITY] = "sensor_required"
            elif energy_entity.split(".", 1)[0] != "sensor":
                errors[CONF_ENERGY_ENTITY] = "sensor_required"
            else:
                await self.async_set_unique_id(source_entity)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=name,
                    data={
                        **user_input,
                        CONF_NAME: name,
                        CONF_SOURCE_ENTITY: source_entity,
                        CONF_ENERGY_ENTITY: energy_entity,
                    },
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        return ApplianceStatsOptionsFlow()


class ApplianceStatsOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Appliance Stats."""

    def __init__(self) -> None:
        """Initialize options flow."""

    async def async_step_init(self, user_input: dict | None = None):
        """Manage the integration options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data = {**self.config_entry.data, **self.config_entry.options}
        energy_entity = data.get(CONF_ENERGY_ENTITY)

        energy_selector = selector(
            {
                "entity": {
                    "filter": [
                        {
                            "domain": "sensor",
                            "device_class": "energy",
                        }
                    ]
                }
            }
        )

        schema_fields = {
            (
                vol.Required(CONF_ENERGY_ENTITY, default=energy_entity)
                if energy_entity
                else vol.Required(CONF_ENERGY_ENTITY)
            ): energy_selector,
            vol.Optional(
                CONF_POWER_THRESHOLD,
                default=data.get(CONF_POWER_THRESHOLD, DEFAULT_POWER_THRESHOLD),
            ): vol.Coerce(float),
            vol.Optional(
                CONF_DELAY_ON,
                default=data.get(CONF_DELAY_ON, DEFAULT_DELAY_ON),
            ): vol.All(vol.Coerce(int), vol.Range(min=0, max=3600)),
            vol.Optional(
                CONF_DELAY_OFF,
                default=data.get(CONF_DELAY_OFF, DEFAULT_DELAY_OFF),
            ): vol.All(vol.Coerce(int), vol.Range(min=0, max=3600)),
            vol.Optional(
                CONF_UPDATE_INTERVAL,
                default=data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
            ): vol.All(vol.Coerce(int), vol.Range(min=5, max=3600)),
        }

        schema = vol.Schema(schema_fields)
        return self.async_show_form(step_id="init", data_schema=schema)
