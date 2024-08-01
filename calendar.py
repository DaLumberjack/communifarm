from homeassistant.components.calendar import CalendarEntity
from homeassistant.helpers.entity import generate_entity_id
from .const import DOMAIN

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    async_add_entities([PhotoperiodCalendar(config)])

class PhotoperiodCalendar(CalendarEntity):
    def __init__(self, config):
        self._name = f"{config['plant']} Photoperiod"
        self._entity_id = generate_entity_id('calendar.{}', self._name, hass=hass)
        self._events = []

    @property
    def name(self):
        return self._name

    @property
    def event(self):
        return self._events

    async def async_create_event(self, start_time, end_time):
        event = {
            'start': {'dateTime': start_time.isoformat()},
            'end': {'dateTime': end_time.isoformat()},
            'summary': f"{self._name} Event"
        }
        self._events.append(event)
        self.async_write_ha_state()
