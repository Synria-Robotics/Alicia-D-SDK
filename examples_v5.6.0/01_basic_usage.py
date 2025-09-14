#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例1: 基本使用 - 展示新架构的基本功能

这个示例展示了如何使用重构后的SDK进行基本的机械臂操作。
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'alicia_d_sdk_v5.6.0'))

from alicia_d_sdk_v5_6_0 import create_robot
import time


def main():
    """主函数"""
    print("=== Alicia-D SDK v5.6.0 基本使用示例 ===")
    
    # 创建机械臂实例
    robot = create_robot(port="COM6", baudrate=1000000, debug_mode=True)
    
    try:
        # 连接到机械臂
        print("正在连接机械臂...")
        if not robot.connect():
            print("连接失败，请检查串口设置")
            return
        
        print("连接成功！")
        
        # 打印当前状态
        print("\n当前状态:")
        robot.print_state()
        
        # 移动到初始位置
        print("\n移动到初始位置...")
        robot.moveHome()
        
        # 关节空间运动
        print("\n关节空间运动...")
        target_joints = [0.5, -0.3, 0.2, 0.0, 0.5, 0.0]  # 弧度
        robot.moveJ(target_joints=target_joints, joint_format='rad')
        
        # 笛卡尔空间运动
        print("\n笛卡尔空间运动...")
        target_pose = [0.3, 0.1, 0.2, 0, 0, 0, 1]  # [x, y, z, qx, qy, qz, qw]
        robot.movePose(target_pose=target_pose)
        
        # 夹爪控制
        print("\n夹爪控制...")
        robot.gripper_control(command="open")
        time.sleep(1)
        robot.gripper_control(command="close")
        time.sleep(1)
        robot.gripper_control(angle_deg=50)  # 50度
        
        # 在线控制
        print("\n在线控制...")
        robot.start_online_control()
        
        # 设置一些目标
        for i in range(5):
            target = [0.2 + i * 0.1, 0.1, 0.2, 0, 0, 0, 1]
            robot.set_pose_target(target)
            time.sleep(2)
        
        robot.stop_online_control()
        
        # 返回初始位置
        print("\n返回初始位置...")
        robot.moveHome()
        
        print("\n示例完成！")
        
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"\n发生错误: {e}")
    finally:
        # 断开连接
        robot.disconnect()
        print("已断开连接")


if __name__ == "__main__":
    main()