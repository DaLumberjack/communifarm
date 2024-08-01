from homeassistant.helpers.event import async_track_time_interval
from datetime import timedelta

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    async_add_entities([PhotoperiodAutomation(config)])

class PhotoperiodAutomation:
    def __init__(self, config):
        self._hass = hass
        self._config = config
        self._interval = timedelta(minutes=1)
        async_track_time_interval(hass, self._check_events, self._interval)

    async def _check_events(self, time):
        calendar_entity = self._hass.states.get(f"calendar.{self._config['plant']}_photoperiod")
        light_entity = self._hass.states.get(self._config['light_entity_id'])
        now = self._hass.helpers.dt.now()

        for event in calendar_entity.attributes['events']:
            start = self._hass.helpers.dt.parse_datetime(event['start']['dateTime'])
            end = self._hass.helpers.dt.parse_datetime(event['end']['dateTime'])
            
            if start <= now <= end:
                if light_entity.state != 'on':
                    await self._hass.services.async_call('light', 'turn_on', {'entity_id': self._config['light_entity_id']})
            else:
                if light_entity.state != 'off':
                    await self._hass.services.async_call('light', 'turn_off', {'entity_id': self._config['light_entity_id']})
