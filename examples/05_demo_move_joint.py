# Copyright (c) 2025 Synria Robotics Co., Ltd.
# Licensed under the MIT License.
#
# Author: Synria Robotics Team
# Website: https://synriarobotics.ai

"""六轴关节位置运动示例。

流程与原版 Demo05 一致：先运动到零位，再运动到示例目标，最后返回零位。
本示教臂不带夹爪，因此回零只发送六轴关节目标。
"""

import sys
import time
import math
from pathlib import Path

# 直接运行 examples 下的脚本时，优先使用当前仓库中的 SDK。
SDK_ROOT = Path(__file__).resolve().parents[1]
sdk_root = str(SDK_ROOT)
if sdk_root in sys.path:
    sys.path.remove(sdk_root)
sys.path.insert(0, sdk_root)

import alicia_d_sdk
from alicia_d_sdk.utils.logger import logger


HOME_JOINTS_DEG = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
TARGET_JOINTS_DEG = [-30.0, -30.0, 30.0, 20.0, -20.0, 10.0]


def move_joints(robot, target_joints_deg, speed_deg_s, label):
    """发送六轴位置目标并等待运动完成。"""
    current_joints = robot.get_robot_state("joint")
    if current_joints is None:
        raise RuntimeError(f"{label}前未能读取关节位置")

    target_joints_rad = [math.radians(value) for value in target_joints_deg]
    max_travel_rad = max(
        abs(target - current)
        for target, current in zip(target_joints_rad, current_joints)
    )
    timeout = max(10.0, max_travel_rad / math.radians(speed_deg_s) + 5.0)
    logger.info(f"{label}：{target_joints_deg} deg")
    logger.info(
        f"预计最大关节行程 {math.degrees(max_travel_rad):.1f} deg，"
        f"等待上限 {timeout:.1f} s"
    )
    reached = robot.set_robot_state(
        target_joints=target_joints_deg,
        joint_format="deg",
        speed_deg_s=speed_deg_s,
        timeout=timeout,
        wait_for_completion=True,
    )
    if reached:
        logger.info(f"{label}完成。")
    else:
        logger.warning(f"{label}未在等待时间内到达目标，继续下一阶段。")
    return reached


def main(args):
    """执行六轴目标姿态往返测试。"""
    robot = alicia_d_sdk.create_robot(port=args.port)
    torque_enabled_by_demo = False

    try:
        control_mode = robot.get_control_mode(timeout=2.0)
        if control_mode is None:
            raise RuntimeError("未能读取 D 端控制模式，请确认固件和串口连接")
        logger.info(f"当前控制模式：{control_mode}")
        if control_mode != "position":
            raise RuntimeError("该示例只支持位置模式，请先切换为 position")

        logger.warning(
            "机械臂将依次运动到零位、示例目标姿态并返回零位，"
            "请确认运动范围内没有障碍物。"
        )
        input("按 Enter 开启扭矩并开始测试...")
        if not robot.torque_control("on"):
            raise RuntimeError("扭矩开启命令发送失败")
        torque_enabled_by_demo = True
        time.sleep(0.5)

        stage_results = []
        stage_results.append(
            ("运动到零位", move_joints(
                robot, HOME_JOINTS_DEG, args.speed_deg_s, "运动到零位"
            ))
        )
        time.sleep(1.0)
        stage_results.append(
            ("运动到示例目标", move_joints(
                robot,
                TARGET_JOINTS_DEG,
                args.speed_deg_s,
                "运动到示例目标",
            ))
        )
        time.sleep(1.0)
        stage_results.append(
            ("返回零位", move_joints(
                robot, HOME_JOINTS_DEG, args.speed_deg_s, "返回零位"
            ))
        )

        failed_stages = [name for name, reached in stage_results if not reached]
        if failed_stages:
            logger.warning(
                "Demo05 已执行完整流程，但以下阶段未通过到位检查："
                + "、".join(failed_stages)
            )
        else:
            logger.info("Demo05 六轴位置运动测试全部通过。")

    except KeyboardInterrupt:
        logger.warning("测试已中断")
    except Exception as exc:
        logger.warning(f"测试未完成：{exc}")
    finally:
        try:
            if torque_enabled_by_demo:
                logger.warning(
                    "机械臂当前仍在位置保持。请先用手托住机械臂，"
                    "再按 Enter 关闭扭矩。"
                )
                input("确认已托住后按 Enter 关闭扭矩并退出...")
                if robot.torque_control("off"):
                    logger.info("扭矩已关闭。")
                else:
                    logger.warning("扭矩关闭命令发送失败，请保持托举并检查设备。")
        finally:
            robot.disconnect()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="六轴关节位置运动控制示例")
    parser.add_argument(
        "--port",
        type=str,
        default="",
        help="串口端口（例如 /dev/ttyUSB0 或 COM3）",
    )
    parser.add_argument(
        "--speed_deg_s",
        type=float,
        default=1.0,
        help="关节运动速度，单位 deg/s，默认 1",
    )
    main(parser.parse_args())
