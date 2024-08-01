from homeassistant.components.light import LightEntity
from .const import DOMAIN

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    async_add_entities([CommunifarmLight(config)])

class CommunifarmLight(LightEntity):
    def __init__(self, config):
        self._name = config['light_entity_id']
        self._is_on = False

    @property
    def name(self):
        return self._name

    @property
    def is_on(self):
        return self._is_on

    async def async_turn_on(self, **kwargs):
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self._is_on = False
        self.async_write_ha_state()
