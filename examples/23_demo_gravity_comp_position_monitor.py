"""纯重力补偿位置监视工具。

只使用板端 0x06/0x21 重力补偿协议：不启用 0x22 电流位置控制，
不下发关节位置目标。用于记录哪些姿态下纯 G(q) 无法托住机械臂。
"""

import argparse
import time

from alicia_d_sdk.hardware.servo_driver import ServoDriver


def print_sample(elapsed: float, preview: dict, status: dict) -> None:
    """把位置、模型预测和实际写入电流放在同一行，便于人工记录。"""
    positions = preview["positions"]
    print(
        f"t={elapsed:6.1f}s "
        f"pos=[{positions[0]:4d}, {positions[1]:4d}, {positions[2]:4d}, "
        f"{positions[3]:4d}, {positions[4]:4d}, {positions[5]:4d}] "
        f"tau2={preview['tau2']:+.4f} tau3={preview['tau3']:+.4f} "
        f"tau5={preview['tau5']:+.4f} "
        f"G_pred=[{preview['current_id2']:+4d}, {preview['current_id3']:+4d}, "
        f"{preview['current_id5']:+4d}] "
        f"I_written=[{status['current_id2']:+4d}, {status['current_id3']:+4d}, "
        f"{status['current_id5']:+4d}] "
        f"state={status['state_name']} fault={status['fault_name']}"
    )


def main(args: argparse.Namespace) -> None:
    driver = ServoDriver(port=args.port, debug_mode=args.debug)
    enabled = False

    try:
        if not driver.connect():
            raise RuntimeError("串口连接失败")

        preview = driver.preview_gravity_compensation(timeout=args.timeout)
        if preview is None:
            raise RuntimeError("未收到板端模型预览回包")

        print("本工具只开启 0x21 纯重力补偿，不会启用 0x22 或写入位置目标。")
        print(
            "初始预览: "
            f"pos={preview['positions']} "
            f"G_pred=[{preview['current_id2']:+d}, {preview['current_id3']:+d}, "
            f"{preview['current_id5']:+d}]"
        )

        if not args.yes:
            answer = input("请先托住机械臂，确认安全后输入 YES 开始，其他输入取消: ").strip()
            if answer != "YES":
                print("已取消。")
                return

        status = driver.set_gravity_compensation(True, timeout=args.timeout)
        if status is None:
            raise RuntimeError("未收到重力补偿开启回包")
        enabled = True
        print("已开启纯重力补偿。按 Ctrl+C 结束并自动关闭。")

        start_time = time.monotonic()
        while args.hold_time <= 0.0 or time.monotonic() - start_time < args.hold_time:
            preview = driver.preview_gravity_compensation(timeout=args.timeout)
            status = driver.get_gravity_compensation_status(timeout=args.timeout)
            if preview is None or status is None:
                print("本次读取超时，继续下一周期。")
            else:
                print_sample(time.monotonic() - start_time, preview, status)
                if status["fault_name"] != "NONE":
                    raise RuntimeError(f"板端进入故障状态: {status['fault_name']}")
            time.sleep(args.period)
    except KeyboardInterrupt:
        print("\n收到 Ctrl+C，正在关闭纯重力补偿。")
    finally:
        if enabled and driver.serial_comm.is_connected():
            try:
                status = driver.set_gravity_compensation(False, timeout=args.timeout)
                if status is not None:
                    print(
                        "关闭确认: "
                        f"state={status['state_name']} fault={status['fault_name']} "
                        f"I=[{status['current_id2']:+d}, {status['current_id3']:+d}, "
                        f"{status['current_id5']:+d}]"
                    )
            finally:
                driver.disconnect()
        else:
            driver.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="纯重力补偿实时位置与电流监视")
    parser.add_argument("--port", default="COM11")
    parser.add_argument("--hold-time", type=float, default=120.0,
                        help="测试秒数；设为 0 表示持续运行至 Ctrl+C")
    parser.add_argument("--period", type=float, default=0.5,
                        help="打印周期（秒），建议不低于 0.2")
    parser.add_argument("--timeout", type=float, default=1.0)
    parser.add_argument("--yes", action="store_true", help="跳过安全确认")
    parser.add_argument("--debug", action="store_true")
    main(parser.parse_args())
