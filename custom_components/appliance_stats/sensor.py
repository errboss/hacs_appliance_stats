"""Sensors for Appliance Stats."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import ApplianceStatsEntity
from .manager import ApplianceStatsManager


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up Appliance Stats sensors."""
    manager: ApplianceStatsManager = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            ApplianceRuntimeTotalSensor(manager, entry),
            ApplianceEnergyActiveTotalSensor(manager, entry),
            ApplianceRunsTotalSensor(manager, entry),
        ]
    )


class ApplianceRuntimeSensor(ApplianceStatsEntity, SensorEntity):
    """Base runtime sensor."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_suggested_display_precision = 2

    @staticmethod
    def _rounded(value: float) -> float:
        return round(value, 3)


class ApplianceRuntimeTotalSensor(ApplianceRuntimeSensor):
    """Total appliance runtime since the integration was added."""

    _attr_translation_key = "runtime_total"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, manager: ApplianceStatsManager, entry: ConfigEntry) -> None:
        super().__init__(manager, entry)
        self._attr_unique_id = f"{entry.entry_id}_runtime_total"
        self._attr_name = "Runtime total"

    @property
    def native_value(self) -> float:
        return self._rounded(self.manager.total_hours)


class ApplianceEnergySensor(ApplianceStatsEntity, SensorEntity):
    """Base energy sensor."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 3

    @staticmethod
    def _rounded(value: float) -> float:
        return round(value, 4)


class ApplianceEnergyActiveTotalSensor(ApplianceEnergySensor):
    """Total energy consumed while the appliance is active."""

    _attr_translation_key = "energy_active_total"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, manager: ApplianceStatsManager, entry: ConfigEntry) -> None:
        super().__init__(manager, entry)
        self._attr_unique_id = f"{entry.entry_id}_energy_active_total"
        self._attr_name = "Energy active total"

    @property
    def native_value(self) -> float:
        return self._rounded(self.manager.total_energy_kwh)


class ApplianceRunsTotalSensor(ApplianceStatsEntity, SensorEntity):
    """Total number of completed appliance runs."""

    _attr_translation_key = "runs_total"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 0
    _attr_icon = "mdi:counter"

    def __init__(self, manager: ApplianceStatsManager, entry: ConfigEntry) -> None:
        super().__init__(manager, entry)
        self._attr_unique_id = f"{entry.entry_id}_runs_total"
        self._attr_name = "Runs total"

    @property
    def native_value(self) -> int:
        return self.manager.runs_total
