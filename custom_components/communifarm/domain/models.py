"""Pure domain models for Communifarm (no Home Assistant imports)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

from ..const import (
    ALLOWED_BATCH_TRANSITIONS,
    BATCH_STAGE_PLANNED,
    DEFAULT_HUMIDITY_TARGET,
    DEFAULT_TEMPERATURE_TARGET,
    ROLE_FAN,
    ROLE_HUMIDITY,
    ROLE_SWITCH,
    ROLE_TEMPERATURE,
)
from .validation import validate_nfc_uid, validate_readable_name


def new_id(prefix: str) -> str:
    """Return a stable Communifarm identifier."""
    return f"{prefix}_{uuid4().hex[:12]}"


@dataclass(slots=True)
class Site:
    """A physical or logical Communifarm site."""

    name: str
    id: str = field(default_factory=lambda: new_id("site"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Site:
        return cls(id=data["id"], name=data["name"])


@dataclass(slots=True)
class Environment:
    """An independently managed growing environment."""

    name: str
    site_id: str
    id: str = field(default_factory=lambda: new_id("env"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Environment:
        return cls(id=data["id"], name=data["name"], site_id=data["site_id"])


@dataclass(slots=True)
class EntityBinding:
    """Binding from a Communifarm role to a stable HA entity registry id."""

    role: str
    entity_entry_id: str
    entity_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EntityBinding:
        return cls(
            role=data["role"],
            entity_entry_id=data["entity_entry_id"],
            entity_id=data.get("entity_id"),
        )


@dataclass(slots=True)
class EnvironmentalProfile:
    """Basic environmental targets for an environment."""

    temperature_target: float = DEFAULT_TEMPERATURE_TARGET
    humidity_target: float = DEFAULT_HUMIDITY_TARGET

    def validate(self) -> None:
        if not (-40.0 <= self.temperature_target <= 80.0):
            raise ValueError("temperature_target out of range")
        if not (0.0 <= self.humidity_target <= 100.0):
            raise ValueError("humidity_target out of range")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EnvironmentalProfile:
        profile = cls(
            temperature_target=float(
                data.get("temperature_target", DEFAULT_TEMPERATURE_TARGET)
            ),
            humidity_target=float(data.get("humidity_target", DEFAULT_HUMIDITY_TARGET)),
        )
        profile.validate()
        return profile


@dataclass(slots=True)
class ProcessEvent:
    """Append-only process/audit event."""

    event_type: str
    detail: str
    timestamp: str
    id: str = field(default_factory=lambda: new_id("evt"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProcessEvent:
        return cls(
            id=data["id"],
            event_type=data["event_type"],
            detail=data["detail"],
            timestamp=data["timestamp"],
        )


@dataclass(slots=True)
class ProductionBatch:
    """Minimal production batch with a three-stage lifecycle."""

    name: str
    environment_id: str
    stage: str = BATCH_STAGE_PLANNED
    id: str = field(default_factory=lambda: new_id("batch"))
    # Written to NFC and follows the bag until split into containers.
    nfc_uid: str = ""
    events: list[ProcessEvent] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.nfc_uid:
            self.nfc_uid = self.id

    def can_transition(self, new_stage: str) -> bool:
        return new_stage in ALLOWED_BATCH_TRANSITIONS.get(self.stage, set())

    def transition(self, new_stage: str, timestamp: str) -> ProcessEvent:
        if not self.can_transition(new_stage):
            raise ValueError(f"cannot transition from {self.stage} to {new_stage}")
        previous = self.stage
        self.stage = new_stage
        event = ProcessEvent(
            event_type="StageChanged",
            detail=f"{previous}->{new_stage}",
            timestamp=timestamp,
        )
        self.events.append(event)
        return event

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "environment_id": self.environment_id,
            "stage": self.stage,
            "nfc_uid": self.nfc_uid,
            "events": [event.to_dict() for event in self.events],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProductionBatch:
        return cls(
            id=data["id"],
            name=data["name"],
            environment_id=data["environment_id"],
            stage=data.get("stage", BATCH_STAGE_PLANNED),
            nfc_uid=data.get("nfc_uid") or data["id"],
            events=[ProcessEvent.from_dict(item) for item in data.get("events", [])],
        )


@dataclass(slots=True)
class CommunifarmState:
    """Root mutable domain state persisted via the repository."""

    site: Site
    environment: Environment
    profile: EnvironmentalProfile
    batch: ProductionBatch
    bindings: list[EntityBinding] = field(default_factory=list)
    recipe_scale: float = 1.0
    schema_version: int = 1

    def binding_for(self, role: str) -> EntityBinding | None:
        for binding in self.bindings:
            if binding.role == role:
                return binding
        return None

    def validate(self) -> None:
        self.profile.validate()
        if not (0.1 <= self.recipe_scale <= 10.0):
            raise ValueError("recipe_scale must be between 0.1 and 10")
        validate_readable_name(self.site.name, field_name="site.name")
        validate_readable_name(self.environment.name, field_name="environment.name")
        validate_readable_name(self.batch.name, field_name="batch.name")
        validate_nfc_uid(self.batch.nfc_uid, required=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "site": self.site.to_dict(),
            "environment": self.environment.to_dict(),
            "profile": self.profile.to_dict(),
            "batch": self.batch.to_dict(),
            "bindings": [binding.to_dict() for binding in self.bindings],
            "recipe_scale": self.recipe_scale,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CommunifarmState:
        state = cls(
            schema_version=int(data.get("schema_version", 1)),
            site=Site.from_dict(data["site"]),
            environment=Environment.from_dict(data["environment"]),
            profile=EnvironmentalProfile.from_dict(data["profile"]),
            batch=ProductionBatch.from_dict(data["batch"]),
            bindings=[EntityBinding.from_dict(item) for item in data.get("bindings", [])],
            recipe_scale=float(data.get("recipe_scale", 1.0)),
        )
        state.validate()
        return state


def suggest_role_from_entity(
    domain: str,
    device_class: str | None,
    unit: str | None,
) -> str | None:
    """Suggest a Communifarm role from HA entity metadata (no name matching)."""
    device_class = (device_class or "").lower()
    unit = (unit or "").lower()
    if domain == "sensor":
        if device_class == "temperature" or unit in {"°c", "c", "°f", "f"}:
            return ROLE_TEMPERATURE
        if device_class == "humidity" or unit == "%":
            return ROLE_HUMIDITY
    if domain == "fan":
        return ROLE_FAN
    if domain == "switch":
        return ROLE_SWITCH
    return None
