"""Local TCP connection to a Sencor vacuum."""
import asyncio
import json
import logging
from typing import Any

from .helpers import parse_value

_LOGGER = logging.getLogger(__name__)


class Connection:
    """Serialize complete transactions on the vacuum's local TCP interface."""

    port = 8888
    timeout = 10
    header_size = 20
    max_response_size = 16 * 1024 * 1024

    def __init__(self, host: str, auth_code: str, device_id: str) -> None:
        self.host = host
        self.auth_code = auth_code
        self.device_id = device_id
        self.reader = None
        self.writer = None
        self._request_lock = asyncio.Lock()

    async def connect(self) -> None:
        """Connect within the transaction timeout."""
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)

    async def disconnect(self) -> None:
        """Release the socket, including after failed or cancelled requests."""
        writer = self.writer
        self.reader = self.writer = None
        if writer is not None:
            writer.close()
            try:
                await asyncio.wait_for(writer.wait_closed(), self.timeout)
            except (OSError, TimeoutError):
                _LOGGER.debug("Error closing vacuum connection", exc_info=True)

    def _get_request_prefix(self, size: int) -> str:
        return size.to_bytes(4, "little").hex()

    async def send_request(
        self, data: dict[str, Any], version: bytes = b"1.5.11",
        *, expect_response: bool = False,
    ) -> Any:
        """Send a command or perform an atomic query and response exchange."""
        body = json.dumps({
            "cmd": 0,
            "control": {
                "authCode": self.auth_code,
                "deviceIp": self.host,
                "devicePort": str(self.port),
                "targetId": self.device_id,
                "targetType": "3",
            },
            "seq": 0,
            "value": data,
            "version": version.decode("ascii"),
        }, separators=(",", ":")).encode("utf-8")
        prefix = self._get_request_prefix(len(body) + self.header_size)
        header = bytes.fromhex(f"{prefix}fa00c8000000eb27ea27000000000000")
        # Never log the packet body: it contains the authentication code.
        _LOGGER.debug("Sending vacuum request (%s bytes)", len(header) + len(body))
        async with self._request_lock:
            try:
                async with asyncio.timeout(self.timeout):
                    await self.send_raw_request(header + body)
                    if expect_response:
                        return await self.get_response()
            finally:
                await self.disconnect()

    async def send_raw_request(self, raw_data: bytes) -> None:
        """Write a packet inside a serialized transaction."""
        await self.connect()
        self.writer.write(raw_data)
        await self.writer.drain()

    async def read_data(self, size: int) -> bytes:
        """Read an exact frame fragment, regardless of TCP segmentation."""
        return await self.reader.readexactly(size)

    async def get_response(self) -> Any:
        """Read one length-prefixed response inside the transaction timeout."""
        header = await self.read_data(self.header_size)
        size = int.from_bytes(header[:4], "little") - self.header_size
        if not 0 < size <= self.max_response_size:
            raise ValueError(f"Invalid vacuum response size: {size}")
        data = await self.read_data(size)
        return parse_value(data.decode("utf-8"))
