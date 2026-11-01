"""Text platform — variety name + Intake purchase / machine / employee drafts."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ENTITY_INTAKE_EMPLOYEE_LABEL,
    ENTITY_INTAKE_MACHINE_LABEL,
    ENTITY_INTAKE_PURCHASE_DATE,
    ENTITY_INTAKE_PURCHASE_LOCATION,
    ENTITY_VARIETY_NAME,
)
from .entity import CommunifarmEntity


class CommunifarmText(CommunifarmEntity, TextEntity):
    """Text identity and entry bucket."""


@dataclass(frozen=True, slots=True)
class _TextSpec:
    name: str
    unique_id: str
    entity_id: str
    icon: str
    bucket_key: str
    default: str
    native_max: int = 64


class CommunifarmBucketText(CommunifarmText):
    _attr_mode = "text"
    _attr_native_min = 0

    def __init__(self, entry_id: str, spec: _TextSpec) -> None:
        super().__init__(
            entry_id,
            name=spec.name,
            unique_id=spec.unique_id,
            entity_id=spec.entity_id,
            icon=spec.icon,
        )
        self._bucket_key = spec.bucket_key
        self._value = spec.default
        self._attr_native_max = spec.native_max

    async def async_added_to_hass(self) -> None:
        self.bucket()[self._bucket_key] = self._value

    @property
    def native_value(self) -> str | None:
        return self._value

    async def async_set_value(self, value: str) -> None:
        self._value = value or ""
        self.bucket()[self._bucket_key] = self._value
        self.async_write_ha_state()


_TEXTS: tuple[_TextSpec, ...] = (
    _TextSpec(
        "Intake purchase location",
        "communifarm_intake_purchase_location",
        ENTITY_INTAKE_PURCHASE_LOCATION,
        "mdi:store",
        "intake_purchase_location",
        "",
        64,
    ),
    _TextSpec(
        "Intake purchase date (YYYY-MM-DD)",
        "communifarm_intake_purchase_date",
        ENTITY_INTAKE_PURCHASE_DATE,
        "mdi:calendar",
        "intake_purchase_date",
        "",
        32,
    ),
    _TextSpec(
        "Intake machine label",
        "communifarm_intake_machine_label",
        ENTITY_INTAKE_MACHINE_LABEL,
        "mdi:cog",
        "intake_machine_label",
        "PN532 station",
        64,
    ),
    _TextSpec(
        "Intake employee badge label",
        "communifarm_intake_employee_label",
        ENTITY_INTAKE_EMPLOYEE_LABEL,
        "mdi:badge-account",
        "intake_employee_label",
        "Operator",
        64,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(
        [
            CommunifarmVarietyNameText(entry.entry_id),
            *[CommunifarmBucketText(entry.entry_id, spec) for spec in _TEXTS],
        ]
    )


class CommunifarmVarietyNameText(CommunifarmText):
    _attr_name = "New variety name"
    _attr_unique_id = "communifarm_variety_name"
    _attr_icon = "mdi:mushroom"
    _attr_native_min = 0
    _attr_native_max = 64
    _attr_mode = "text"

    def __init__(self, entry_id: str) -> None:
        super().__init__(entry_id, entity_id=ENTITY_VARIETY_NAME)
        self._value = ""

    async def async_added_to_hass(self) -> None:
        self.bucket()["variety_name_draft"] = self._value

    @property
    def native_value(self) -> str | None:
        return self._value

    async def async_set_value(self, value: str) -> None:
        self._value = value or ""
        self.bucket()["variety_name_draft"] = self._value
        self.async_write_ha_state()
