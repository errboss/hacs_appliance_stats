"""Binary sensors for Appliance Stats."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import ApplianceStatsEntity
from .manager import ApplianceStatsManager


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up Appliance Stats binary sensors."""
    manager: ApplianceStatsManager = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ApplianceActiveBinarySensor(manager, entry)])


class ApplianceActiveBinarySensor(ApplianceStatsEntity, BinarySensorEntity):
    """Show whether the appliance is currently active based on power draw."""

    _attr_translation_key = "active"

    def __init__(self, manager: ApplianceStatsManager, entry: ConfigEntry) -> None:
        super().__init__(manager, entry)
        self._attr_unique_id = f"{entry.entry_id}_active"
        self._attr_name = "Active"

    @property
    def is_on(self) -> bool:
        return self.manager.is_active
