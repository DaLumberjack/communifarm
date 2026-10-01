"""Frozen entity identity. Playwright and existing installs key off these ids."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.communifarm import button, number, select, sensor, switch, text
from custom_components.communifarm.const import DOMAIN
from custom_components.communifarm.domain.models import CommunifarmState
from custom_components.communifarm.entity import CommunifarmEntity
from custom_components.communifarm.storage.repository import CommunifarmRepository

# entity_id, unique_id. unique_id is the object id (no domain prefix).
EXPECTED_ENTITIES: frozenset[tuple[str, str]] = frozenset(
    {
        ("sensor.communifarm_batch_stage", "communifarm_batch_stage"),
        ("sensor.communifarm_environment_status", "communifarm_environment_status"),
        ("sensor.communifarm_batch_nfc_uid", "communifarm_batch_nfc_uid"),
        ("sensor.communifarm_weigh_session", "communifarm_weigh_session"),
        ("sensor.communifarm_batch_list", "communifarm_batch_list"),
        ("sensor.communifarm_batch_milestones", "communifarm_batch_milestones"),
        ("sensor.communifarm_production_status", "communifarm_production_status"),
        ("sensor.communifarm_active_culture_id", "communifarm_active_culture_id"),
        ("sensor.communifarm_variety_list", "communifarm_variety_list"),
        ("sensor.communifarm_culture_inventory", "communifarm_culture_inventory"),
        ("sensor.communifarm_nfc_checkin", "communifarm_nfc_checkin"),
        ("sensor.communifarm_sales_status", "communifarm_sales_status"),
        ("number.communifarm_temperature_target", "communifarm_temperature_target"),
        ("number.communifarm_humidity_target", "communifarm_humidity_target"),
        ("number.communifarm_recipe_scale", "communifarm_recipe_scale"),
        ("number.communifarm_container_count", "communifarm_container_count"),
        ("number.communifarm_substrate_g_per_container", "communifarm_substrate_g_per_container"),
        ("number.communifarm_harvest_mass_g", "communifarm_harvest_mass_g"),
        ("number.communifarm_sale_mass_g", "communifarm_sale_mass_g"),
        ("number.communifarm_sale_line_amount", "communifarm_sale_line_amount"),
        ("switch.communifarm_allowlisted_switch", "communifarm_allowlisted_switch"),
        ("switch.communifarm_lc_stir_plate", "communifarm_lc_stir_plate"),
        ("button.communifarm_water_added", "communifarm_water_added"),
        ("button.communifarm_dry_wet_mix_started", "communifarm_dry_wet_mix_started"),
        ("button.communifarm_settling_started", "communifarm_settling_started"),
        ("button.communifarm_field_capacity_reached", "communifarm_field_capacity_reached"),
        ("button.communifarm_completely_mixed", "communifarm_completely_mixed"),
        ("button.communifarm_separate_containers", "communifarm_separate_containers"),
        ("button.communifarm_heat_treated", "communifarm_heat_treated"),
        ("button.communifarm_stored_for_cooling", "communifarm_stored_for_cooling"),
        ("button.communifarm_production_cycle_started", "communifarm_production_cycle_started"),
        ("button.communifarm_complete_and_new_batch", "communifarm_complete_and_new_batch"),
        ("button.communifarm_select_inoculum_from_nfc", "communifarm_select_inoculum_from_nfc"),
        ("button.communifarm_inoculate_batch", "communifarm_inoculate_batch"),
        ("button.communifarm_move_to_incubation", "communifarm_move_to_incubation"),
        ("button.communifarm_move_to_fruiting", "communifarm_move_to_fruiting"),
        ("button.communifarm_move_to_harvest", "communifarm_move_to_harvest"),
        ("button.communifarm_record_harvest", "communifarm_record_harvest"),
        ("button.communifarm_final_harvest", "communifarm_final_harvest"),
        ("button.communifarm_nfc_checkin_harvest", "communifarm_nfc_checkin_harvest"),
        ("button.communifarm_confirm_container_harvest", "communifarm_confirm_container_harvest"),
        (
            "button.communifarm_confirm_final_container_harvest",
            "communifarm_confirm_final_container_harvest",
        ),
        ("button.communifarm_create_variety", "communifarm_create_variety"),
        ("button.communifarm_retire_variety", "communifarm_retire_variety"),
        ("button.communifarm_acquire_culture", "communifarm_acquire_culture"),
        ("button.communifarm_set_culture_status", "communifarm_set_culture_status"),
        ("button.communifarm_record_sale", "communifarm_record_sale"),
        ("button.communifarm_record_sale_cleanup", "communifarm_record_sale_cleanup"),
        ("select.communifarm_heat_treatment", "communifarm_heat_treatment"),
        ("select.communifarm_container_type", "communifarm_container_type"),
        ("select.communifarm_active_inoculum", "communifarm_active_inoculum"),
        ("select.communifarm_catalog_variety", "communifarm_catalog_variety"),
        ("select.communifarm_acquire_form", "communifarm_acquire_form"),
        ("select.communifarm_acquire_source", "communifarm_acquire_source"),
        ("select.communifarm_culture_vessel_status", "communifarm_culture_vessel_status"),
        ("select.communifarm_payment_method", "communifarm_payment_method"),
        ("select.communifarm_sale_venue", "communifarm_sale_venue"),
        ("select.communifarm_sale_buyer", "communifarm_sale_buyer"),
        ("text.communifarm_variety_name", "communifarm_variety_name"),
    }
)


async def test_platform_entities_keep_identity_and_base(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    sample_state: CommunifarmState,
) -> None:
    """Every platform entity subclasses CommunifarmEntity and keeps its ids."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][mock_config_entry.entry_id] = {
        "state": sample_state,
        "repository": CommunifarmRepository(hass),
    }
    captured: list[CommunifarmEntity] = []

    def _add(entities, update_before_add: bool = False) -> None:
        del update_before_add
        captured.extend(entities)

    for platform in (sensor, number, switch, button, select, text):
        await platform.async_setup_entry(hass, mock_config_entry, _add)

    pairs = {(entity.entity_id, entity.unique_id) for entity in captured}
    assert pairs == EXPECTED_ENTITIES
    assert all(isinstance(entity, CommunifarmEntity) for entity in captured)
