# Copyright (c) 2025 Synria Robotics Co., Ltd.
# Licensed under the MIT License.
#
# Author: Synria Robotics Team
# Website: https://synriarobotics.ai

"""将示教臂当前六轴姿态设置为新零点。"""

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
        if not robot.zero_calibration():
            raise RuntimeError("六轴调零未完成，请根据上方回读信息检查。")
        logger.info("Demo02 整臂调零命令发送完成。")
        logger.warning(
            "请重新上电后运行 Demo03，确认机械零位下六轴回读均接近 0 deg。"
        )
    except Exception as exc:
        print(f"错误：{exc}")
        import traceback
        traceback.print_exc()
    finally:
        robot.disconnect()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="示教臂六轴零点校准")
    parser.add_argument(
        '--port',
        type=str,
        default="",
        help="串口，例如 COM11 或 /dev/ttyUSB0",
    )
    args = parser.parse_args()

    main(args)
