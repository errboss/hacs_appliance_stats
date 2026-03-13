"""Appliance Stats integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .manager import ApplianceStatsManager


aSYNC_SETUP_NOTE = "Managed through config entries only"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Appliance Stats from a config entry."""
    manager = ApplianceStatsManager(hass, entry)
    await manager.async_setup()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = manager
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an Appliance Stats config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        manager: ApplianceStatsManager = hass.data[DOMAIN].pop(entry.entry_id)
        await manager.async_unload()
    return unload_ok
