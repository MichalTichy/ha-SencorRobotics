"""A Sencor vacuum."""
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
    
    SideBrushStuck = 104 
    NoContactWithFloor = 109                            
    RearWheelOverload = 105
    Stuck = 106
    LocalizationFailed = 119


class SencorVacuum(Connection):
    """A Sencor vacuum."""

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
        data = {"transitCmd":"98"}
        await self.send_request(data)
        state_data = await self.get_response()
        return state_data

    async def update_state(self) -> None:
        """Get and update state of the vacuum."""
        state_value = (await self.get_state_data())["value"]
        if "battery" in state_value:
            self.battery_level = state_value["battery"]
        if "version" in state_value:
            self.version = state_value["version"]
        if "extParam" in state_value and "hadWork" in state_value["extParam"]:
            self.had_work = state_value["extParam"]["hadWork"]
        if "error" in state_value:
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
        if "regionNames" in map_value:
            for room in map_value["regionNames"]:
                region_name = base64.b64decode(room["regionName"]).decode("utf-8")
                room["regionName"] = region_name
            self.rooms = map_value["regionNames"]
        if "chargerPos" in map_value:
            self.charger_position = map_value["chargerPos"]
        if "robotPos" in map_value:
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

    async def clean_rooms(self, rooms: list[dict]) -> None:
        """Clean specific rooms"""

        rooms_request: list[dict] = []
        # Remove duplicates and change format
        for room in rooms:
            room_id_str = str(room["room_id"])
            if not any(room_id_str == x["blockNum"] for x in rooms_request):
                rooms_request.append({
                    "cleanNum":str(room["clean_num"]),
                    "blockNum":room_id_str
                })
        data = {
            "opCmd":"cleanBlocks",
            "cleanBlocks":sorted(rooms_request, key=lambda x: x["blockNum"]),
        }
        await self.send_request(data,b'2.3.1')

    async def find(self) -> None:
        """Announce vacuum's location"""
        data = {
            "find": "",
            "transitCmd": "143",
        }
        await self.send_request(data)
