"""Connection flow for Sencor Vacuum integration."""
import logging
import asyncio
import json
from .helpers import parse_value

_LOGGER = logging.getLogger(__name__)

class Connection:
    """Connection to a vacuum."""
    host: str
    auth_code: str
    device_id: str

    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter

    
    def __init__(self, host: str, auth_code: str,device_id:str) -> None:
        self.host = host
        self.auth_code = auth_code
        self.device_id = device_id

    async def connect(self) -> None:
        """Connect to the vacuum."""
        self.reader, self.writer = await asyncio.open_connection(self.host, 8888)
        self.writer.write_timeout = 10
        self.writer.read_timeout = 10

    async def disconnect(self) -> None:
        """Disconnect from the vacuum."""
        self.writer.close()
        self.reader = None
        self.writer = None

    def _get_request_prefix(self, size: int) -> str:
        size_hex = "{0:x}".format(size)
        temp = f"{'0'*(8-len(size_hex))}{size_hex}"
        return "".join(map(str.__add__, temp[-2::-2], temp[-1::-2]))

    async def send_request(self, data: dict[str, any], version:bytes = b'1.5.11') -> None:
        """Send a request to the vacuum."""
        
        datastring = json.dumps(data,separators=(',', ':'))
        body = b'{"cmd":0,"control":{"authCode":"' \
            + str.encode(self.auth_code) \
            + b'","deviceIp":"' + str.encode(self.host) \
            + b'","devicePort":"8888","targetId":"' \
            + str.encode(self.device_id) \
            + b'","targetType":"3"},"seq":0,"value":' \
            + str.encode(datastring)  \
            + b',"version":"'+version+b'"}'
        
        request_size = len(body) + 20
        prefix = self._get_request_prefix(request_size)
        header = bytes.fromhex(f"{prefix}fa00c8000000eb27ea27000000000000")
        packet = header+body
        
        _LOGGER.debug('Sending: ' \
            +'header: '+''.join(f'{byte:02x}' for byte in header) \
            + ' body: '+body.decode())
        await self.send_raw_request(packet)

    async def send_raw_request(self, raw_data: bytes) -> None:
        """Send a raw request to the Sencor vacuum."""
        await self.connect()
        self.writer.write(raw_data)
        await self.writer.drain()
        
    async def read_data(self, bytes: int) -> bytes:
        data = await self.reader.read(bytes)
        if(not data): 
            raise ConnectionError
        return data
    
    async def get_response(self):
        try:
            # Read size from header
            header = await self.read_data(20)

            raw_size_hex = header[:4].hex()

            # Reverse the order pairwise
            size_hex: str = "".join(
                map(str.__add__, raw_size_hex[-2::-2], raw_size_hex[-1::-2])
            )
            size = (
                int(size_hex, base=16) - len(header)
            )  # Minus the header that we already gathered

            # Read actual data
            data = b""
            while len(data) < size:
                data += await self.read_data(size)
            response = parse_value(data.decode("ascii"))
            return response
        except asyncio.TimeoutError as err:
            raise err
