"""只读查看 Alicia-D 各关节的协议位置值（0~4095）。"""

import argparse
import math
import time
from typing import Optional

import alicia_d_sdk


def angle_to_protocol_position(angle_rad: float) -> int:
    """将 0x06 回包中的关节弧度还原为协议位置值。"""
    position = round((angle_rad + math.pi) / (2.0 * math.pi) * 4096.0)
    return max(0, min(4095, position))


def print_positions(robot, servo_id: Optional[int]) -> None:
    """读取一次关节状态并打印目标关节或全部六个关节。"""
    state = robot.get_robot_state("joint_gripper", timeout=1.0)
    if state is None or state.angles is None:
        raise RuntimeError("没有读到关节位置，请确认机械臂上电且 read state 正常。")

    ids = range(1, 7) if servo_id is None else (servo_id,)
    for current_id in ids:
        angle_rad = state.angles[current_id - 1]
        position = angle_to_protocol_position(angle_rad)
        print(
            f"ID{current_id}: position={position:4d}  "
            f"angle={angle_rad:+.4f} rad  "
            f"({math.degrees(angle_rad):+.2f} deg)"
        )


def main(args: argparse.Namespace) -> None:
    robot = alicia_d_sdk.create_robot(port=args.port)
    try:
        if args.continuous:
            while True:
                print_positions(robot, args.servo_id)
                time.sleep(1.0 / args.fps)
        else:
            print_positions(robot, args.servo_id)
    except KeyboardInterrupt:
        print("\n读取结束。")
    finally:
        robot.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="只读打印 Alicia-D 关节协议位置；不写舵机、不切换控制模式。"
    )
    parser.add_argument("--port", default="COM11", help="串口，例如 COM11")
    parser.add_argument(
        "--servo-id",
        type=int,
        choices=range(1, 7),
        default=1,
        help="要查看的关节 ID；默认 ID1。使用 --all 查看全部。",
    )
    parser.add_argument("--all", action="store_true", help="查看 ID1~ID6")
    parser.add_argument("--continuous", action="store_true", help="持续读取，按 Ctrl+C 停止")
    parser.add_argument("--fps", type=float, default=5.0, help="持续读取频率，默认 5 Hz")
    args = parser.parse_args()
    if args.fps <= 0:
        parser.error("--fps 必须大于 0")
    if args.all:
        args.servo_id = None
    main(args)
