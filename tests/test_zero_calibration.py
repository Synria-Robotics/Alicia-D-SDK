import unittest
from unittest.mock import patch

from alicia_d_sdk.api.synria_robot_api import SynriaRobotAPI
from alicia_d_sdk.hardware.servo_driver import ServoDriver


class _FakeServoDriver:
    def __init__(self):
        self.calls = []

    def acquire_info(self, info_type, wait=False, timeout=0.0):
        self.calls.append((info_type, wait))
        return True

    @staticmethod
    def stop_update_thread():
        return None

    @staticmethod
    def disconnect():
        return None


class _FakeDataParser:
    @staticmethod
    def get_info(info_type):
        if info_type == "joint":
            return [0.0] * 6
        return None


class ZeroCalibrationTests(unittest.TestCase):
    def test_freeze_full_arm_protocol_frame(self):
        self.assertEqual(
            ServoDriver.INFO_COMMAND_MAP["zero_cali"],
            [0xAA, 0x03, 0x00, 0x01, 0xFE, 0xA8, 0xFF],
        )

    def make_robot(self, initial_mode="current"):
        robot = object.__new__(SynriaRobotAPI)
        robot.servo_driver = _FakeServoDriver()
        robot.data_parser = _FakeDataParser()
        robot.mode_calls = []
        robot.torque_calls = []
        robot.get_control_mode = lambda timeout=0.0: initial_mode
        robot.set_control_mode = lambda mode, timeout=0.0: (
            robot.mode_calls.append(mode) or True
        )
        robot.torque_control = lambda command, timeout=0.0: (
            robot.torque_calls.append(command) or True
        )
        return robot

    @patch("builtins.input", return_value="")
    @patch("alicia_d_sdk.api.synria_robot_api.time.sleep", return_value=None)
    def test_switches_to_position_and_leaves_torque_off(self, _sleep, _input):
        robot = self.make_robot(initial_mode="current")

        self.assertTrue(robot.zero_calibration())

        self.assertEqual(robot.mode_calls, ["position"])
        self.assertEqual(robot.torque_calls, ["off"])
        self.assertIn(("zero_cali", False), robot.servo_driver.calls)
        self.assertNotIn(("torque_on", True), robot.servo_driver.calls)

    @patch("builtins.input", return_value="")
    @patch("alicia_d_sdk.api.synria_robot_api.time.sleep", return_value=None)
    def test_uses_legacy_position_mode_when_mode_cannot_be_read(
            self, _sleep, _input):
        robot = self.make_robot(initial_mode=None)

        self.assertTrue(robot.zero_calibration())

        self.assertEqual(robot.mode_calls, [])
        self.assertEqual(robot.torque_calls, ["off"])
        self.assertIn(("zero_cali", False), robot.servo_driver.calls)


if __name__ == "__main__":
    unittest.main()
