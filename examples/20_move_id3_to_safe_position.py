"""将 ID3 切回普通位置模式，并低速移动到便于测试的中间位置。"""

import argparse
import time

from alicia_d_sdk.hardware.servo_driver import ServoDriver


def main(args: argparse.Namespace) -> None:
    driver = ServoDriver(port=args.port, debug_mode=args.debug)

    try:
        if not driver.connect():
            raise RuntimeError("串口连接失败")

        print(
            f"即将关闭电流控制，并以普通位置模式将 ID3 移动到 {args.target}。\n"
            f"速度为 {args.speed}（HLS 原始速度值）。请先托住机械臂。"
        )
        if input("确认安全后输入 YES 继续，其他输入取消: ").strip().upper() != "YES":
            print("已取消，未写入位置目标。")
            return

        # 先退出 0x22，再退出 0x21，保证只有普通位置命令写入 ID3。
        position_status = driver.disable_current_position_control(timeout=args.timeout)
        if position_status is None:
            raise RuntimeError("未收到 0x22 关闭确认，停止发送普通位置目标")

        gravity_status = driver.set_gravity_compensation(False, timeout=args.timeout)
        if gravity_status is None:
            raise RuntimeError("未收到 0x21 关闭确认，停止发送普通位置目标")

        # 即使 0x22 本来就是 OFF，也显式让 ID3 回到位置模式并重新使能扭矩。
        if not driver.hls_set_position_mode(3):
            raise RuntimeError("ID3 切回 HLS 位置模式失败")
        time.sleep(0.2)
        if not driver.set_single_joint_position(3, args.target, args.speed):
            raise RuntimeError("ID3 普通位置目标发送失败")

        print(
            f"已发送：ID3 -> {args.target}，speed={args.speed}。\n"
            f"保持托住机械臂，等待约 {args.wait:.1f} 秒观察；Ctrl+C 不会撤销该位置目标。"
        )
        time.sleep(args.wait)
    finally:
        driver.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="安全地将 ID3 移至普通位置模式的中间测试区")
    parser.add_argument("--port", default="COM11")
    parser.add_argument("--target", type=int, default=2500, help="ID3 普通位置目标，范围 0~4095")
    parser.add_argument("--speed", type=int, default=50, help="HLS 原始速度值，建议先用 50")
    parser.add_argument("--wait", type=float, default=8.0, help="发送后保持串口连接的观察时间（秒）")
    parser.add_argument("--timeout", type=float, default=1.0)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    if args.target < 0 or args.target > 4095:
        parser.error("--target 必须在 0~4095")
    if args.speed < 0 or args.speed > 65535:
        parser.error("--speed 必须在 0~65535")
    if args.wait < 0:
        parser.error("--wait 不能为负数")

    main(args)
