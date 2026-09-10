import threading
import unittest
import zlib

from alicia_d_sdk.hardware.data_parser import DataParser
from alicia_d_sdk.hardware.servo_driver import ServoDriver
from alicia_d_sdk.api.synria_robot_api import SynriaRobotAPI


class FakeSerial:
    def __init__(self, parser):
        self.parser = parser
        self.applied_mode = 0
        self.sent = []

    @staticmethod
    def calculate_checksum(data):
        return zlib.crc32(bytes(data)) & 0xFF

    def send_data(self, frame):
        self.sent.append(list(frame))
        if frame[1:3] == [0x05, 0x01]:
            self.applied_mode = frame[4]
            self.parser.parse_frame(
                [0xAA, 0x05, 0x01, 0x03, 0x01, frame[4], 0x00, 0x00, 0xFF]
            )
        elif frame[1:3] == [0x05, 0x02]:
            self.parser.parse_frame(
                [0xAA, 0x05, 0x02, 0x04, 0x01, 0x00, 0x3F, 0x0A, 0x00, 0xFF]
            )
        elif frame[1:3] == [0x06, 0x24]:
            data = [0x01, self.applied_mode, 0x00, 0x3F] + [0x00] * 48
            self.parser.parse_frame(
                [0xAA, 0x06, 0x24, len(data), *data, 0x00, 0xFF]
            )
        return True

    def disconnect(self):
        return None


class FakeRobotModeApi:
    def __init__(self):
        self.calls = []

    def set_force_feedback_enabled(self, enabled, timeout=0.0):
        self.calls.append(("force_feedback", enabled))
        return True

    def set_control_mode(self, mode, timeout=0.0):
        self.calls.append(("control_mode", mode))
        return True

    def torque_control(self, command, timeout=0.0):
        self.calls.append(("torque", command))
        return True


