"""Entity contract checks against the installed Home Assistant package."""
import importlib.util
import unittest
import warnings
from unittest.mock import AsyncMock

from test_protocol import SencorVacuum
from sencor_protocol_tests.devices.vacuum import WorkState

HAS_HA = importlib.util.find_spec('homeassistant') is not None
if HAS_HA:
    # Ignore known warnings in HA's dependencies only during the HA import;
    # integration code and test execution still run with warnings as errors.
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', message='Inheritance class HomeAssistantApplication.*', category=DeprecationWarning)
        # HA 2025.1's acme/josepy dependencies import deprecated pyOpenSSL
        # certificate types. Keep this exception scoped to those dependencies.
        warnings.filterwarnings(
            'ignore', message=r'.*support in pyOpenSSL is deprecated\.',
            category=DeprecationWarning, module=r'(acme|josepy)(\.|$)',
        )
        from homeassistant.components.vacuum import VacuumActivity, VacuumEntityFeature
    from homeassistant.const import STATE_UNKNOWN
    from sencor_protocol_tests.vacuum import Vacuum
    from sencor_protocol_tests.number import SencorVacuumVolume


@unittest.skipUnless(HAS_HA, 'Install homeassistant to run entity compatibility checks')
class EntityTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.device = SencorVacuum('127.0.0.1', 'test-auth', 'robot')
        self.vacuum = Vacuum(self.device)

    async def test_state_and_feature_contract(self):
        self.assertTrue(self.vacuum.supported_features & VacuumEntityFeature.START)
        self.assertTrue(self.vacuum.supported_features & VacuumEntityFeature.STATE)
        cases = {
            WorkState.Cleaning: VacuumActivity.CLEANING,
            WorkState.Idle: VacuumActivity.IDLE,
            WorkState.Returning: VacuumActivity.RETURNING,
            WorkState.Charging: VacuumActivity.DOCKED,
            WorkState.Docked: VacuumActivity.DOCKED,
            WorkState.Error: VacuumActivity.ERROR,
            WorkState.Problem: VacuumActivity.ERROR,
            WorkState.Unknown: None,
        }
        for state, activity in cases.items():
            self.device.work_state = state
            self.assertEqual(self.vacuum.activity, activity)
            if activity is None:
                # HA 2025.1 maps a missing activity to STATE_UNKNOWN; newer
                # versions leave it as None for the entity state machinery.
                self.assertIn(self.vacuum.state, (None, STATE_UNKNOWN))
            else:
                self.assertEqual(self.vacuum.state, activity)
        self.device.work_state = WorkState.Idle
        self.device.had_work = True
        self.assertEqual(self.vacuum.state, VacuumActivity.PAUSED)
        self.device.battery_level = 80
        self.assertEqual(self.vacuum.extra_state_attributes['battery_level'], 80)

    async def test_actions_dispatch_to_device(self):
        for action, method in [('async_start', 'start'), ('async_stop', 'stop'),
                               ('async_pause', 'pause'), ('async_return_to_base', 'charge'),
                               ('async_locate', 'find')]:
            command = AsyncMock()
            setattr(self.device, method, command)
            await getattr(self.vacuum, action)()
            command.assert_awaited_once_with()

    async def test_constructors_do_not_create_unawaited_coroutines(self):
        self.device.update_state = AsyncMock()
        Vacuum(self.device)
        SencorVacuumVolume(self.device, 'Volume')
        self.device.update_state.assert_not_called()
