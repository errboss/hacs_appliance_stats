"""Runtime manager for Appliance Stats."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, EVENT_HOMEASSISTANT_STOP, UnitOfEnergy
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_CURRENT_ENERGY,
    ATTR_CURRENT_POWER,
    ATTR_DELAY_OFF,
    ATTR_DELAY_ON,
    ATTR_ENERGY_ENTITY,
    ATTR_POWER_THRESHOLD,
    ATTR_SOURCE_ENTITY,
    ATTR_UPDATE_INTERVAL,
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
    STORAGE_SAVE_DELAY,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)
_INVALID_STATES = {"unknown", "unavailable", "none", "None"}


def _utcnow() -> datetime:
    return dt_util.utcnow()


class ApplianceStatsManager:
    """Track appliance activity, runtime, energy, and completed runs."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.name: str = entry.title or entry.data[CONF_NAME]

        config = {**entry.data, **entry.options}
        self.source_entity: str = config[CONF_SOURCE_ENTITY]
        self.energy_entity: str | None = config.get(CONF_ENERGY_ENTITY)
        self.power_threshold: float = float(config.get(CONF_POWER_THRESHOLD, DEFAULT_POWER_THRESHOLD))
        self.delay_on: int = int(config.get(CONF_DELAY_ON, DEFAULT_DELAY_ON))
        self.delay_off: int = int(config.get(CONF_DELAY_OFF, DEFAULT_DELAY_OFF))
        self.update_interval: int = int(config.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))

        self._store: Store = Store(hass, STORAGE_VERSION, f"{DOMAIN}_{entry.entry_id}")
        self._listeners: list[Callable[[], None]] = []
        self._unsubscribers: list[Callable[[], None]] = []

        self._is_active = False
        self._run_in_progress = False
        self._current_power: float | None = None
        self._current_energy_kwh: float | None = None
        self._source_available = False
        self._energy_available = False
        self._pending_on_since: datetime | None = None
        self._pending_off_since: datetime | None = None
        self._last_accounting_at: datetime | None = None
        self._last_energy_value_kwh: float | None = None

        self._total_hours = 0.0
        self._total_energy_kwh = 0.0
        self._runs_total = 0

    async def async_setup(self) -> None:
        """Set up the runtime manager."""
        stored = await self._store.async_load() or {}
        self._restore(stored)

        now = _utcnow()
        self._last_accounting_at = now
        self._refresh(now)

        tracked_entities = [self.source_entity]
        if self.energy_entity:
            tracked_entities.append(self.energy_entity)

        self._unsubscribers.append(
            async_track_state_change_event(self.hass, tracked_entities, self._handle_tracked_state_change)
        )
        self._unsubscribers.append(
            async_track_time_interval(self.hass, self._handle_timer_tick, timedelta(seconds=self.update_interval))
        )
        self._unsubscribers.append(self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self._handle_stop))

        self._notify_listeners()

    async def async_unload(self) -> None:
        """Unload the runtime manager."""
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
        await self._store.async_save(self._serialize())

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def current_power(self) -> float | None:
        return self._current_power

    @property
    def current_energy_kwh(self) -> float | None:
        return self._current_energy_kwh

    @property
    def source_available(self) -> bool:
        return self._source_available

    @property
    def energy_available(self) -> bool:
        return self._energy_available

    @property
    def total_hours(self) -> float:
        return self._total_hours

    @property
    def total_energy_kwh(self) -> float:
        return self._total_energy_kwh

    @property
    def runs_total(self) -> int:
        return self._runs_total

    @property
    def extra_attributes(self) -> dict[str, Any]:
        return {
            ATTR_SOURCE_ENTITY: self.source_entity,
            ATTR_ENERGY_ENTITY: self.energy_entity,
            ATTR_POWER_THRESHOLD: self.power_threshold,
            ATTR_DELAY_ON: self.delay_on,
            ATTR_DELAY_OFF: self.delay_off,
            ATTR_UPDATE_INTERVAL: self.update_interval,
            ATTR_CURRENT_POWER: self.current_power,
            ATTR_CURRENT_ENERGY: self.current_energy_kwh,
        }

    @callback
    def async_add_listener(self, update_callback: Callable[[], None]) -> Callable[[], None]:
        """Register a callback that is fired on manager updates."""
        self._listeners.append(update_callback)

        @callback
        def _remove_listener() -> None:
            self._listeners.remove(update_callback)

        return _remove_listener

    @callback
    def _handle_timer_tick(self, now: datetime) -> None:
        self._refresh(now)

    @callback
    def _handle_tracked_state_change(self, _event) -> None:
        self._refresh(_utcnow())

    async def _handle_stop(self, _event) -> None:
        await self._store.async_save(self._serialize())

    @callback
    def _refresh(self, now: datetime) -> None:
        """Refresh internal state from the source sensors and account new values."""
        if self._last_accounting_at is None:
            self._last_accounting_at = now

        previously_active = self._is_active
        previous_energy_value = self._last_energy_value_kwh

        self._account_runtime_until(now)
        self._update_current_power()
        self._update_current_energy()
        self._account_energy_delta(previous_energy_value)

        above_threshold = self._source_available and self._current_power is not None and self._current_power > self.power_threshold

        if above_threshold:
            self._pending_off_since = None
            if self._is_active:
                pass
            elif self.delay_on == 0:
                self._activate(now)
            elif self._pending_on_since is None:
                self._pending_on_since = now
            elif (now - self._pending_on_since).total_seconds() >= self.delay_on:
                self._activate(now)
        else:
            self._pending_on_since = None
            if self._is_active and self.delay_off == 0:
                self._deactivate()
            elif self._is_active and self._pending_off_since is None:
                self._pending_off_since = now
            elif self._is_active and (now - self._pending_off_since).total_seconds() >= self.delay_off:
                self._deactivate()

        if previously_active != self._is_active or above_threshold != previously_active:
            self._schedule_save()

        self._notify_listeners()

    @callback
    def _activate(self, now: datetime) -> None:
        self._is_active = True
        self._run_in_progress = True
        self._pending_on_since = None
        self._pending_off_since = None
        self._last_accounting_at = now
        self._schedule_save()

    @callback
    def _deactivate(self) -> None:
        self._is_active = False
        self._pending_off_since = None
        if self._run_in_progress:
            self._runs_total += 1
        self._run_in_progress = False
        self._schedule_save()

    @callback
    def _account_runtime_until(self, now: datetime) -> None:
        """Account runtime between the previous update and now."""
        if self._last_accounting_at is None:
            self._last_accounting_at = now
            return

        if now <= self._last_accounting_at:
            return

        start = self._last_accounting_at
        self._last_accounting_at = now

        if not self._is_active:
            return

        segment_hours = (now - start).total_seconds() / 3600
        self._total_hours += segment_hours
        self._schedule_save()

    @callback
    def _account_energy_delta(self, previous_energy_value: float | None) -> None:
        """Account the delta of the selected energy entity while active."""
        current_energy_value = self._current_energy_kwh

        if current_energy_value is None:
            return

        if previous_energy_value is None:
            self._last_energy_value_kwh = current_energy_value
            return

        delta_kwh = current_energy_value - previous_energy_value
        self._last_energy_value_kwh = current_energy_value

        if delta_kwh <= 0:
            if delta_kwh < 0:
                _LOGGER.debug(
                    "Energy sensor %s moved backwards from %s to %s, ignoring delta",
                    self.energy_entity,
                    previous_energy_value,
                    current_energy_value,
                )
            return

        if not self._is_active:
            return

        self._total_energy_kwh += delta_kwh
        self._schedule_save()

    @callback
    def _update_current_power(self) -> None:
        """Read the power source entity state and parse it to a float."""
        state = self.hass.states.get(self.source_entity)
        self._source_available = False
        self._current_power = None

        if state is None:
            return

        raw_state = state.state
        if raw_state in _INVALID_STATES:
            return

        try:
            self._current_power = float(raw_state)
        except (TypeError, ValueError):
            _LOGGER.debug("Unable to parse power value '%s' for %s", raw_state, self.source_entity)
            return

        self._source_available = True

    @callback
    def _update_current_energy(self) -> None:
        """Read the selected energy entity and normalize it to kWh."""
        self._energy_available = False
        self._current_energy_kwh = None

        if not self.energy_entity:
            return

        state = self.hass.states.get(self.energy_entity)
        if state is None:
            return

        raw_state = state.state
        if raw_state in _INVALID_STATES:
            return

        try:
            raw_value = float(raw_state)
        except (TypeError, ValueError):
            _LOGGER.debug("Unable to parse energy value '%s' for %s", raw_state, self.energy_entity)
            return

        unit = state.attributes.get("unit_of_measurement")
        normalized_value = self._energy_to_kwh(raw_value, unit)
        if normalized_value is None:
            _LOGGER.debug("Unsupported energy unit '%s' for %s", unit, self.energy_entity)
            return

        self._current_energy_kwh = normalized_value
        self._energy_available = True

    @staticmethod
    def _energy_to_kwh(value: float, unit: str | None) -> float | None:
        if unit in (None, UnitOfEnergy.KILO_WATT_HOUR):
            return value
        if unit == UnitOfEnergy.WATT_HOUR:
            return value / 1000
        if unit == UnitOfEnergy.MEGA_WATT_HOUR:
            return value * 1000
        if unit == UnitOfEnergy.GIGA_WATT_HOUR:
            return value * 1_000_000
        return None

    @callback
    def _schedule_save(self) -> None:
        self._store.async_delay_save(self._serialize, STORAGE_SAVE_DELAY)

    def _serialize(self) -> dict[str, Any]:
        return {
            "is_active": self._is_active,
            "run_in_progress": self._run_in_progress,
            "current_power": self._current_power,
            "current_energy_kwh": self._current_energy_kwh,
            "source_available": self._source_available,
            "energy_available": self._energy_available,
            "pending_on_since": self._datetime_to_str(self._pending_on_since),
            "pending_off_since": self._datetime_to_str(self._pending_off_since),
            "last_accounting_at": self._datetime_to_str(self._last_accounting_at),
            "last_energy_value_kwh": self._last_energy_value_kwh,
            "total_hours": self._total_hours,
            "total_energy_kwh": self._total_energy_kwh,
            "runs_total": self._runs_total,
        }

    def _restore(self, data: dict[str, Any]) -> None:
        self._is_active = bool(data.get("is_active", False))
        self._run_in_progress = bool(data.get("run_in_progress", self._is_active))
        self._current_power = self._safe_float(data.get("current_power"))
        self._current_energy_kwh = self._safe_float(data.get("current_energy_kwh"))
        self._source_available = bool(data.get("source_available", False))
        self._energy_available = bool(data.get("energy_available", False))
        self._pending_on_since = self._str_to_datetime(data.get("pending_on_since"))
        self._pending_off_since = self._str_to_datetime(data.get("pending_off_since"))
        self._last_accounting_at = self._str_to_datetime(data.get("last_accounting_at"))
        self._last_energy_value_kwh = self._safe_float(data.get("last_energy_value_kwh"))
        self._total_hours = self._safe_float(data.get("total_hours"), default=0.0) or 0.0
        self._total_energy_kwh = self._safe_float(data.get("total_energy_kwh"), default=0.0) or 0.0
        self._runs_total = self._safe_int(data.get("runs_total"), default=0) or 0

    @staticmethod
    def _safe_float(value: Any, default: float | None = None) -> float | None:
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_int(value: Any, default: int | None = None) -> int | None:
        if value is None:
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _datetime_to_str(value: datetime | None) -> str | None:
        return value.isoformat() if value is not None else None

    @staticmethod
    def _str_to_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        parsed = dt_util.parse_datetime(value)
        if parsed is None:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed

    @callback
    def _notify_listeners(self) -> None:
        for listener in list(self._listeners):
            listener()
