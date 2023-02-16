"""A Cleanmate vacuum."""
import base64
from enum import Enum
from typing import Tuple
from ..connection import Connection

class WorkMode(Enum):
    """The cleaning intensity."""

    Intensive = 7
    Standard = 1
    Silent = 9
    Unknown = 99


class WorkState(Enum):
    """The work state."""

    Cleaning = 1
    Idle = 2
    Returning = 4
    Charging = 5
    Docked = 6
    Error = 7
    Problem = 9
    Unknown = 99


class MopMode(Enum):
    """The mop intensity."""

    High = 20
    Medium = 40
    Low = 60
    Unknown = 99


class ErrorCode(Enum):
    """The error code"""
    
    SideBrushStuck = 104 # Sidoborsten/-arna har fastnat. Vänligen kontrollera.
                         # Lossa och rensa borstarna från föremål/smuts. Se till att de kan rotera fritt.
    NoContactWithFloow = 109 # Roboten har inte kontakt med golver
                             # Placera roboten med båda hjulen på golvet och starta på nytt.
    RearWheelOverload = 105
    Stuck = 106
    LocalizationFailed = 119


class CleanmateVacuum(Connection):
    """A Cleanmate vacuum."""

    # Values from state response
    battery_level: int = None
    version: str = None
    work_mode: WorkMode = None
    work_state: WorkState = None
    had_work: bool = False
    mop_mode: MopMode = None
    volume: int = None
    error_code: int = None

    # Values from map response
    rooms: list = []
    charger_position: Tuple[int, int] = ()
    robot_position: Tuple[int, int] = ()

    async def get_state_data(self) -> dict:
        """Get state data of the vacuum."""
        data = {"state": "", "transitCmd": "98"}
        await self.send_request(data)
        state_data = await self.get_response()
        return state_data

    async def update_state(self) -> None:
        """Get and update state of the vacuum."""
        state_value = (await self.get_state_data())["value"]
        self.battery_level = state_value["battery"]
        self.version = state_value["version"]
        self.had_work = state_value["extParam"]["hadWork"]
        self.error_code = state_value["error"]

        try:
            self.work_mode = WorkMode(state_value["workMode"])
        except:
            self.work_mode = WorkMode.Unknown
        try:
            self.work_state = WorkState(state_value["workState"])
        except:
            self.work_state = WorkState.Unknown
        try:
            self.mop_mode = MopMode(state_value["waterTank"])
        except:
            self.mop_mode = MopMode.Unknown

    async def get_map_data(self) -> dict:
        """Get map data of the vacuum."""
        data = {
            "mapWidth": "0",
            "centerPoint": "0",
            "mapHeight": "0",
            "trackNum": "AAA=",
            "mapSign": "AAA=",
            "transitCmd": "133",
        }
        await self.send_request(data)
        map_data = await self.get_response()
        return map_data
    
    async def update_map_data(self) -> None:
        """Get and update map data of the vacuum."""
        map_value = (await self.get_map_data())["value"]
        for room in map_value["regionNames"]:
            region_name = base64.b64decode(room["regionName"]).decode("utf-8")
            room["regionName"] = region_name
        self.rooms = map_value["regionNames"]
        self.charger_position = map_value["chargerPos"]
        self.robot_position = map_value["robotPos"]

    async def start(self, work_mode: WorkMode = None) -> None:
        """Start cleaning."""
        if work_mode is None:
            data = {
                "start": "1",
                "transitCmd": "100",
            }
        else:
            data = {
                "mode": str(work_mode.value),
                "transitCmd": "106",
            }
        await self.send_request(data)

    async def stop(self):
        """Stop cleaning."""
        data = {
            "stop": "1",
            "isStop": "1",
            "transitCmd": "102",
        }
        await self.send_request(data)

    async def pause(self) -> None:
        """Pause cleaning."""
        data = {
            "pause": "1",
            "isStop": "0",
            "transitCmd": "102",
        }
        await self.send_request(data)

    async def charge(self) -> None:
        """Go to charging station."""
        data = {
            "charge": "1",
            "transitCmd": "104",
        }
        await self.send_request(data)

    async def set_mop_mode(self, mop_mode: MopMode) -> None:
        """Set mop mode of the vacuum."""
        data = {
            "waterTank": str(mop_mode.value),
            "transitCmd": "145",
        }
        await self.send_request(data)

    async def set_volume(self, volume: int) -> None:
        """Set volume of the vacuum."""
        vol = 1 + round((volume / 100) * 10) / 10
        data = {
            "volume": str(vol),
            "voice": "",
            "transitCmd": "123",
        }
        await self.send_request(data)

    async def clean_rooms(self, room_ids: list[int]) -> None:
        """Clean specific rooms"""
        unique_sorted_ids = sorted(list(dict.fromkeys(room_ids)))
        clean_blocks = list(
            map(
                lambda room_id: {"cleanNum": "1", "blockNum": str(room_id)},
                unique_sorted_ids,
            )
        )
        data = {
            "opCmd": "cleanBlocks",
            "cleanBlocks": clean_blocks,
        }
        await self.send_request(data)

    async def find(self) -> None:
        """Announce vacuum's location"""
        data = {
            "find": "",
            "transitCmd": "143",
        }
        await self.send_request(data)
