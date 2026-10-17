"""Authorization boundary for persistent automation-setting changes."""

from __future__ import annotations

from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import HomeAssistantError


async def async_require_automation_settings_access(
    hass: HomeAssistant, context: Context | None
) -> None:
    """Require an HA administrator until Communifarm has an operator role."""
    if context is None or context.user_id is None:
        raise HomeAssistantError(
            "Automation settings require an authenticated Home Assistant administrator"
        )
    user = await hass.auth.async_get_user(context.user_id)
    if user is None or not user.is_admin:
        raise HomeAssistantError(
            "Automation settings require a Home Assistant administrator"
        )
