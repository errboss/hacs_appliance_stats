"""Shared entity helpers for Appliance Stats."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .manager import ApplianceStatsManager


class ApplianceStatsEntity(Entity):
    """Base entity for Appliance Stats."""

    _attr_has_entity_name = True
    _unsub_listener = None

    def __init__(self, manager: ApplianceStatsManager, entry: ConfigEntry) -> None:
        self.manager = manager
        self.entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=manager.name,
            manufacturer="Custom",
            model="Appliance runtime and energy tracker",
        )

    @property
    def available(self):
        return True

    @property
    def extra_state_attributes(self):
        return self.manager.extra_attributes

    async def async_added_to_hass(self) -> None:
        self._unsub_listener = self.manager.async_add_listener(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub_listener is not None:
            self._unsub_listener()
            self._unsub_listener = None
