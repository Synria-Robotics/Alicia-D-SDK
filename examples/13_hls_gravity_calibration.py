# Copyright (c) 2025 Synria Robotics Co., Ltd.
# Licensed under the MIT License.

"""
HLS电流模式重力补偿标定工具。

用途：
- 给示教臂ID2/ID3单独切换到电流模式
- 手动输入测试电流
- 观察机械臂是否稳定、下坠或上抬
- 把 position-current-result 记录到CSV，后续生成固件查表数据
"""

import argparse
import csv
import math
import time
from pathlib import Path

import alicia_d_sdk
from alicia_d_sdk.utils.logger import logger


def rad_to_raw_position(angle_rad: float) -> int:
    """把SDK读取到的弧度角近似还原为舵机0~4095原始位置。"""
    raw = int((angle_rad + math.pi) / (2.0 * math.pi) * 4096.0)
    return max(0, min(4095, raw))


def read_servo_position(robot, servo_id: int):
    """读取指定示教臂舵机的当前角度和估算原始position。"""
    state = robot.get_robot_state("joint_gripper", timeout=1.0)
    if state is None or state.angles is None:
        return None, None

    joint_index = servo_id - 1
    if joint_index < 0 or joint_index >= len(state.angles):
        return None, None

    angle_rad = state.angles[joint_index]
    return angle_rad, rad_to_raw_position(angle_rad)


def ramp_current(driver, servo_id: int, start_current: int, target_current: int,
                 step: int, delay_s: float):
    """用小步进改变电流，避免电流突变导致机械臂猛动。"""
    if step <= 0:
        raise ValueError("step must be positive")

    current = start_current
    direction = 1 if target_current >= start_current else -1

    while current != target_current:
        next_current = current + direction * step
        if direction > 0:
            next_current = min(next_current, target_current)
        else:
            next_current = max(next_current, target_current)

        driver.hls_write_current(servo_id, next_current)
        current = next_current
        time.sleep(delay_s)


def append_sample(csv_path: Path, servo_id: int, position: int,
                  angle_deg: float, current: int, result: str):
    """追加一条标定记录，CSV可直接导入表格或后续脚本生成查表数组。"""
    file_exists = csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["servo_id", "position", "angle_deg", "current", "result"])
        writer.writerow([servo_id, position, f"{angle_deg:.2f}", current, result])


def main(args):
    if args.servo_id not in (2, 3):
        logger.warning("当前标定建议只用于ID2或ID3；如果确认要测其它ID，请先扩展脚本限制。")
        return

    csv_path = Path(args.output)
    robot = alicia_d_sdk.create_robot(port=args.port, debug_mode=args.debug)
    driver = robot.servo_driver
    active_current = 0
    in_current_mode = False

    try:
        logger.warning("请用手托住示教臂，确认周围没有障碍物。")
        input(f"按回车后将 ID{args.servo_id} 切换到电流模式...")

        driver.hls_set_current_mode(args.servo_id)
        in_current_mode = True
        time.sleep(0.1)

        while True:
            angle_rad, position = read_servo_position(robot, args.servo_id)
            if position is None:
                print("没有读到当前位置，请确认 read state 正常。")
            else:
                print(f"\nID{args.servo_id}: position={position}, angle={math.degrees(angle_rad):.2f} deg")

            text = input("输入测试电流，或 q 退出，例如 -80: ").strip().lower()
            if text in ("q", "quit", "exit"):
                break
            if not text:
                continue

            try:
                target_current = int(text)
            except ValueError:
                print("请输入整数电流值，例如 -80。")
                continue

            if abs(target_current) > args.max_abs_current:
                print(f"电流超过限制 +/-{args.max_abs_current}，本次忽略。")
                continue

            ramp_current(
                driver,
                args.servo_id,
                active_current,
                target_current,
                args.step,
                args.step_delay,
            )
            active_current = target_current
            time.sleep(args.hold_time)

            angle_rad, position = read_servo_position(robot, args.servo_id)
            if position is None:
                print("保持后仍未读到当前位置，本次不记录。")
                continue

            angle_deg = math.degrees(angle_rad)
            print(f"保持后: position={position}, angle={angle_deg:.2f} deg, current={active_current}")
            result = input("结果 stable/drop/lift/skip [stable]: ").strip().lower() or "stable"
            if result not in ("stable", "drop", "lift", "skip"):
                print("结果只能是 stable/drop/lift/skip，本次不记录。")
                continue
            if result != "skip":
                append_sample(csv_path, args.servo_id, position, angle_deg, active_current, result)
                print(f"已记录到 {csv_path}")

    except KeyboardInterrupt:
        print("\n收到中断，正在安全退出电流模式...")
    finally:
        if in_current_mode:
            try:
                # 安全退出顺序：先把电流斜坡归零，再切回位置模式。
                ramp_current(driver, args.servo_id, active_current, 0, args.step, args.step_delay)
                driver.hls_set_position_mode(args.servo_id)
            finally:
                robot.disconnect()
        else:
            robot.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HLS gravity compensation calibration")
    parser.add_argument("--port", type=str, default="", help="Serial port, for example COM11")
    parser.add_argument("--servo-id", type=int, default=2, help="Servo ID to calibrate, recommended 2 or 3")
    parser.add_argument("--output", type=str, default="hls_gravity_calibration.csv", help="CSV output path")
    parser.add_argument("--max-abs-current", type=int, default=250, help="Safety current limit")
    parser.add_argument("--step", type=int, default=5, help="Current ramp step")
    parser.add_argument("--step-delay", type=float, default=0.03, help="Delay between ramp steps")
    parser.add_argument("--hold-time", type=float, default=2.0, help="Hold time after reaching target current")
    parser.add_argument("--debug", action="store_true", help="Enable SDK debug logs")
    main(parser.parse_args())
