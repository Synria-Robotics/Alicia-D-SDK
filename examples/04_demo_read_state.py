#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例4: 读取状态 - 展示如何读取机械臂状态信息

这个示例展示了如何读取机械臂的关节角度、末端位姿、夹爪状态等信息。
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'alicia_d_sdk'))

from alicia_d_sdk import create_robot
import time


def main():
    """主函数"""
    print("=== Alicia-D SDK 读取状态示例 ===")
    
    # 创建机械臂实例
    robot = create_robot(port="COM6", baudrate=1000000, debug_mode=True)
    
    try:
        # 连接到机械臂
        print("正在连接机械臂...")
        if not robot.connect():
            print("连接失败，请检查串口设置")
            return
        
        print("连接成功！")
        
        # 连续读取状态信息
        print("\n开始读取状态信息（按Ctrl+C停止）...")
        try:
            while True:
                # 读取关节角度
                joints = robot.get_joints()
                if joints:
                    print(f"关节角度 (弧度): {[round(j, 3) for j in joints]}")
                    print(f"关节角度 (度): {[round(j * 180 / 3.14159, 1) for j in joints]}")
                
                # 读取末端位姿
                pose = robot.get_pose()
                if pose:
                    print(f"末端位姿: 位置=[{pose[0]:.3f}, {pose[1]:.3f}, {pose[2]:.3f}], "
                          f"姿态=[{pose[3]:.3f}, {pose[4]:.3f}, {pose[5]:.3f}, {pose[6]:.3f}]")
                
                # 读取夹爪状态
                gripper = robot.get_gripper()
                if gripper is not None:
                    print(f"夹爪角度: {gripper:.1f}°")
                
                # 检查运动状态
                is_moving = robot.is_moving()
                print(f"运动状态: {'运动中' if is_moving else '静止'}")
                
                print("-" * 50)
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n停止读取状态")
        
        print("\n示例完成！")
        
    except Exception as e:
        print(f"\n发生错误: {e}")
    finally:
        # 断开连接
        robot.disconnect()
        print("已断开连接")


if __name__ == "__main__":
    main()