class ControlModeProtocolTest(unittest.TestCase):
    def setUp(self):
        self.parser = DataParser(threading.Lock())

    def test_mode_acknowledgement(self):
        frame = [0xAA, 0x05, 0x01, 0x03, 0x01, 0x01, 0x00, 0x00, 0xFF]
        parsed = self.parser.parse_frame(frame)
        self.assertEqual(parsed["requested_mode"], "current")
        self.assertTrue(parsed["accepted"])
        self.assertTrue(self.parser._control_mode_ack_event.is_set())

    def test_current_mode_diagnostics(self):
        data = [0x01, 0x01, 0x04, 0x3F] + [0x00] * 48
        # J1 remote torque = -1.250 Nm, requested current = +0.500 A.
        data[4:8] = [0x1E, 0xFB, 0xF4, 0x01]
        frame = [0xAA, 0x06, 0x24, len(data), *data, 0x00, 0xFF]
        parsed = self.parser.parse_frame(frame)
        self.assertEqual(parsed["mode"], "current")
        self.assertEqual(self.parser.get_info("control_mode"), "current")
        self.assertAlmostEqual(parsed["axes"][0]["remote_torque_nm"], -1.25)
        self.assertAlmostEqual(parsed["axes"][0]["requested_current_a"], 0.5)
        diagnostics = self.parser.get_info("control_mode_diagnostics")
        self.assertEqual(diagnostics["mode"], "current")
        self.assertEqual(diagnostics["feedback_valid_mask"], 0x3F)

    def test_direct_current_acknowledgement(self):
        frame = [0xAA, 0x05, 0x02, 0x04, 0x01, 0x00, 0x3F, 0x0A, 0x00, 0xFF]
        parsed = self.parser.parse_frame(frame)
        self.assertEqual(parsed["type"], "direct_current_ack")
        self.assertTrue(parsed["accepted"])
        self.assertEqual(parsed["accepted_mask"], 0x3F)
        self.assertEqual(parsed["refresh_deadline_ms"], 100)
        self.assertTrue(self.parser._direct_current_ack_event.is_set())

    def test_unknown_mode_is_not_exposed(self):
        data = [0x01, 0x02, 0x00, 0x3F] + [0x00] * 48
        frame = [0xAA, 0x06, 0x24, len(data), *data, 0x00, 0xFF]
        self.assertIsNone(self.parser.parse_frame(frame))
        self.assertIsNone(self.parser.get_info("control_mode"))

    def test_tx_diagnostic_tracks_last_started_torque_write(self):
        data = [0x00] * 51
        data[0:4] = [0x01, 0x00, 0x00, 0x02]
        values = {
            4: 12,
            8: 11,
            12: 1,
            16: 0,
            20: 4,
            24: 1,
            28: 3,
            32: 2,
            36: 1234,
            40: 11,
            44: 8,
        }
        for offset, value in values.items():
            data[offset:offset + 4] = value.to_bytes(4, "little")
        data[48:50] = (100).to_bytes(2, "little")
        data[50] = 0x03
        frame = [0xAA, 0x06, 0x26, len(data), *data, 0x00, 0xFF]

        parsed = self.parser.parse_frame(frame)

        self.assertEqual(parsed["tx_started"], 11)
        self.assertEqual(parsed["last_torque_value"], 0)
        self.assertEqual(parsed["last_mode_value"], 2)
        self.assertEqual(parsed["torque_on"], 1)
        self.assertEqual(parsed["torque_off"], 3)
        self.assertEqual(parsed["last_batch_len"], 100)

    def test_driver_waits_for_applied_mode(self):
        driver = object.__new__(ServoDriver)
        driver.data_parser = self.parser
        driver.serial_comm = FakeSerial(self.parser)
        driver._update_thread = None
        driver._thread_running = False
        driver._stop_thread = threading.Event()

        self.assertTrue(driver.set_control_mode("current", timeout=0.2))
        self.assertEqual(driver.get_control_mode(timeout=0.2), "current")
        set_frame = driver.serial_comm.sent[0]
        self.assertEqual(set_frame[:5], [0xAA, 0x05, 0x01, 0x01, 0x01])
        self.assertEqual(set_frame[-2], 0xCE)

    def test_driver_sends_direct_current(self):
        driver = object.__new__(ServoDriver)
        driver.data_parser = self.parser
        driver.serial_comm = FakeSerial(self.parser)
        driver.joint_count = 6
        driver._update_thread = None
        driver._thread_running = False
        driver._stop_thread = threading.Event()

        acknowledgement = driver.set_direct_current(
            [0, 300, -300, 0, 0, 0],
            timeout=0.2,
        )

        self.assertIsNotNone(acknowledgement)
        self.assertTrue(acknowledgement["accepted"])
        set_frame = driver.serial_comm.sent[0]
        self.assertEqual(set_frame[:4], [0xAA, 0x05, 0x02, 0x0C])
        self.assertEqual(set_frame[4:10], [0x00, 0x00, 0x2C, 0x01, 0xD4, 0xFE])

    def test_driver_rejects_private_modes(self):
        driver = object.__new__(ServoDriver)
        driver.data_parser = self.parser
        driver.serial_comm = FakeSerial(self.parser)
        driver._update_thread = None
        driver._thread_running = False
        driver._stop_thread = threading.Event()
        with self.assertRaises(ValueError):
            driver.set_control_mode("sync")

    def test_exit_teleoperation_returns_to_manual_position_mode(self):
        robot = FakeRobotModeApi()
        result = SynriaRobotAPI.set_teleoperation_enabled(
            robot, False, timeout=0.2
        )
        self.assertTrue(result)
        self.assertEqual(robot.calls, [
            ("force_feedback", False),
            ("control_mode", "position"),
        ])

    def test_enter_teleoperation_does_not_enable_position_hold(self):
        robot = FakeRobotModeApi()
        result = SynriaRobotAPI.set_teleoperation_enabled(
            robot, True, timeout=0.2
        )
        self.assertTrue(result)
        self.assertEqual(robot.calls, [("control_mode", "current")])


if __name__ == "__main__":
    unittest.main()
