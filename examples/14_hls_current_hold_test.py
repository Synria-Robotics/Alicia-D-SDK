# Copyright (c) 2025 Synria Robotics Co., Ltd.
# Licensed under the MIT License.

"""
HLS舵机电流模式最小保持测试。

这个脚本只做一件事：
1. 连接串口
2. 把指定舵机切到电流模式
3. 写入一个固定电流并保持几秒
4. 最后写0电流并切回位置模式

它不读取机械臂状态，也不写CSV，用来排查“SDK命令到底有没有让舵机托住”。
"""

import argparse
import time

from alicia_d_sdk.hardware.servo_driver import ServoDriver


def print_frame(driver: ServoDriver, title: str, frame):
    """把用户协议帧打印成十六进制，方便和STM32固件里的解析格式对照。"""
    text = " ".join(f"{byte:02X}" for byte in frame)
    print(f"{title}: {text}")


def main(args):
    driver = ServoDriver(port=args.port, debug_mode=args.debug)
    active_current = 0

    if args.servo_id not in (2, 3):
        print("提示：当前重力补偿标定建议先测ID2或ID3。")

    print_frame(
        driver,
        "进入电流模式帧",
        driver._build_hls_current_frame(args.servo_id, "current_mode"),
    )
    print_frame(
        driver,
        "写目标电流帧",
        driver._build_hls_current_frame(args.servo_id, "write_current", args.current),
    )
    print_frame(
        driver,
        "退出位置模式帧",
        driver._build_hls_current_frame(args.servo_id, "position_mode"),
    )

    try:
        if not driver.serial_comm.connect():
            print("串口连接失败，请检查端口号和占用情况。")
            return

        input("请先用手托住机械臂，确认安全后按回车开始测试...")

        print(f"ID{args.servo_id} 切换到电流模式")
        driver.hls_set_current_mode(args.servo_id)
        time.sleep(args.mode_delay)

        print(f"ID{args.servo_id} 写入电流 {args.current}，保持 {args.hold_time} 秒")
        driver.hls_write_current(args.servo_id, args.current)
        active_current = args.current
        time.sleep(args.hold_time)

    except KeyboardInterrupt:
        print("\n收到中断，开始安全退出。")
    finally:
        # 安全退出顺序：先写0电流，再切回位置模式。
        if driver.serial_comm.is_connected():
            if active_current != 0:
                driver.hls_write_current(args.servo_id, 0)
                time.sleep(0.05)
            driver.hls_set_position_mode(args.servo_id)
            time.sleep(0.05)
        driver.disconnect()
        print("测试结束，已尝试归零电流并切回位置模式。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HLS current mode minimal hold test")
    parser.add_argument("--port", type=str, default="", help="串口号，例如 COM11")
    parser.add_argument("--servo-id", type=int, default=2, help="舵机ID，建议先用2或3")
    parser.add_argument("--current", type=int, default=-80, help="目标电流，例如 -80")
    parser.add_argument("--hold-time", type=float, default=10.0, help="保持时间，单位秒")
    parser.add_argument("--mode-delay", type=float, default=0.2, help="切模式后等待时间，单位秒")
    parser.add_argument("--debug", action="store_true", help="打印SDK串口发送日志")
    main(parser.parse_args())
