"""Config flow for Communifarm onboarding."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector

from .const import (
    CONF_BATCH_NAME,
    CONF_ENVIRONMENT_NAME,
    CONF_FAN_ENTITY,
    CONF_HUMIDITY_ENTITY,
    CONF_HUMIDITY_TARGET,
    CONF_SITE_NAME,
    CONF_SWITCH_ENTITY,
    CONF_TEMPERATURE_ENTITY,
    CONF_TEMPERATURE_TARGET,
    DEFAULT_HUMIDITY_TARGET,
    DEFAULT_TEMPERATURE_TARGET,
    DOMAIN,
    ROLE_FAN,
    ROLE_HUMIDITY,
    ROLE_SWITCH,
    ROLE_TEMPERATURE,
)
from .domain.models import (
    CommunifarmState,
    EntityBinding,
    Environment,
    EnvironmentalProfile,
    ProductionBatch,
    Site,
    suggest_role_from_entity,
)


def _entity_meta(hass: HomeAssistant, entity_id: str) -> tuple[str, str | None, str | None]:
    state = hass.states.get(entity_id)
    domain = entity_id.split(".", 1)[0]
    if state is None:
        return domain, None, None
    device_class = state.attributes.get("device_class")
    unit = state.attributes.get("unit_of_measurement")
    return domain, device_class, unit


def _stable_entry_id(hass: HomeAssistant, entity_id: str) -> str:
    registry = er.async_get(hass)
    entry = registry.async_get(entity_id)
    if entry is not None:
        return entry.id
    # Tests / unbound entities: persist entity_id as a stable stand-in.
    return entity_id


def _suggest_entities(hass: HomeAssistant) -> dict[str, str | None]:
    suggestions: dict[str, str | None] = {
        ROLE_TEMPERATURE: None,
        ROLE_HUMIDITY: None,
        ROLE_FAN: None,
        ROLE_SWITCH: None,
    }
    for entity_id in hass.states.async_entity_ids():
        domain, device_class, unit = _entity_meta(hass, entity_id)
        role = suggest_role_from_entity(domain, device_class, unit)
        if role and suggestions.get(role) is None:
            suggestions[role] = entity_id
    return suggestions


class CommunifarmConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Communifarm config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._site_name: str | None = None
        self._environment_name: str | None = None
        self._batch_name: str | None = None
        self._temperature_entity: str | None = None
        self._humidity_entity: str | None = None
        self._fan_entity: str | None = None
        self._switch_entity: str | None = None
        self._temperature_target: float = DEFAULT_TEMPERATURE_TARGET
        self._humidity_target: float = DEFAULT_HUMIDITY_TARGET

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            self._site_name = user_input[CONF_SITE_NAME]
            self._environment_name = user_input[CONF_ENVIRONMENT_NAME]
            return await self.async_step_bindings()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SITE_NAME, default="Home Site"): str,
                    vol.Required(CONF_ENVIRONMENT_NAME, default="Main Tent"): str,
                }
            ),
        )

    async def async_step_bindings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        suggestions = _suggest_entities(self.hass)
        if user_input is not None:
            self._temperature_entity = user_input.get(CONF_TEMPERATURE_ENTITY)
            self._humidity_entity = user_input.get(CONF_HUMIDITY_ENTITY)
            self._fan_entity = user_input.get(CONF_FAN_ENTITY)
            self._switch_entity = user_input.get(CONF_SWITCH_ENTITY)
            return await self.async_step_profile()

        fields: dict[Any, Any] = {}
        for key, role, domain in (
            (CONF_TEMPERATURE_ENTITY, ROLE_TEMPERATURE, "sensor"),
            (CONF_HUMIDITY_ENTITY, ROLE_HUMIDITY, "sensor"),
            (CONF_FAN_ENTITY, ROLE_FAN, "fan"),
            (CONF_SWITCH_ENTITY, ROLE_SWITCH, "switch"),
        ):
            suggested = suggestions.get(role)
            entity_selector = selector.EntitySelector(
                selector.EntitySelectorConfig(domain=domain)
            )
            if suggested:
                fields[vol.Optional(key, default=suggested)] = entity_selector
            else:
                fields[vol.Optional(key)] = entity_selector
        return self.async_show_form(step_id="bindings", data_schema=vol.Schema(fields))

    async def async_step_profile(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._temperature_target = float(user_input[CONF_TEMPERATURE_TARGET])
            self._humidity_target = float(user_input[CONF_HUMIDITY_TARGET])
            self._batch_name = user_input[CONF_BATCH_NAME]
            return await self._async_create_entry()

        return self.async_show_form(
            step_id="profile",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_TEMPERATURE_TARGET, default=DEFAULT_TEMPERATURE_TARGET
                    ): vol.Coerce(float),
                    vol.Required(
                        CONF_HUMIDITY_TARGET, default=DEFAULT_HUMIDITY_TARGET
                    ): vol.Coerce(float),
                    vol.Required(CONF_BATCH_NAME, default="Batch 1"): str,
                }
            ),
        )

    async def _async_create_entry(self) -> FlowResult:
        assert self._site_name and self._environment_name and self._batch_name
        site = Site(name=self._site_name)
        environment = Environment(name=self._environment_name, site_id=site.id)
        profile = EnvironmentalProfile(
            temperature_target=self._temperature_target,
            humidity_target=self._humidity_target,
        )
        profile.validate()
        batch = ProductionBatch(name=self._batch_name, environment_id=environment.id)

        bindings: list[EntityBinding] = []
        role_map = {
            ROLE_TEMPERATURE: self._temperature_entity,
            ROLE_HUMIDITY: self._humidity_entity,
            ROLE_FAN: self._fan_entity,
            ROLE_SWITCH: self._switch_entity,
        }
        for role, entity_id in role_map.items():
            if not entity_id:
                continue
            bindings.append(
                EntityBinding(
                    role=role,
                    entity_entry_id=_stable_entry_id(self.hass, entity_id),
                    entity_id=entity_id,
                )
            )

        state = CommunifarmState(
            site=site,
            environment=environment,
            profile=profile,
            batch=batch,
            bindings=bindings,
        )

        return self.async_create_entry(
            title=f"{site.name} / {environment.name}",
            data={
                "state": state.to_dict(),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> CommunifarmOptionsFlow:
        return CommunifarmOptionsFlow(config_entry)


class CommunifarmOptionsFlow(config_entries.OptionsFlow):
    """Options flow for profile targets and bindings."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        current = CommunifarmState.from_dict(self._config_entry.data["state"])
        if user_input is not None:
            current.profile.temperature_target = float(
                user_input[CONF_TEMPERATURE_TARGET]
            )
            current.profile.humidity_target = float(user_input[CONF_HUMIDITY_TARGET])
            current.profile.validate()

            new_bindings: list[EntityBinding] = []
            role_map = {
                ROLE_TEMPERATURE: user_input.get(CONF_TEMPERATURE_ENTITY),
                ROLE_HUMIDITY: user_input.get(CONF_HUMIDITY_ENTITY),
                ROLE_FAN: user_input.get(CONF_FAN_ENTITY),
                ROLE_SWITCH: user_input.get(CONF_SWITCH_ENTITY),
            }
            for role, entity_id in role_map.items():
                if not entity_id:
                    continue
                new_bindings.append(
                    EntityBinding(
                        role=role,
                        entity_entry_id=_stable_entry_id(self.hass, entity_id),
                        entity_id=entity_id,
                    )
                )
            current.bindings = new_bindings

            new_data = {**self._config_entry.data, "state": current.to_dict()}
            self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)
            return self.async_create_entry(title="", data={})

        resolved = {
            binding.role: binding.entity_id for binding in current.bindings
        }
        fields: dict[Any, Any] = {
            vol.Required(
                CONF_TEMPERATURE_TARGET,
                default=current.profile.temperature_target,
            ): vol.Coerce(float),
            vol.Required(
                CONF_HUMIDITY_TARGET,
                default=current.profile.humidity_target,
            ): vol.Coerce(float),
        }
        for key, role, domain in (
            (CONF_TEMPERATURE_ENTITY, ROLE_TEMPERATURE, "sensor"),
            (CONF_HUMIDITY_ENTITY, ROLE_HUMIDITY, "sensor"),
            (CONF_FAN_ENTITY, ROLE_FAN, "fan"),
            (CONF_SWITCH_ENTITY, ROLE_SWITCH, "switch"),
        ):
            suggested = resolved.get(role)
            entity_selector = selector.EntitySelector(
                selector.EntitySelectorConfig(domain=domain)
            )
            if suggested:
                fields[vol.Optional(key, default=suggested)] = entity_selector
            else:
                fields[vol.Optional(key)] = entity_selector
        return self.async_show_form(step_id="init", data_schema=vol.Schema(fields))
