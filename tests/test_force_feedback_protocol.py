import threading
import unittest
import zlib

from alicia_d_sdk.hardware.data_parser import DataParser
from alicia_d_sdk.hardware.servo_driver import ServoDriver


class FakeForceFeedbackSerial:
    def __init__(self, parser):
        self.parser = parser
        self.requested = False
        self.sent = []

    @staticmethod
    def calculate_checksum(data):
        return zlib.crc32(bytes(data)) & 0xFF

    def send_data(self, frame):
        self.sent.append(list(frame))
        if frame[1:3] != [0x06, 0x20]:
            return True
        action = frame[4]
        if action in (0, 1):
            self.requested = bool(action)
        data = [
            0x01,
            int(self.requested),
            int(self.requested),
            0x00,
            0x01,
            0x00,
        ]
        self.parser.parse_frame(
            [0xAA, 0x06, 0x20, len(data), *data, 0x00, 0xFF]
        )
        return True

    def disconnect(self):
        return None


class ForceFeedbackProtocolTest(unittest.TestCase):
    def setUp(self):
        self.parser = DataParser(threading.Lock())
        self.driver = object.__new__(ServoDriver)
        self.driver.data_parser = self.parser
        self.driver.serial_comm = FakeForceFeedbackSerial(self.parser)
        self.driver._update_thread = None
        self.driver._thread_running = False
        self.driver._stop_thread = threading.Event()

    def test_parse_inhibit_reasons(self):
        data = [0x01, 0x01, 0x00, 0x05, 0x00, 0x00]
        parsed = self.parser.parse_frame(
            [0xAA, 0x06, 0x20, len(data), *data, 0x00, 0xFF]
        )
        self.assertTrue(parsed["requested"])
        self.assertFalse(parsed["effective"])
        self.assertEqual(parsed["inhibit_mask"], 0x05)
        self.assertEqual(parsed["inhibit_reasons"],
                         ["未进入遥操", "D-M链路超时"])

    def test_query_is_read_only(self):
        self.driver.serial_comm.requested = True
        state = self.driver.get_force_feedback_state(timeout=0.1)
        self.assertTrue(state["requested"])
        self.assertEqual(self.driver.serial_comm.sent[-1][4], 0xFE)
        self.assertTrue(self.driver.serial_comm.requested)

    def test_parse_v2_control_path_diagnostics(self):
        data = [0x02, 0x00, 0x00, 0x05, 0x00, 0x00,
                0x00, 0x02, 0x01, 0x00]
        parsed = self.parser.parse_frame(
            [0xAA, 0x06, 0x20, len(data), *data, 0x00, 0xFF]
        )
        self.assertFalse(parsed["torque_requested"])
        self.assertFalse(parsed["torque_enabled"])
        self.assertEqual(parsed["transition"], 2)
        self.assertEqual(parsed["grip_enabled_raw"], 1)
        self.assertEqual(parsed["requested_mode"], "position")

    def test_set_is_confirmed_and_idempotent(self):
        self.assertTrue(
            self.driver.set_force_feedback_enabled(True, timeout=0.2)
        )
        self.assertTrue(
            self.driver.set_force_feedback_enabled(True, timeout=0.2)
        )
        self.assertTrue(
            self.driver.set_force_feedback_enabled(False, timeout=0.2)
        )
        self.assertFalse(self.driver.serial_comm.requested)


if __name__ == "__main__":
    unittest.main()
