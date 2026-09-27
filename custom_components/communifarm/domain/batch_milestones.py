"""Batch mix / process milestone types (pure domain)."""

from __future__ import annotations

# Weigh-tab / auto
MILESTONE_DRY_MIXING_STARTED = "dry_mixing_started"
MILESTONE_WATER_ADDED = "water_added"
MILESTONE_DRY_WET_MIX_STARTED = "dry_wet_mix_started"
MILESTONE_SETTLING_STARTED = "settling_started"
MILESTONE_FIELD_CAPACITY_REACHED = "field_capacity_reached"

# Batches tab
MILESTONE_COMPLETELY_MIXED = "completely_mixed"
MILESTONE_CONTAINERS_SEPARATED = "containers_separated"
MILESTONE_HEAT_TREATED = "heat_treated"
MILESTONE_STORED_FOR_COOLING = "stored_for_cooling"
MILESTONE_PRODUCTION_CYCLE_STARTED = "production_cycle_started"
MILESTONE_BATCH_COMPLETED = "batch_completed"
MILESTONE_BATCH_CREATED = "batch_created"

HEAT_STERILIZED = "sterilized"
HEAT_PASTEURIZED = "pasteurized"
HEAT_METHODS = frozenset({HEAT_STERILIZED, HEAT_PASTEURIZED})

WEIGH_MILESTONES = frozenset(
    {
        MILESTONE_WATER_ADDED,
        MILESTONE_DRY_WET_MIX_STARTED,
        MILESTONE_SETTLING_STARTED,
        MILESTONE_FIELD_CAPACITY_REACHED,
    }
)

BATCH_TAB_MILESTONES = frozenset(
    {
        MILESTONE_COMPLETELY_MIXED,
        MILESTONE_CONTAINERS_SEPARATED,
        MILESTONE_HEAT_TREATED,
        MILESTONE_STORED_FOR_COOLING,
        MILESTONE_PRODUCTION_CYCLE_STARTED,
    }
)

BATCH_STATUS_ACTIVE = "active"
BATCH_STATUS_COMPLETE = "complete"
