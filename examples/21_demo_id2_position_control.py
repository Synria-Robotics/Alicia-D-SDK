"""0x06/0x22 的 ID2 小行程电流位置控制测试。

ID3 与 ID5 保持锁存姿态，只让 ID2 在当前姿态附近做小范围主动运动。
第一阶段用于确认 ID2 的运动方向、重力项和 P-D 位置项是否正确。
"""

import argparse
import time

from alicia_d_sdk.hardware.servo_driver import ServoDriver


def print_status(prefix: str, status: dict) -> None:
    """打印 ID2 的位置、电流分项，并保留 ID3/ID5 的保持状态。"""
    print(
        f"{prefix}: state={status['state_name']} fault={status['fault_name']} "
        f"ID2 actual={status['actual_id2']} target={status['targets'][1]} "
        f"error={status['error_id2_ticks']:+d} I={status['current_id2']:+d} "
        f"G={status['gravity_current_id2']:+d} "
        f"PD={status['pd_current_id2']:+d} BIAS={status['bias_current_id2']:+d} "
        f"STALL={status['stall_cycles_id2']} | "
        f"ID3 actual={status['actual_id3']} target={status['targets'][2]} "
        f"error={status['error_id3_ticks']:+d} I={status['current_id3']:+d} "
        f"G={status['gravity_current_id3']:+d} "
        f"PD={status['pd_current_id3']:+d} BIAS={status['bias_current_id3']:+d} | "
        f"ID5_I={status['current_id5']:+d}"
    )


def main(args: argparse.Namespace) -> None:
    driver = ServoDriver(port=args.port, debug_mode=args.debug)
    enabled = False

    try:
        if not driver.connect():
            raise RuntimeError("串口连接失败")

        status = driver.enable_current_position_control(timeout=args.timeout)
        if status is None:
            raise RuntimeError("未收到 0x22 开启回包，请确认已刷入最新固件")
        enabled = True
        print_status("锁存当前姿态", status)

        start_id2 = status["targets"][1]
        # 协议位置为单圈 0~4095；跨越边界时按单圈环绕，板端会保留连续运动方向。
        target_id2 = (start_id2 + args.id2_offset) % 4096

        targets = list(status["targets"])
        targets[1] = target_id2
        status = driver.set_current_position_targets(targets, timeout=args.timeout)
        if status is None:
            raise RuntimeError("未收到 ID2 目标回包")
        if status["fault_name"] != "NONE":
            raise RuntimeError(f"板端拒绝 ID2 目标: {status['fault_name']}")

        print(
            f"ID2 相对当前锁存值偏移 {args.id2_offset:+d} tick: {target_id2}。"
            "请托住机械臂，确认 ID2 的初始运动方向；异常立即 Ctrl+C。"
        )
        print_status("目标已写入", status)

        deadline = time.monotonic() + args.hold_time
        while time.monotonic() < deadline:
            time.sleep(args.poll_period)
            status = driver.get_current_position_control_status(timeout=args.timeout)
            if status is None:
                raise RuntimeError("测试期间未收到 0x22 状态回包")
            print_status("ID2 控制中", status)
            if status["state_name"] == "FAULT":
                raise RuntimeError(f"板端进入故障状态: {status['fault_name']}")
            if abs(status["error_id2_ticks"]) > args.max_error:
                raise RuntimeError(
                    f"ID2 误差扩大至 {status['error_id2_ticks']:+d} tick，已停止测试"
                )
    finally:
        if enabled and driver.serial_comm.is_connected():
            status = driver.disable_current_position_control(timeout=args.timeout)
            if status is not None:
                print_status("关闭确认", status)
        driver.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ID2 小行程电流位置控制测试")
    parser.add_argument("--port", default="COM11")
    parser.add_argument("--timeout", type=float, default=1.0)
    parser.add_argument(
        "--id2-offset",
        type=int,
        required=True,
        help="相对锁存位置的 ID2 目标偏移，第一阶段只能在 -100 到 +100 tick",
    )
    parser.add_argument("--hold-time", type=float, default=15.0)
    parser.add_argument("--poll-period", type=float, default=0.2)
    parser.add_argument("--max-error", type=int, default=160)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    if args.id2_offset == 0 or abs(args.id2_offset) > 100:
        parser.error("--id2-offset 第一阶段必须在 -100 到 +100 tick，且不能为 0")
    if args.hold_time <= 0 or args.poll_period <= 0:
        parser.error("时间参数必须为正数")
    if args.max_error <= abs(args.id2_offset):
        parser.error("--max-error 必须大于 |--id2-offset|")

    main(args)
