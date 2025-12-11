"""
Demo: Gripper control

Copyright (c) 2025 Synria Robotics Co., Ltd.
Licensed under GPL v3.0

Features:
- Open/close gripper
- Control gripper to specific angle
- Wait for gripper motion completion
"""

import alicia_d_sdk
import time
from alicia_d_sdk.utils.logger import logger

def main(args):
    """Demonstrate gripper control.
    
    :param args: Command line arguments
    """
    # Initialize robot instance
    robot = alicia_d_sdk.create_robot(
        port=args.port,
        baudrate=args.baudrate,
        robot_version=args.robot_version,
        gripper_type=args.gripper_type    
    )
    
    try:
        # Connect to robot
        if not robot.connect():
            return
        
        # Get gripper value (0-100)
        gripper_value = robot.get_gripper()
        logger.info(f"Gripper value: {gripper_value:.1f}")
        
        # # Test 1: Open gripper
        robot.set_gripper_target(command='open', wait_for_completion=True)
        time.sleep(1)
        robot.set_gripper_target(command='close', wait_for_completion=True)
        time.sleep(1)
        # Test 3: Partially open
        robot.set_gripper_target(command='open', wait_for_completion=True)
        time.sleep(1)

        
    except KeyboardInterrupt:
        print("\n✗ Processing interrupted")
    
    except Exception as e:
        import traceback
        traceback.print_exc()
    
    finally:
        robot.disconnect()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Gripper Control Demo")
    
    # Serial port settings
    parser.add_argument('--port', type=str, default="/dev/ttyUSB0", help="串口端口 (例如: /dev/ttyUSB0 或 COM3)")
    parser.add_argument('--baudrate', type=int, default=1000000,  help="波特率 (默认: 1000000)")
    parser.add_argument('--robot_version', type=str, default="v5_6",  help="机器人版本 (默认: v5_6)")
    parser.add_argument('--gripper_type', type=str, default="50mm",  help="夹爪型号 (默认: 50mm)")
    
    args = parser.parse_args()
    
    
    main(args)
