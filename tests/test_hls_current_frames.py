import struct

from alicia_d_sdk.hardware.servo_driver import ServoDriver


class _OpenSerialPort:
    is_open = True

    def write(self, data):
        return len(data)

    def flush(self):
        return None

    def close(self):
        self.is_open = False


def test_build_hls_current_mode_frame():
    driver = ServoDriver(port="COM_TEST")

    frame = driver._build_hls_current_frame(servo_id=2, action="current_mode")

    assert frame == [
        0xAA, 0x07, 0x00, 0x01, 0x02,
        driver.serial_comm.calculate_checksum([0x07, 0x00, 0x01, 0x02]),
        0xFF,
    ]


def test_build_hls_write_current_frame_encodes_signed_current_little_endian():
    driver = ServoDriver(port="COM_TEST")

    frame = driver._build_hls_current_frame(servo_id=2, action="write_current", current=-80)

    assert frame == [
        0xAA, 0x07, 0x01, 0x03, 0x02, 0xB0, 0xFF,
        driver.serial_comm.calculate_checksum([0x07, 0x01, 0x03, 0x02, 0xB0, 0xFF]),
        0xFF,
    ]


def test_build_hls_position_mode_frame():
    driver = ServoDriver(port="COM_TEST")

    frame = driver._build_hls_current_frame(servo_id=2, action="position_mode")

    assert frame == [
        0xAA, 0x07, 0x02, 0x01, 0x02,
        driver.serial_comm.calculate_checksum([0x07, 0x02, 0x01, 0x02]),
        0xFF,
    ]


def test_build_hls_position_calibration_frame():
    driver = ServoDriver(port="COM_TEST")

    frame = driver._build_hls_current_frame(servo_id=6, action="calibrate_position")

    assert frame == [
        0xAA, 0x07, 0x03, 0x01, 0x06,
        driver.serial_comm.calculate_checksum([0x07, 0x03, 0x01, 0x06]),
        0xFF,
    ]


def test_debug_send_data_uses_existing_hex_printer():
    driver = ServoDriver(port="COM_TEST", debug_mode=True)
    driver.serial_comm.serial_port = _OpenSerialPort()

    assert driver.serial_comm.send_data([0xAA, 0x07, 0x00, 0x01, 0x02, 0xC8, 0xFF])


def test_build_gravity_compensation_frames():
    driver = ServoDriver(port="COM_TEST")

    assert driver._build_gravity_compensation_frame(
        driver.GRAVITY_COMP_ACTION_ENABLE
    ) == [
        0xAA, 0x06, 0x21, 0x01, 0x01,
        driver.serial_comm.calculate_checksum([0x06, 0x21, 0x01, 0x01]),
        0xFF,
    ]
    assert driver._build_gravity_compensation_frame(
        driver.GRAVITY_COMP_ACTION_GET_STATUS
    ) == [
        0xAA, 0x06, 0x21, 0x01, 0x02,
        driver.serial_comm.calculate_checksum([0x06, 0x21, 0x01, 0x02]),
        0xFF,
    ]


def test_parse_gravity_compensation_preview_response():
    driver = ServoDriver(port="COM_TEST")
    payload = bytes([driver.GRAVITY_COMP_ACTION_PREVIEW_MODEL, 0, 0])
    payload += (-43).to_bytes(2, "little", signed=True) + (-364).to_bytes(2, "little", signed=True) + (-26).to_bytes(2, "little", signed=True)
    payload += struct.pack("<6Hffffff", 205, 3127, 2561, 2025, 1025, 4099, -0.0107, 0.0, -0.0368, 0.0833, 0.8092, 0.2554)
    frame = [0xAA, 0x06, 0x21, len(payload), *payload, 0x00, 0xFF]
    frame[-2] = driver.serial_comm.calculate_checksum(frame[1:-2])

    result = driver._parse_gravity_compensation_response(frame)

    assert result["state_name"] == "OFF"
    assert result["current_id2"] == -43
    assert result["positions"] == [205, 3127, 2561, 2025, 1025, 4099]
    assert abs(result["tau3"] - 0.8092) < 1e-5


def test_parse_gravity_compensation_status_response():
    driver = ServoDriver(port="COM_TEST")
    payload = bytes([driver.GRAVITY_COMP_ACTION_GET_STATUS, 2, 0])
    payload += (12).to_bytes(2, "little", signed=True)
    payload += (-345).to_bytes(2, "little", signed=True)
    payload += (-25).to_bytes(2, "little", signed=True)
    frame = [0xAA, 0x06, 0x21, len(payload), *payload, 0x00, 0xFF]
    frame[-2] = driver.serial_comm.calculate_checksum(frame[1:-2])

    result = driver._parse_gravity_compensation_response(frame)

    assert result["action"] == driver.GRAVITY_COMP_ACTION_GET_STATUS
    assert result["state_name"] == "ACTIVE"
    assert result["current_id2"] == 12
    assert result["current_id3"] == -345
    assert result["current_id5"] == -25
