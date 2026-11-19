"""Protocol regressions using a real local TCP server, without HA dependencies."""
import asyncio
import json
from pathlib import Path
import sys
import types
import unittest

# Load protocol modules without executing the HA integration entry point.
ROOT = Path(__file__).resolve().parents[1] / 'custom_components' / 'sencor'
package = types.ModuleType('sencor_protocol_tests')
package.__path__ = [str(ROOT)]
sys.modules[package.__name__] = package
from sencor_protocol_tests.connection import Connection
from sencor_protocol_tests.devices.vacuum import SencorVacuum, WorkMode


def frame(value):
    body = json.dumps(value, ensure_ascii=False).encode('utf-8')
    return (len(body) + 20).to_bytes(4, 'little') + bytes(16) + body


class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.requests = []
        self.handlers = set()
        self.errors = []
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.behavior = 'normal'
        self.server = await asyncio.start_server(self.handle, '127.0.0.1', 0)
        self.device = SencorVacuum('127.0.0.1', 'secret-auth', 'robot-id')
        self.device.port = self.server.sockets[0].getsockname()[1]
        self.device.timeout = 1

    async def asyncTearDown(self):
        self.release.set()
        self.server.close()
        await self.server.wait_closed()
        if self.handlers:
            await asyncio.wait_for(asyncio.gather(*self.handlers), 2)
        self.assertEqual(self.errors, [])

    async def handle(self, reader, writer):
        task = asyncio.current_task()
        self.handlers.add(task)
        try:
            header = await reader.readexactly(20)
            self.assertEqual(header[4:].hex(), 'fa00c8000000eb27ea27000000000000')
            body = await reader.readexactly(int.from_bytes(header[:4], 'little') - 20)
            request = json.loads(body)
            self.requests.append(request)
            self.started.set()
            if self.behavior == 'blocked':
                await self.release.wait()
            if request['value'].get('transitCmd') in ('98', '133'):
                response = frame({'value': {'battery': '80', 'name': 'Kuchyně'}})
                if self.behavior == 'invalid':
                    response = bytes(20)
                elif self.behavior == 'truncated':
                    response = response[:23]
                elif self.behavior == 'silent':
                    await reader.read()
                    return
                # Deliberately split the size field, header and body across writes.
                for chunk in (response[:2], response[2:11], response[11:23], response[23:]):
                    writer.write(chunk)
                    await writer.drain()
                    await asyncio.sleep(0.001)
                if self.behavior in ('invalid', 'truncated'):
                    return
            # Commands intentionally have no acknowledgement; all clients must close.
            self.assertEqual(await asyncio.wait_for(reader.read(), 1), b'')
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as err:
            self.errors.append(err)
        finally:
            writer.close()
            await writer.wait_closed()
            self.handlers.discard(task)

    async def test_fragmented_response_and_utf8(self):
        result = await self.device.get_state_data()
        self.assertEqual(result['value'], {'battery': 80, 'name': 'Kuchyně'})
        self.assertIsNone(self.device.writer)

    async def test_poll_and_start_are_serialized(self):
        self.behavior = 'blocked'
        poll = asyncio.create_task(self.device.get_state_data())
        await self.started.wait()
        start = asyncio.create_task(self.device.start())
        await asyncio.sleep(0.02)
        self.assertEqual(len(self.requests), 1)
        self.release.set()
        result, _ = await asyncio.gather(poll, start)
        self.assertEqual(result['value']['battery'], 80)
        await asyncio.sleep(0.02)
        self.assertEqual([r['value']['transitCmd'] for r in self.requests], ['98', '100'])

    async def test_commands_close_without_requiring_ack(self):
        await self.device.start()
        await self.device.pause()
        await self.device.stop()
        await self.device.charge()
        await self.device.start(WorkMode.Standard)
        await self.device.clean_rooms([{'room_id': 4, 'clean_num': 1}])
        await asyncio.sleep(0.02)
        self.assertEqual([r['value'].get('transitCmd') for r in self.requests],
                         ['100', '102', '102', '104', '106', None])
        self.assertEqual(self.requests[0]['value'], {'start': '1', 'transitCmd': '100'})
        self.assertEqual(self.requests[0]['version'], '1.5.11')
        self.assertEqual(self.requests[-1]['version'], '2.3.1')
        self.assertEqual(self.requests[-1]['value']['cleanBlocks'], [{'cleanNum': '1', 'blockNum': '4'}])
        self.assertIsNone(self.device.writer)

    async def test_timeout_releases_socket_and_allows_next_command(self):
        self.behavior = 'silent'
        self.device.timeout = 0.05
        with self.assertRaises(TimeoutError):
            await self.device.get_state_data()
        self.assertIsNone(self.device.writer)
        self.behavior = 'normal'
        await self.device.start()

    async def test_cancel_releases_socket_and_lock(self):
        self.behavior = 'silent'
        poll = asyncio.create_task(self.device.get_state_data())
        await self.started.wait()
        poll.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await poll
        self.assertIsNone(self.device.writer)
        self.behavior = 'normal'
        await self.device.start()

    async def test_truncated_frame_fails_and_recovers(self):
        self.behavior = 'truncated'
        with self.assertRaises(asyncio.IncompleteReadError):
            await self.device.get_state_data()
        self.assertIsNone(self.device.writer)
        self.behavior = 'normal'
        await self.device.start()

    async def test_invalid_size_fails_and_recovers(self):
        self.behavior = 'invalid'
        with self.assertRaises(ValueError):
            await self.device.get_state_data()
        self.behavior = 'normal'
        await self.device.start()

    async def test_debug_log_excludes_credentials(self):
        with self.assertLogs('sencor_protocol_tests.connection', level='DEBUG') as logs:
            await self.device.start()
        self.assertNotIn('secret-auth', '\n'.join(logs.output))


if __name__ == '__main__':
    unittest.main()
