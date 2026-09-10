# Copyright (c) 2025 Synria Robotics Co., Ltd.
# Licensed under the MIT License.
#
# Author: Synria Robotics Team
# Website: https://synriarobotics.ai

"""示教臂扭矩开关示例。"""

import sys
from pathlib import Path

# 直接运行 examples 下的脚本时，优先使用当前仓库中的 SDK，而不是已安装的旧版本。
SDK_ROOT = Path(__file__).resolve().parents[1]
sdk_root = str(SDK_ROOT)
if sdk_root in sys.path:
    sys.path.remove(sdk_root)
sys.path.insert(0, sdk_root)

import alicia_d_sdk
from alicia_d_sdk.utils.logger import logger

def main(args):
    """执行示教臂扭矩开关测试。
    
    :param args: Command line arguments containing port
    """
    # Initialize robot instance
    robot = alicia_d_sdk.create_robot(
        port=args.port,
    )
    
    try:
        control_mode = robot.get_control_mode(timeout=2.0)
        if control_mode is None:
            raise RuntimeError("未能读取 D 端控制模式，请确认固件和串口连接")
        logger.info(f"当前控制模式：{control_mode}")
        if control_mode != "position":
            raise RuntimeError(
                "该示例只验证位置模式扭矩保持；当前不是位置模式，请先切换为 position"
            )

        if not robot.torque_control('off'):
            raise RuntimeError("初始扭矩关闭命令发送失败")
        logger.info("当前扭矩已设为关闭，请用手托住机械臂。")

        input("按 Enter 开启扭矩并进入位置保持...")
        if not robot.torque_control('on'):
            raise RuntimeError("扭矩开启命令发送失败")
        logger.info("扭矩开启命令已发送，请确认机械臂是否进入位置保持。")

        input("按 Enter 关闭扭矩并退出...")
        if not robot.torque_control('off'):
            raise RuntimeError("扭矩关闭命令发送失败")
        logger.info("扭矩已关闭，测试结束。")
        
    
    except Exception as e:
        print(f"错误：{e}")
        
        import traceback
        traceback.print_exc()
    
    finally:
        robot.disconnect()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="示教臂扭矩开关测试")
    
    # Robot configuration
    parser.add_argument('--port', type=str, default="", help="串口，例如 COM11 或 /dev/ttyUSB0")
    args = parser.parse_args()

    main(args)
