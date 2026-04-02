import importlib.util
import sys
import threading
import time
import types
import unittest
from pathlib import Path


ROOT = Path("/Users/young/works/Alicia-D-SDK")
SERVO_DRIVER_PATH = ROOT / "alicia_d_sdk" / "hardware" / "servo_driver.py"


def load_servo_driver_module():
    """Load servo_driver.py with lightweight stubs for external dependencies."""
    fake_numpy = types.ModuleType("numpy")
    fake_numpy.ndarray = type("ndarray", (), {})
    sys.modules["numpy"] = fake_numpy

    fake_pkg = types.ModuleType("alicia_d_sdk")
    fake_pkg.__path__ = []
    sys.modules["alicia_d_sdk"] = fake_pkg

    fake_hardware_pkg = types.ModuleType("alicia_d_sdk.hardware")
    fake_hardware_pkg.__path__ = []
    sys.modules["alicia_d_sdk.hardware"] = fake_hardware_pkg

    fake_utils_pkg = types.ModuleType("alicia_d_sdk.utils")
    fake_utils_pkg.__path__ = []
    sys.modules["alicia_d_sdk.utils"] = fake_utils_pkg

    fake_logger_module = types.ModuleType("alicia_d_sdk.utils.logger")

    class _FakeLogger:
        def info(self, *_args, **_kwargs):
            pass

        def warning(self, *_args, **_kwargs):
            pass

        def error(self, *_args, **_kwargs):
            pass

        def debug(self, *_args, **_kwargs):
            pass

    fake_logger_module.logger = _FakeLogger()
    fake_logger_module.hex_print = lambda *_args, **_kwargs: None
    sys.modules["alicia_d_sdk.utils.logger"] = fake_logger_module

    fake_serial_module = types.ModuleType("alicia_d_sdk.hardware.serial_comm")

    class FakeSerialComm:
        def __init__(self, port="", timeout=1.0, debug_mode=False, lock=None):
            self.port = port
            self.timeout = timeout
            self.debug_mode = debug_mode
            self._lock = lock
            self.connected = False
            self.read_calls = 0

        def connect(self):
            self.connected = True
            return True

        def disconnect(self):
            self.connected = False

        def is_connected(self):
            return self.connected

        def read_frame(self):
            self.read_calls += 1
            time.sleep(0.001)
            return None

    fake_serial_module.SerialComm = FakeSerialComm
    sys.modules["alicia_d_sdk.hardware.serial_comm"] = fake_serial_module

    fake_parser_module = types.ModuleType("alicia_d_sdk.hardware.data_parser")

    class FakeDataParser:
        def __init__(self, lock=None, debug_mode=False):
            self.lock = lock
            self.debug_mode = debug_mode
            self._info_event_map = {}

        def parse_frame(self, _frame):
            pass

        def get_joint_state(self):
            return None

    fake_parser_module.DataParser = FakeDataParser
    sys.modules["alicia_d_sdk.hardware.data_parser"] = fake_parser_module

    module_name = "alicia_d_sdk.hardware.servo_driver"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, SERVO_DRIVER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestConnectionThreadLifecycle(unittest.TestCase):
    def test_connect_starts_background_thread_and_disconnect_stops_it(self):
        servo_driver_module = load_servo_driver_module()
        driver = servo_driver_module.ServoDriver()

        self.assertFalse(driver.is_update_thread_running())

        connected = driver.connect()
        self.assertTrue(connected)

        deadline = time.time() + 0.5
        while not driver.is_update_thread_running() and time.time() < deadline:
            time.sleep(0.01)

        worker = driver._update_thread
        self.assertIsNotNone(worker)
        self.assertIsInstance(worker, threading.Thread)
        self.assertTrue(worker.is_alive())
        self.assertTrue(driver.serial_comm.is_connected())

        driver.disconnect()

        deadline = time.time() + 0.5
        while worker.is_alive() and time.time() < deadline:
            time.sleep(0.01)

        self.assertFalse(worker.is_alive())
        self.assertFalse(driver.is_update_thread_running())
        self.assertFalse(driver.serial_comm.is_connected())


if __name__ == "__main__":
    unittest.main()
