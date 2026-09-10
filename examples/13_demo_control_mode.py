# Copyright (c) 2026 Synria Robotics Co., Ltd.
# Licensed under the MIT License.

"""安全验证公开的位置/电流控制模式接口。"""

import argparse
import sys
from pathlib import Path

# 直接运行 examples 下的脚本时，优先使用当前仓库中的 SDK。
SDK_ROOT = Path(__file__).resolve().parents[1]
sdk_root = str(SDK_ROOT)
if sdk_root in sys.path:
    sys.path.remove(sdk_root)
sys.path.insert(0, sdk_root)

import alicia_d_sdk
from alicia_d_sdk.utils.logger import logger


def main(args):
    logger.info(f"当前 SDK 路径：{Path(alicia_d_sdk.__file__).resolve()}")
    robot = alicia_d_sdk.create_robot(port=args.port)
    try:
        initial_mode = robot.get_control_mode()
        logger.info(f"当前控制模式：{initial_mode}")
        logger.warning("关闭扭矩前请先用手托住机械臂。")
        input("按 Enter 关闭扭矩并开始模式验证...")
        if not robot.torque_control("off"):
            raise RuntimeError("扭矩关闭命令发送失败")

        if not robot.set_control_mode("current"):
            raise RuntimeError("电流模式切换失败")
        logger.info(f"当前控制模式：{robot.get_control_mode()}")

        input("当前为电流模式且扭矩关闭。按 Enter 恢复位置模式...")
        if not robot.set_control_mode("position"):
            raise RuntimeError("位置模式恢复失败")
        logger.info(f"当前控制模式：{robot.get_control_mode()}")
        logger.info("模式验证完成，扭矩保持关闭。")
    finally:
        # Always request the compatibility default before disconnecting.
        try:
            robot.set_control_mode("position")
        finally:
            robot.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="验证 Alicia-D 位置/电流模式切换"
    )
    parser.add_argument(
        "--port",
        type=str,
        default="",
        help="串口，例如 COM11 或 /dev/ttyUSB0",
    )
    main(parser.parse_args())
