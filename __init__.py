from homeassistant.helpers import discovery
from .const import DOMAIN

async def async_setup(hass, config):
    hass.data[DOMAIN] = {}
    await discovery.async_load_platform(hass, 'calendar', DOMAIN, {}, config)
    await discovery.async_load_platform(hass, 'light', DOMAIN, {}, config)
    await discovery.async_load_platform(hass, 'automation', DOMAIN, {}, config)
    return True