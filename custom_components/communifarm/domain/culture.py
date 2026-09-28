"""Culture lots + media prep (pure domain, no Home Assistant)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .models import new_id
from .recipe import RecipeLine, clamp_recipe_scale
from .validation import ValidationError, validate_readable_name
from .weight import ingredient_key_from_label

# --- Acquisition / form catalogs ---
SOURCE_WILD = "wild"
SOURCE_ACQUAINTANCE = "acquaintance"
SOURCE_PURCHASED = "purchased"
SOURCE_TYPES = frozenset({SOURCE_WILD, SOURCE_ACQUAINTANCE, SOURCE_PURCHASED})

FORM_LIQUID_CULTURE = "liquid_culture"
FORM_AGAR = "agar"
FORM_SPORES = "spores"
CULTURE_FORMS = frozenset({FORM_LIQUID_CULTURE, FORM_AGAR, FORM_SPORES})

CONTAINER_SYRINGE = "syringe"
CONTAINER_STERILE_BAG = "sterile_bag"
CONTAINER_PLATE = "plate"
CONTAINER_JAR = "jar"
CONTAINER_SLANT = "slant"
CONTAINER_OTHER = "other"
CULTURE_CONTAINERS = frozenset(
    {
        CONTAINER_SYRINGE,
        CONTAINER_STERILE_BAG,
        CONTAINER_PLATE,
        CONTAINER_JAR,
        CONTAINER_SLANT,
        CONTAINER_OTHER,
    }
)

CULTURE_STATUS_ACTIVE = "active"
CULTURE_STATUS_RETIRED = "retired"
CULTURE_STATUS_CONTAMINATED = "contaminated"
CULTURE_STATUS_CONSUMED = "consumed"
CULTURE_STATUSES = frozenset(
    {
        CULTURE_STATUS_ACTIVE,
        CULTURE_STATUS_RETIRED,
        CULTURE_STATUS_CONTAMINATED,
        CULTURE_STATUS_CONSUMED,
    }
)

# --- Media batch ---
MEDIA_FORM_AGAR = "agar"
MEDIA_FORM_LC = "liquid_culture"
MEDIA_FORMS = frozenset({MEDIA_FORM_AGAR, MEDIA_FORM_LC})

VESSEL_PLATE = "plate"
VESSEL_JAR = "jar"
VESSEL_TYPES = frozenset({VESSEL_PLATE, VESSEL_JAR})

MEDIA_STATUS_PLANNED = "planned"
MEDIA_STATUS_WEIGHING = "weighing"
MEDIA_STATUS_STERILIZING = "sterilizing"
MEDIA_STATUS_READY = "media_ready"
MEDIA_STATUS_IN_USE = "in_use"
MEDIA_STATUS_COMPLETE = "complete"
MEDIA_STATUS_FAILED = "failed"
MEDIA_STATUSES = frozenset(
    {
        MEDIA_STATUS_PLANNED,
        MEDIA_STATUS_WEIGHING,
        MEDIA_STATUS_STERILIZING,
        MEDIA_STATUS_READY,
        MEDIA_STATUS_IN_USE,
        MEDIA_STATUS_COMPLETE,
        MEDIA_STATUS_FAILED,
    }
)

# Statuses that may accept culture into the vessel body.
MEDIA_ACCEPT_CULTURE_STATUSES = frozenset({MEDIA_STATUS_READY, MEDIA_STATUS_IN_USE})

RECIPE_MEA_AGAR_500 = "mea_agar_500"
RECIPE_HONEY_LC_500 = "honey_lc_500"
RECIPE_KARO_LC_500 = "karo_lc_500"
DEFAULT_AGAR_RECIPE_KEY = RECIPE_MEA_AGAR_500
DEFAULT_LC_RECIPE_KEY = RECIPE_HONEY_LC_500

MEA_AGAR_500_RECIPE: tuple[RecipeLine, ...] = (
    RecipeLine("distilled water", 500.0, "ml"),
    RecipeLine("agar-agar powder", 10.0, "g"),
    RecipeLine("light malt extract", 10.0, "g"),
)

HONEY_LC_500_RECIPE: tuple[RecipeLine, ...] = (
    RecipeLine("distilled water", 500.0, "ml"),
    RecipeLine("honey", 20.0, "g"),
)

KARO_LC_500_RECIPE: tuple[RecipeLine, ...] = (
    RecipeLine("distilled water", 500.0, "ml"),
    RecipeLine("light corn syrup", 20.0, "ml"),
)

MEDIA_RECIPES: dict[str, tuple[RecipeLine, ...]] = {
    RECIPE_MEA_AGAR_500: MEA_AGAR_500_RECIPE,
    RECIPE_HONEY_LC_500: HONEY_LC_500_RECIPE,
    RECIPE_KARO_LC_500: KARO_LC_500_RECIPE,
}

# Append-only media milestones (snake_case, matches batch style).
MILESTONE_WEIGHING_STARTED = "weighing_started"
MILESTONE_MEDIA_DISSOLVED = "media_dissolved"
MILESTONE_MEDIA_PORTIONED = "media_portioned"
MILESTONE_MEDIA_STERILIZED = "media_sterilized"
MILESTONE_MEDIA_READY = "media_ready"
MILESTONE_MEDIA_FAILED = "media_failed"
MILESTONE_LC_STIR_STARTED = "lc_stir_started"
MILESTONE_LC_STIR_STOPPED = "lc_stir_stopped"

MEDIA_MILESTONES = frozenset(
    {
        MILESTONE_WEIGHING_STARTED,
        MILESTONE_MEDIA_DISSOLVED,
        MILESTONE_MEDIA_PORTIONED,
        MILESTONE_MEDIA_STERILIZED,
        MILESTONE_MEDIA_READY,
        MILESTONE_MEDIA_FAILED,
        MILESTONE_LC_STIR_STARTED,
        MILESTONE_LC_STIR_STOPPED,
    }
)

# Status-changing milestones only. Stir start/stop keep current media status.
MILESTONE_TO_MEDIA_STATUS: dict[str, str] = {
    MILESTONE_WEIGHING_STARTED: MEDIA_STATUS_WEIGHING,
    MILESTONE_MEDIA_DISSOLVED: MEDIA_STATUS_WEIGHING,
    MILESTONE_MEDIA_PORTIONED: MEDIA_STATUS_WEIGHING,
    MILESTONE_MEDIA_STERILIZED: MEDIA_STATUS_STERILIZING,
    MILESTONE_MEDIA_READY: MEDIA_STATUS_READY,
    MILESTONE_MEDIA_FAILED: MEDIA_STATUS_FAILED,
}

# Culture process events
EVENT_CULTURE_ACQUIRED = "culture_acquired"
EVENT_MEDIA_BATCH_CREATED = "media_batch_created"
EVENT_MEDIA_WEIGHED = "media_weighed"
EVENT_CULTURE_INTRODUCED = "culture_introduced"
EVENT_CULTURE_DRAWN = "culture_drawn"
EVENT_CULTURE_TRANSFER = "culture_transfer"
EVENT_CULTURE_INOCULATED_BATCH = "culture_inoculated_batch"
EVENT_CULTURE_CONTAMINATED = "culture_contaminated"
EVENT_CULTURE_RETIRED = "culture_retired"

# LC mason-jar lid expectations (documented on recipe meta; not separate columns yet).
LC_LID_FEATURES = frozenset({"syringe_port", "breathability_port", "stir_bar"})

MEDIA_RECIPE_META: dict[str, dict[str, str]] = {
    RECIPE_MEA_AGAR_500: {
        "media_form": MEDIA_FORM_AGAR,
        "vessel_type": VESSEL_PLATE,
        "name": "MEA agar 500 ml",
    },
    RECIPE_HONEY_LC_500: {
        "media_form": MEDIA_FORM_LC,
        "vessel_type": VESSEL_JAR,
        "name": "Honey LC 500 ml",
        "vessel_notes": "mason_jar+syringe_port+breathability_port+stir_bar",
    },
    RECIPE_KARO_LC_500: {
        "media_form": MEDIA_FORM_LC,
        "vessel_type": VESSEL_JAR,
        "name": "Karo LC 500 ml",
        "vessel_notes": "mason_jar+syringe_port+breathability_port+stir_bar",
    },
}

ALLOWED_MEDIA_UNITS = frozenset({"g", "ml"})


@dataclass(slots=True)
class CultureLot:
    """Stable culture inventory unit."""

    site_id: str
    environment_id: str
    name: str
    source_type: str
    form: str
    container: str
    strain_label: str = ""
    parent_culture_id: str | None = None
    status: str = CULTURE_STATUS_ACTIVE
    acquired_at: str | None = None
    nfc_uid: str | None = None
    notes: str | None = None
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = new_id("culture")
        validate_culture_lot_fields(self)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MediaBatch:
    """One media prep run (agar plates or LC jars)."""

    site_id: str
    environment_id: str
    name: str
    recipe_key: str
    media_form: str
    vessel_type: str
    recipe_scale: float = 1.0
    status: str = MEDIA_STATUS_PLANNED
    vessel_count: int | None = None
    sterilized_at: str | None = None
    ready_at: str | None = None
    nfc_uid: str | None = None
    notes: str | None = None
    created_at: str | None = None
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = new_id("media")
        self.recipe_scale = clamp_recipe_scale(self.recipe_scale)
        validate_media_batch_fields(self)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MediaWeightEvent:
    """One recorded media ingredient weigh/measure."""

    site_id: str
    environment_id: str
    media_batch_id: str
    amount: float
    unit: str
    recorded_at: str
    ingredient_key: str | None = None
    ingredient_label: str | None = None
    recipe_scale: float | None = None
    target_amount: float | None = None
    source_entity_id: str | None = None
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = new_id("mwgt")
        if self.ingredient_label and not self.ingredient_key:
            self.ingredient_key = ingredient_key_from_label(self.ingredient_label)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CultureEvent:
    """Append-only culture / media / production inoculate process event."""

    event_type: str
    recorded_at: str
    culture_id: str | None = None
    child_culture_id: str | None = None
    media_batch_id: str | None = None
    batch_id: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = new_id("cevt")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_culture_lot_fields(lot: CultureLot) -> None:
    validate_readable_name(lot.name, field_name="culture name")
    if lot.source_type not in SOURCE_TYPES:
        raise ValidationError(f"source_type must be one of {sorted(SOURCE_TYPES)}")
    if lot.form not in CULTURE_FORMS:
        raise ValidationError(f"form must be one of {sorted(CULTURE_FORMS)}")
    if lot.container not in CULTURE_CONTAINERS:
        raise ValidationError(f"container must be one of {sorted(CULTURE_CONTAINERS)}")
    if lot.status not in CULTURE_STATUSES:
        raise ValidationError(f"status must be one of {sorted(CULTURE_STATUSES)}")
    if lot.strain_label and len(lot.strain_label) > 64:
        raise ValidationError("strain_label must be at most 64 characters")


def validate_media_batch_fields(batch: MediaBatch) -> None:
    validate_readable_name(batch.name, field_name="media batch name")
    if batch.recipe_key not in MEDIA_RECIPES:
        raise ValidationError(f"unknown media recipe_key: {batch.recipe_key}")
    if batch.media_form not in MEDIA_FORMS:
        raise ValidationError(f"media_form must be one of {sorted(MEDIA_FORMS)}")
    if batch.vessel_type not in VESSEL_TYPES:
        raise ValidationError(f"vessel_type must be one of {sorted(VESSEL_TYPES)}")
    if batch.status not in MEDIA_STATUSES:
        raise ValidationError(f"status must be one of {sorted(MEDIA_STATUSES)}")
    meta = MEDIA_RECIPE_META[batch.recipe_key]
    if batch.media_form != meta["media_form"]:
        raise ValidationError(
            f"media_form {batch.media_form} does not match recipe {batch.recipe_key}"
        )


def media_recipe_lines(recipe_key: str) -> tuple[RecipeLine, ...]:
    if recipe_key not in MEDIA_RECIPES:
        raise ValidationError(f"unknown media recipe_key: {recipe_key}")
    return MEDIA_RECIPES[recipe_key]


def build_media_batch_from_recipe(
    *,
    site_id: str,
    environment_id: str,
    recipe_key: str = DEFAULT_AGAR_RECIPE_KEY,
    name: str | None = None,
    recipe_scale: float = 1.0,
    vessel_count: int | None = None,
    nfc_uid: str | None = None,
    notes: str | None = None,
) -> MediaBatch:
    if recipe_key not in MEDIA_RECIPES:
        raise ValidationError(f"unknown media recipe_key: {recipe_key}")
    meta = MEDIA_RECIPE_META[recipe_key]
    return MediaBatch(
        site_id=site_id,
        environment_id=environment_id,
        name=name or meta["name"],
        recipe_key=recipe_key,
        media_form=meta["media_form"],
        vessel_type=meta["vessel_type"],
        recipe_scale=recipe_scale,
        vessel_count=vessel_count,
        nfc_uid=nfc_uid,
        notes=notes,
    )


def assert_media_accepts_culture(status: str) -> None:
    """Hard gate: culture may only enter ready / in-use media bodies."""
    if status not in MEDIA_ACCEPT_CULTURE_STATUSES:
        raise ValidationError(
            "media batch must be media_ready (or already in_use) before introducing culture"
        )


def validate_media_amount(amount: float, unit: str) -> tuple[float, str]:
    if unit not in ALLOWED_MEDIA_UNITS:
        raise ValidationError(f"unit must be one of {sorted(ALLOWED_MEDIA_UNITS)}")
    try:
        value = float(amount)
    except (TypeError, ValueError) as err:
        raise ValidationError("amount must be a number") from err
    if value != value or value in (float("inf"), float("-inf")):  # NaN / Inf
        raise ValidationError("amount must be a finite number")
    if value < 0:
        raise ValidationError("amount must be >= 0")
    return value, unit


def child_culture_from_parent(
    parent: CultureLot,
    *,
    name: str | None = None,
    form: str | None = None,
    container: str | None = None,
    acquired_at: str | None = None,
) -> CultureLot:
    """Always create a new child lot — never mutate parent identity."""
    return CultureLot(
        site_id=parent.site_id,
        environment_id=parent.environment_id,
        name=name or f"{parent.name} child",
        source_type=parent.source_type,
        form=form or parent.form,
        container=container
        or (CONTAINER_PLATE if (form or parent.form) == FORM_AGAR else parent.container),
        strain_label=parent.strain_label,
        parent_culture_id=parent.id,
        status=CULTURE_STATUS_ACTIVE,
        acquired_at=acquired_at,
        notes=f"expanded from {parent.id}",
    )


def target_for_media_ingredient(
    recipe_key: str, ingredient_key: str, recipe_scale: float
) -> tuple[float, str] | None:
    scale = clamp_recipe_scale(recipe_scale)
    for line in media_recipe_lines(recipe_key):
        if line.key == ingredient_key:
            return line.amount * scale, line.unit
    return None
