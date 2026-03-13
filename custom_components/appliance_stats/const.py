"""Constants for the Appliance Stats integration."""

from __future__ import annotations

DOMAIN = "appliance_stats"
PLATFORMS = ["binary_sensor", "sensor"]

CONF_SOURCE_ENTITY = "source_entity"
CONF_ENERGY_ENTITY = "energy_entity"
CONF_POWER_THRESHOLD = "power_threshold"
CONF_DELAY_ON = "delay_on"
CONF_DELAY_OFF = "delay_off"
CONF_UPDATE_INTERVAL = "update_interval"

DEFAULT_POWER_THRESHOLD = 10.0
DEFAULT_DELAY_ON = 30
DEFAULT_DELAY_OFF = 120
DEFAULT_UPDATE_INTERVAL = 30

STORAGE_VERSION = 1
STORAGE_SAVE_DELAY = 10

ATTR_CURRENT_POWER = "current_power"
ATTR_CURRENT_ENERGY = "current_energy"
ATTR_POWER_THRESHOLD = "power_threshold"
ATTR_SOURCE_ENTITY = "source_entity"
ATTR_ENERGY_ENTITY = "energy_entity"
ATTR_DELAY_ON = "delay_on"
ATTR_DELAY_OFF = "delay_off"
ATTR_UPDATE_INTERVAL = "update_interval"
