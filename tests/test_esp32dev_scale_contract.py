"""Contract tests for esp32dev scale mock entity IDs."""

from __future__ import annotations

from pathlib import Path

from custom_components.communifarm.fixtures.esp32dev_scale import (
    ESP32DEV_MOCK_INJECTORS,
    ESP32DEV_PUBLIC_ENTITIES,
    NFC_UID_TO_INGREDIENT,
    RECIPE_INGREDIENTS,
)


def test_public_entities_use_esp32dev_prefix() -> None:
    for entity_id in ESP32DEV_PUBLIC_ENTITIES:
        assert "esp32dev" in entity_id


def test_recipe_ingredients_cover_wood_lover_lines() -> None:
    assert "hardwood pellets" in RECIPE_INGREDIENTS
    assert "potash" in RECIPE_INGREDIENTS
    assert len(RECIPE_INGREDIENTS) >= 9


def test_nfc_uid_map_points_at_recipe_ingredients() -> None:
    for ingredient in NFC_UID_TO_INGREDIENT.values():
        assert ingredient in RECIPE_INGREDIENTS


def test_package_yaml_mentions_public_entities() -> None:
    package = (
        Path(__file__).resolve().parents[1]
        / "devcontainer"
        / "ha_config"
        / "packages"
        / "mock_esp32dev_scale.yaml"
    )
    text = package.read_text(encoding="utf-8")
    assert "esp32dev Calibrated g" in text
    assert "esp32dev Selected Ingredient" in text
    assert "esp32dev Simulate NFC Scan" in text
    for entity_id in ESP32DEV_PUBLIC_ENTITIES:
        # Package uses friendly names; object ids follow HA slug rules from those names.
        slug = entity_id.split(".", 1)[1].replace("_", " ")
        assert "esp32dev" in slug or entity_id.startswith("input_select.")
    assert "input_number.esp32dev_inject_calibrated_sensor" in text
    assert ESP32DEV_MOCK_INJECTORS[0] in text
