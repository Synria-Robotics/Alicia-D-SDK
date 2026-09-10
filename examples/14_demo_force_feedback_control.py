# Copyright (c) 2026 Synria Robotics Co., Ltd.
# Licensed under the MIT License.

"""验证遥操与力反馈公开控制接口。

该示例只使用公开SDK接口，不直接发送内部协议帧。固件和SDK必须先实现
0x06/0x20控制/状态协议；能力缺失时，本示例会在改变机械臂状态前退出。
"""

import argparse
import sys
import time
from pathlib import Path


SDK_ROOT = Path(__file__).resolve().parents[1]
sdk_root = str(SDK_ROOT)
if sdk_root in sys.path:
    sys.path.remove(sdk_root)
sys.path.insert(0, sdk_root)

import alicia_d_sdk
from alicia_d_sdk.utils.logger import logger


REQUIRED_METHODS = (
    "set_teleoperation_enabled",
    "set_force_feedback_enabled",
    "set_control_mode",
    "get_control_mode",
)


def _restore_position_mode(robot, attempts=3):
    """依次关闭力反馈、退出遥操并确认位置模式。"""
    for attempt in range(1, attempts + 1):
        try:
            feedback_disabled = robot.set_force_feedback_enabled(
                False, timeout=2.0
            )
            position_applied = robot.set_control_mode("position", timeout=3.0)
            mode = robot.get_control_mode(timeout=1.0)
            if feedback_disabled and position_applied and mode == "position":
                logger.info("力反馈已关闭，遥操已退出，当前为position模式。")
                return True
            logger.warning(
                f"第{attempt}次退出未完成：力反馈关闭={feedback_disabled}，"
                f"位置模式切换={position_applied}，当前模式={mode}"
            )
        except Exception as exc:
            logger.warning(f"安全收尾第{attempt}次失败：{exc}")
        time.sleep(0.15)

    logger.warning(
        "安全收尾失败：D端未确认返回position模式。"
        "请勿运行其他位置控制Demo，先重新上电并检查控制模式。"
    )
    return False


def main(args):
    logger.info(f"当前 SDK 路径：{Path(alicia_d_sdk.__file__).resolve()}")
    robot = alicia_d_sdk.create_robot(port=args.port)
    position_restored = False
    try:
        missing = [name for name in REQUIRED_METHODS if not hasattr(robot, name)]
        if missing:
            logger.warning(
                "当前SDK尚未实现Demo14所需公开接口：" + "、".join(missing)
            )
            logger.warning(
                "请先完成D端0x06/0x20协议和SDK封装；本次未改变机械臂状态。"
            )
            return

        logger.warning(
            "即将开启遥操。请确认D、M两端姿态接近，运动范围内没有障碍物。"
        )
        input("确认安全后按 Enter 开启遥操...")
        if not robot.set_teleoperation_enabled(True):
            raise RuntimeError("遥操开启请求未被确认")
        logger.info("遥操已开启。")

        input("按 Enter 开启力反馈...")
        if not robot.set_force_feedback_enabled(True):
            raise RuntimeError("力反馈开启请求未被确认")
        logger.info("力反馈已开启。")

        input("按 Enter 关闭力反馈并退出遥操...")
        if not _restore_position_mode(robot):
            raise RuntimeError("退出遥操后未确认返回position模式")
        position_restored = True
        logger.info("Demo14 遥操与力反馈接口测试完成。")
    finally:
        if not position_restored:
            _restore_position_mode(robot)
        robot.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="验证遥操与力反馈公开接口")
    parser.add_argument(
        "--port", type=str, default="", help="串口，例如 COM11 或 /dev/ttyUSB0"
    )
    main(parser.parse_args())
