import struct

from alicia_d_sdk.hardware.servo_driver import ServoDriver


def test_build_current_position_enable_frame():
    driver = ServoDriver(port="COM_TEST")

    frame = driver._build_current_position_frame(driver.CURRENT_POSITION_ACTION_ENABLE)

    assert frame == [
        0xAA, 0x06, 0x22, 0x01, 0x01,
        driver.serial_comm.calculate_checksum([0x06, 0x22, 0x01, 0x01]),
        0xFF,
    ]


def test_build_current_position_targets_frame():
    driver = ServoDriver(port="COM_TEST")
    targets = [2048, 2050, 2060, 2070, 2080, 2090]

    frame = driver._build_current_position_frame(
        driver.CURRENT_POSITION_ACTION_SET_TARGETS,
        targets,
    )

    assert frame[0:4] == [0xAA, 0x06, 0x22, 0x0D]
    assert frame[4] == driver.CURRENT_POSITION_ACTION_SET_TARGETS
    assert list(struct.unpack_from("<6H", bytes(frame), 5)) == targets
    assert frame[-1] == 0xFF


def test_build_current_position_id3_prepose_preview_frame():
    driver = ServoDriver(port="COM_TEST")

    frame = driver._build_current_position_frame(
        driver.CURRENT_POSITION_ACTION_PREVIEW_ID3_PREPOSE,
    )

    assert frame == [
        0xAA, 0x06, 0x22, 0x01,
        driver.CURRENT_POSITION_ACTION_PREVIEW_ID3_PREPOSE,
        driver.serial_comm.calculate_checksum([
            0x06, 0x22, 0x01,
            driver.CURRENT_POSITION_ACTION_PREVIEW_ID3_PREPOSE,
        ]),
        0xFF,
    ]


def test_parse_current_position_response():
    driver = ServoDriver(port="COM_TEST")
    targets = [2048, 2049, 2050, 2051, 2052, 2053]
    payload = (
        bytes([driver.CURRENT_POSITION_ACTION_GET_STATUS, 2, 0])
        + struct.pack("<6H", *targets)
        + struct.pack("<Hhh", 2050, -365, 2)
        + struct.pack("<Hhh", 2060, -25, -3)
        + struct.pack("<hhh", -320, -85, 40)
        + struct.pack("<h", 640)
        + struct.pack("<HhhhhB", 2040, 8, -500, -32, 0, 8)
    )
    frame = [0xAA, 0x06, 0x22, len(payload), *payload, 0x00, 0xFF]
    frame[-2] = driver.serial_comm.calculate_checksum(frame[1:-2])

    result = driver._parse_current_position_response(frame)

    assert result["state_name"] == "ACTIVE"
    assert result["fault_name"] == "NONE"
    assert result["targets"] == targets
    assert result["current_id2"] == 640
    assert result["actual_id2"] == 2040
    assert result["error_id2_ticks"] == 8
    assert result["gravity_current_id2"] == -500
    assert result["pd_current_id2"] == -32
    assert result["bias_current_id2"] == 0
    assert result["stall_cycles_id2"] == 8
    assert result["actual_id3"] == 2050
    assert result["current_id3"] == -365
    assert result["error_id3_ticks"] == 2
    assert result["actual_id5"] == 2060
    assert result["current_id5"] == -25
    assert result["error_id5_ticks"] == -3
    assert result["gravity_current_id3"] == -320
    assert result["pd_current_id3"] == -85
    assert result["bias_current_id3"] == 40


def test_parse_current_position_id3_prepose_preview_response():
    driver = ServoDriver(port="COM_TEST")
    targets = [2048, 2049, 2050, 2051, 2052, 2053]
    payload = (
        bytes([driver.CURRENT_POSITION_ACTION_PREVIEW_ID3_PREPOSE, 1, 0])
        + struct.pack("<6H", *targets)
        + struct.pack("<Hhh", 2050, -365, 2)
        + struct.pack("<Hhh", 2060, -25, -3)
        + struct.pack("<hhh", -320, -85, 40)
        + struct.pack("<h", 640)
        + struct.pack("<HhhhhB", 2040, 8, -500, -32, 0, 8)
        + struct.pack("<Hhh", 2200, -280, 150)
    )
    frame = [0xAA, 0x06, 0x22, len(payload), *payload, 0x00, 0xFF]
    frame[-2] = driver.serial_comm.calculate_checksum(frame[1:-2])

    result = driver._parse_current_position_response(frame)

    assert result["id3_prepose_target"] == 2200
    assert result["predicted_id2_gravity_current"] == -280
    assert result["id3_prepose_offset_ticks"] == 150
