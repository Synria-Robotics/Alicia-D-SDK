"""
HLS 示教臂关节零点校准工具。

原理：通过 STM32 转发 Feetech HLS 的 0x0B 指令，将指定舆机的当前位置重标定为内部中位 2048。

安全要求：
1. 先关闭重力补偿，并用工装或手动托住机械臂。
2. 将六个关节摆到与 URDF q=[0, 0, 0, 0, 0, 0] 对应的实物姿态。
3. 该操作会修改舆机内部零点，不可当作普通位置控制命令使用。
"""

import argparse
import math
import time

from alicia_d_sdk.hardware.servo_driver import ServoDriver


def angle_to_position(angle_rad: float) -> int:
    """将 STM32 0x06 读状态角度还原为协议 position。"""
    position = round((angle_rad + math.pi) / (2.0 * math.pi) * 4096.0)
    return max(0, min(4095, position))


def read_positions(driver: ServoDriver, timeout: float) -> list[int]:
    """读取一次六关节位置，用于校准前后对照。"""
    if not driver.acquire_info("joint_gripper", wait=True, timeout=timeout):
        raise RuntimeError("没有读到六关节位置，请确认机械臂已上电且 read state 正常。")

    state = driver.data_parser.get_info("joint_gripper")
    if state is None or state.angles is None:
        raise RuntimeError("关节状态回包无效。")
    return [angle_to_position(angle) for angle in state.angles]


def print_positions(title: str, positions: list[int]) -> None:
    """以定长格式显示六个关节的当前 position。"""
    print(f"{title}: " + "  ".join(f"ID{index}={value:4d}" for index, value in enumerate(positions, start=1)))


def confirm_or_abort(message: str, assume_yes: bool) -> None:
    """交互式安全确认，非交互调用必须显式使用 --yes。"""
    if assume_yes:
        return
    answer = input(f"{message} 输入 YES 继续，其他任意输入取消: ").strip()
    if answer != "YES":
        raise RuntimeError("已取消校准，未向舆机写入任何零点。")


def main(args: argparse.Namespace) -> None:
    servo_ids = list(range(1, 7)) if args.all else args.servo_ids
    if not servo_ids:
        raise ValueError("请指定 --all 或 --servo-ids，不会默认校准任何关节。")

    driver = ServoDriver(port=args.port, debug_mode=args.debug)
    try:
        if not driver.connect():
            raise RuntimeError("串口连接失败。")

        # 校准前先读取一次，可以确认机械臂未在若干关节间明显偏离预期姿态。
        before = read_positions(driver, args.read_timeout)
        print_positions("校准前", before)
        print("目标关节: " + ", ".join(f"ID{servo_id}" for servo_id in servo_ids))
        print("请确认：重力补偿已关闭，机械臂已固定在 URDF q=0 姿态，且所有关节都已托住。")
        confirm_or_abort("现在将把当前位置写入上述舆机的内部零点。", args.yes)

        for servo_id in servo_ids:
            if not driver.hls_calibrate_current_position(servo_id):
                raise RuntimeError(f"ID{servo_id} 校准指令发送失败。")
            print(f"ID{servo_id}: 已发送 HLS 0x0B 当前位置校准指令")
            time.sleep(args.interval)

        # 给舆机 EEPROM 写入和 STM32 轮询状态留出时间，再用同一个读状态通路验证。
        time.sleep(args.settle_time)
        after = read_positions(driver, args.read_timeout)
        print_positions("校准后", after)

        for servo_id in servo_ids:
            position = after[servo_id - 1]
            error = position - 2048
            print(f"ID{servo_id}: position={position}, 与 2048 的差值={error:+d} tick")

        print("校准指令已完成。在恢复扭矩或运行任何位置控制前，请先确认六个读回值都在 2048 附近。")
    finally:
        driver.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HLS 示教臂关节当前位置零点校准")
    parser.add_argument("--port", default="COM11", help="串口，例如 COM11")
    parser.add_argument("--all", action="store_true", help="校准 ID1~ID6（建议将六关节固定后一次执行）")
    parser.add_argument("--servo-ids", type=int, nargs="+", choices=range(1, 7), help="仅校准指定的关节 ID")
    parser.add_argument("--interval", type=float, default=0.15, help="相邻两个舆机校准命令的间隔，单位秒")
    parser.add_argument("--settle-time", type=float, default=0.8, help="发送完后等待读回的时间，单位秒")
    parser.add_argument("--read-timeout", type=float, default=1.0, help="读状态超时，单位秒")
    parser.add_argument("--yes", action="store_true", help="跳过交互式安全确认（只用于已确认姿态正确的自动化流程）")
    parser.add_argument("--debug", action="store_true", help="打印串口发送帧")
    parsed_args = parser.parse_args()
    if parsed_args.all and parsed_args.servo_ids:
        parser.error("--all 与 --servo-ids 不能同时使用")
    if parsed_args.interval < 0 or parsed_args.settle_time < 0:
        parser.error("--interval 和 --settle-time 不能为负数")
    main(parsed_args)
