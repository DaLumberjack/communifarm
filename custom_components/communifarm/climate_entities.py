"""Preset entities for the sensors and machines drawn on the schematic."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import PERCENTAGE, UnitOfPressure, UnitOfTemperature

from .domain.climate import ROLE_FLOAT, ROLE_HUMIDITY, ROLE_PRESSURE, ROLE_TEMPERATURE
from .domain.climate_drawing import (
    DrawingDevice,
    drawing_devices,
    drawing_entity_id,
    drawing_name,
    drawing_object_id,
)
from .entity import CommunifarmEntity

_SENSOR_CLASS = {
    ROLE_TEMPERATURE: (SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, "mdi:thermometer"),
    ROLE_HUMIDITY: (SensorDeviceClass.HUMIDITY, PERCENTAGE, "mdi:water-percent"),
    ROLE_PRESSURE: (SensorDeviceClass.PRESSURE, UnitOfPressure.HPA, "mdi:gauge"),
}

_SWITCH_ICON = {
    "ac": "mdi:air-conditioner",
    "heater": "mdi:radiator",
    "fresh_air_intake": "mdi:fan",
    "condensate_pump": "mdi:pump",
}


class CommunifarmDrawingSensor(CommunifarmEntity, SensorEntity):
    """Stand-in probe. A real sensor replaces it with bind_climate_role."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, entry_id: str, device: DrawingDevice) -> None:
        object_id = drawing_object_id(device)
        device_class, unit, icon = _SENSOR_CLASS[device.role]
        super().__init__(
            entry_id,
            entity_id=drawing_entity_id(device),
            name=drawing_name(device),
            unique_id=object_id,
            icon=icon,
        )
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._value = device.initial

    @property
    def native_value(self) -> float | None:
        return self._value


class CommunifarmDrawingSwitch(CommunifarmEntity, SwitchEntity):
    """Stand-in machine the climate tick can turn on and off."""

    def __init__(self, entry_id: str, device: DrawingDevice) -> None:
        object_id = drawing_object_id(device)
        super().__init__(
            entry_id,
            entity_id=drawing_entity_id(device),
            name=drawing_name(device),
            unique_id=object_id,
            icon=_SWITCH_ICON.get(device.role, "mdi:toggle-switch"),
        )
        self._is_on = False

    @property
    def is_on(self) -> bool:
        return self._is_on

    async def async_turn_on(self, **kwargs) -> None:
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self._is_on = False
        self.async_write_ha_state()


class CommunifarmDrawingBinarySensor(CommunifarmEntity, BinarySensorEntity):
    """Stand-in float. Off until a real float is bound over it."""

    def __init__(self, entry_id: str, device: DrawingDevice) -> None:
        object_id = drawing_object_id(device)
        icon = "mdi:cup-water" if device.role == ROLE_FLOAT else "mdi:circle-outline"
        super().__init__(
            entry_id,
            entity_id=drawing_entity_id(device),
            name=drawing_name(device),
            unique_id=object_id,
            icon=icon,
        )
        self._is_on = False

    @property
    def is_on(self) -> bool:
        return self._is_on


def drawing_sensor_entities(entry_id: str) -> list[CommunifarmDrawingSensor]:
    return [
        CommunifarmDrawingSensor(entry_id, device)
        for device in drawing_devices()
        if device.platform == "sensor"
    ]


def drawing_switch_entities(entry_id: str) -> list[CommunifarmDrawingSwitch]:
    return [
        CommunifarmDrawingSwitch(entry_id, device)
        for device in drawing_devices()
        if device.platform == "switch"
    ]


def drawing_binary_entities(entry_id: str) -> list[CommunifarmDrawingBinarySensor]:
    return [
        CommunifarmDrawingBinarySensor(entry_id, device)
        for device in drawing_devices()
        if device.platform == "binary_sensor"
    ]
