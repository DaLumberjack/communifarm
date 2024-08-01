from homeassistant.helpers import discovery
from .const import DOMAIN

async def async_setup(hass, config):
    hass.data[DOMAIN] = {}
    await discovery.async_load_platform(hass, 'sensor', DOMAIN, {}, config)
    return True