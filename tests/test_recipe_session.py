"""Weigh session / recipe scale unit tests."""

from __future__ import annotations

from custom_components.communifarm.domain.recipe import (
    WOOD_LOVER_RECIPE,
    build_weigh_session_progress,
    clamp_recipe_scale,
)
from custom_components.communifarm.domain.weight import WeightEvent


def test_clamp_recipe_scale() -> None:
    assert clamp_recipe_scale(0.01) == 0.1
    assert clamp_recipe_scale(99) == 10.0
    assert clamp_recipe_scale(2.5) == 2.5


def test_weigh_session_progress_scaled_targets_and_status() -> None:
    events = [
        WeightEvent(
            site_id="s",
            environment_id="e",
            batch_id="b",
            mass_g=6000.0,
            ingredient_key="hardwood_pellets",
            ingredient_label="hardwood pellets",
            recorded_at="2026-09-27T01:00:00+00:00",
        )
    ]
    progress = build_weigh_session_progress(
        batch_id="b",
        batch_nfc_uid="batch_nfc",
        recipe_scale=2.0,
        events=events,
    )
    assert progress.completed == 1
    assert progress.total == len(WOOD_LOVER_RECIPE)
    pellets = progress.lines[0]
    assert pellets.target_amount == 6000.0
    assert pellets.status == "close"
    assert progress.next_label == "hardwood shavings"
    assert "hardwood pellets" in progress.progress_text()
    assert "×2" in progress.progress_text()
