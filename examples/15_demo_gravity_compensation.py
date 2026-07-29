"""通过 SDK 手动开关 STM32 板端重力补偿。"""

import argparse
import time

from alicia_d_sdk.hardware.servo_driver import ServoDriver


def print_status(prefix: str, status: dict) -> None:
    print(
        f"{prefix}: state={status['state_name']} fault={status['fault_name']} "
        f"I2={status['current_id2']} I3={status['current_id3']} I5={status['current_id5']}"
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
        print(
            f"模型预览: pos={preview['positions']} "
            f"tau2={preview['tau2']:.4f} tau3={preview['tau3']:.4f} tau5={preview['tau5']:.4f} "
            f"I2={preview['current_id2']} I3={preview['current_id3']} I5={preview['current_id5']}"
        )

        if not args.enable:
            print("仅完成模型预览；加入 --enable 才会开启实际补偿。")
            return

        answer = input("请先托住机械臂；确认安全后输入 y 开启补偿: ").strip().lower()
        if answer != "y":
            print("已取消。")
            return

        status = driver.set_gravity_compensation(True, timeout=args.timeout)
        if status is None:
            raise RuntimeError("开启命令没有收到 ACK")
        enabled = True
        print_status("开启确认", status)

        deadline = time.monotonic() + args.hold_time
        while time.monotonic() < deadline:
            time.sleep(args.status_period)
            status = driver.get_gravity_compensation_status(timeout=args.timeout)
            if status is None:
                print("状态查询超时")
                continue
            print_status("运行中", status)
    except KeyboardInterrupt:
        print("\n收到 Ctrl+C，开始关闭补偿。")
    finally:
        if enabled and driver.serial_comm.is_connected():
            try:
                status = driver.set_gravity_compensation(False, timeout=args.timeout)
                if status is not None:
                    print_status("关闭确认", status)
                time.sleep(0.15)
                status = driver.get_gravity_compensation_status(timeout=args.timeout)
                if status is not None:
                    print_status("最终状态", status)
            except Exception as exc:
                print(f"关闭补偿时发生异常: {exc}")
        driver.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SDK 板端重力补偿测试")
    parser.add_argument("--port", default="COM11")
    parser.add_argument("--hold-time", type=float, default=30.0)
    parser.add_argument("--status-period", type=float, default=0.25)
    parser.add_argument("--timeout", type=float, default=1.0)
    parser.add_argument("--enable", action="store_true", help="实际开启补偿；默认仅预览")
    parser.add_argument("--debug", action="store_true")
    main(parser.parse_args())
