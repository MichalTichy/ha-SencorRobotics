"""Support for Sencor Vaccums."""
import logging
from typing import Any
import voluptuous as vol

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumEntityFeature,
    STATE_IDLE,
    STATE_CLEANING,
    STATE_DOCKED,
    STATE_PAUSED,
    STATE_ERROR,
)

from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.icon import icon_for_battery_level

from .const import DOMAIN
from .devices.vacuum import SencorVacuum, WorkMode, WorkState

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config_entry, async_add_entities):
    """Set up the Sencor vacuums."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    device = config["device"]

    vacuums = [Vacuum(device)]  # Change name

    _LOGGER.debug("Adding Sencor Vacuums to Home Assistant: %s", vacuums)
    async_add_entities(vacuums)


async def async_setup_entry(hass, config_entry, async_add_entities):
    await async_setup_platform(hass, config_entry, async_add_entities)
    platform = entity_platform.async_get_current_platform()

    # This will call Entity.clean_room(entity_id=VALUE)
    platform.async_register_entity_service(
        "clean_rooms",
        {
            "rooms": [
                {
                    vol.Required('room_id'): cv.Number,
                    vol.Required('clean_num', default=1): cv.Number
                }
            ]
        },
        "clean_rooms",
    )


class Vacuum(StateVacuumEntity):

    fan_speed_map = {
        "intensive": WorkMode.Intensive,
        "standard": WorkMode.Standard,
        "silent": WorkMode.Silent,
    }

    work_state_map = {
        "intensive": WorkMode.Intensive,
        "standard": WorkMode.Standard,
        "silent": WorkMode.Silent,
    }

    def __init__(self, device: SencorVacuum) -> None:
        """Initialize the Sencor vacuum cleaner"""
        self.device = device
        self.device.update_state()
        self._attr_fan_speed = None
        self._attr_error = None

    @property
    def unique_id(self) -> str:
        return f"{self.device.host}"

    @property
    def name(self) -> str:
        return "Vacuum"

    @property
    def device_info(self):
        """Return the device info."""
        return {
            "identifiers": {(DOMAIN, self.device.host)},
            "name": self.name,
            "manufacturer": "Sencor",
            "sw_version": self.device.version,
        }

    @property
    def state(self) -> str:
        """Return the state of the vacuum cleaner."""
        current_work_state = self.device.work_state
        if current_work_state is WorkState.Cleaning:
            return STATE_CLEANING
        if current_work_state is WorkState.Idle:
            if self.device.had_work:
                return STATE_PAUSED
            return STATE_IDLE
        if current_work_state is WorkState.Returning:
            return STATE_IDLE
        if current_work_state in [WorkState.Docked, WorkState.Charging] :
            return STATE_DOCKED
        if current_work_state is WorkState.Problem:
            return STATE_ERROR
        _LOGGER.debug("Unkown work_state %s", current_work_state)
        return STATE_DOCKED

    @property
    def battery_level(self) -> int:
        """Return the battery level of the vacuum cleaner."""
        return self.device.battery_level

    @property
    def battery_icon(self) -> str:
        """Return the battery icon for the vacuum cleaner."""
        return icon_for_battery_level(
            battery_level=self.battery_level,
            charging=self.device.work_state == WorkState.Charging,
        )

    @property
    def fan_speed(self) -> str:
        """Return the fan speed of the vacuum cleaner."""
        current_work_mode = self.device.work_mode
        if current_work_mode is WorkMode.Intensive:
            return "intensive"
        elif current_work_mode is WorkMode.Standard:
            return "standard"
        elif current_work_mode is WorkMode.Silent:
            return "silent"
        return "standard"

    @property
    def fan_speed_list(self) -> list[str]:
        """Get the list of available fan speed steps of the vacuum cleaner."""
        return [
            "intensive",
            "standard",
            "silent",
        ]

    @property
    def supported_features(self) -> VacuumEntityFeature:
        """Flag vacuum cleaner features that are supported."""
        return (
            VacuumEntityFeature.PAUSE
            | VacuumEntityFeature.STOP
            | VacuumEntityFeature.RETURN_HOME
            | VacuumEntityFeature.FAN_SPEED
            | VacuumEntityFeature.BATTERY
            | VacuumEntityFeature.LOCATE
            | VacuumEntityFeature.STATE
            | VacuumEntityFeature.STATUS
            | VacuumEntityFeature.START
        )
    
    @property
    def rooms(self):
        """Return the state attributes of the vacuum cleaner."""
        rooms = []
        for room in self.device.rooms:
            rooms.append({
                "id": room["regionNum"],
                "name": room["regionName"],
            })
        return rooms

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the vacuum cleaner."""
        # Add room ids, progress, etc
        return {
            "charger_position": self.device.charger_position,
            "robot_position": self.device.robot_position,
            "rooms": self.rooms
        }

    async def async_return_to_base(self, **kwargs: Any) -> None:
        """Set the vacuum cleaner to return to the dock."""
        await self.device.charge()

    async def async_start(self, **kwargs: Any) -> None:
        """Start the vacuum cleaner."""
        await self.device.start()

    async def async_stop(self, **kwargs: Any) -> None:
        """Stop the vacuum cleaner."""
        await self.device.stop()

    async def async_pause(self, **kwargs: Any) -> None:
        """Stop the vacuum cleaner."""
        await self.device.pause()

    async def async_locate(self, **kwargs: Any) -> None:
        """Locate the vacuum cleaner."""
        await self.device.find()

    async def async_set_fan_speed(self, fan_speed: str, **kwargs: Any) -> None:
        """Set fan speed."""
        work_mode = self.fan_speed_map[fan_speed]
        await self.device.start(work_mode)

    async def async_update(self) -> None:
        await self.device.update_state()
        await self.device.update_map_data()
    
    async def clean_rooms(self, rooms: list[dict]):
        # Make sure all rooms exists
        await self.device.clean_rooms(rooms)
