#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例2: 高级控制 - 展示新架构的高级功能

这个示例展示了如何使用重构后的SDK进行高级控制操作，
包括轨迹规划、状态监控、错误处理等。
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'alicia_d_sdk_v5.6.0'))

from alicia_d_sdk_v5_6_0 import create_robot
import time
import numpy as np


def progress_callback(current_step, total_steps, joint_angles):
    """进度回调函数"""
    progress = current_step / total_steps * 100
    print(f"执行进度: {progress:.1f}% ({current_step}/{total_steps})")


def completion_callback(total_steps):
    """完成回调函数"""
    print(f"轨迹执行完成，共{total_steps}个点")


def error_callback(error_message):
    """错误回调函数"""
    print(f"执行错误: {error_message}")


def main():
    """主函数"""
    print("=== Alicia-D SDK v5.6.0 高级控制示例 ===")
    
    # 创建机械臂实例
    robot = create_robot(port="COM6", baudrate=1000000, debug_mode=True)
    
    try:
        # 连接到机械臂
        print("正在连接机械臂...")
        if not robot.connect():
            print("连接失败，请检查串口设置")
            return
        
        print("连接成功！")
        
        # 设置关节限位
        joint_limits = [
            (-3.14, 3.14),  # 关节1
            (-1.57, 1.57),  # 关节2
            (-3.14, 3.14),  # 关节3
            (-3.14, 3.14),  # 关节4
            (-1.57, 1.57),  # 关节5
            (-3.14, 3.14),  # 关节6
        ]
        robot.set_joint_limits(joint_limits)
        
        # 设置笛卡尔限位
        cartesian_limits = {
            'x': (0.1, 0.5),
            'y': (-0.3, 0.3),
            'z': (0.05, 0.4)
        }
        robot.set_cartesian_limits(cartesian_limits)
        
        # 移动到初始位置
        print("\n移动到初始位置...")
        robot.moveHome()
        
        # 多点关节轨迹
        print("\n多点关节轨迹...")
        waypoints = [
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.5, -0.3, 0.2, 0.0, 0.5, 0.0],
            [0.3, 0.2, 0.3, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        ]
        
        robot.moveJ_waypoints(
            waypoints=waypoints,
            joint_format='rad',
            speed_factor=0.5,
            interpolation_type="cubic",
            progress_callback=progress_callback,
            completion_callback=completion_callback,
            error_callback=error_callback
        )
        
        # 多点笛卡尔轨迹
        print("\n多点笛卡尔轨迹...")
        pose_waypoints = [
            [0.3, 0.0, 0.2, 0, 0, 0, 1],
            [0.3, 0.1, 0.2, 0, 0, 0, 1],
            [0.3, 0.1, 0.3, 0, 0, 0, 1],
            [0.3, 0.0, 0.3, 0, 0, 0, 1],
            [0.3, 0.0, 0.2, 0, 0, 0, 1]
        ]
        
        robot.moveCartesian(
            waypoints=pose_waypoints,
            speed_factor=0.3,
            interpolation_type="linear",
            progress_callback=progress_callback,
            completion_callback=completion_callback,
            error_callback=error_callback
        )
        
        # 状态监控
        print("\n状态监控...")
        for i in range(10):
            joints = robot.get_joints()
            pose = robot.get_pose()
            gripper = robot.get_gripper()
            
            print(f"状态 {i+1}:")
            print(f"  关节角度: {[round(j, 3) for j in joints] if joints else 'None'}")
            print(f"  位姿: {[round(p, 3) for p in pose] if pose else 'None'}")
            print(f"  夹爪: {round(gripper, 3) if gripper else 'None'}")
            print(f"  运动状态: {robot.is_moving()}")
            
            time.sleep(1)
        
        # 在线控制演示
        print("\n在线控制演示...")
        robot.start_online_control(command_rate_hz=100)
        
        # 创建圆形轨迹
        center = [0.3, 0.0, 0.25]
        radius = 0.05
        for i in range(20):
            angle = i * 2 * np.pi / 20
            x = center[0] + radius * np.cos(angle)
            y = center[1] + radius * np.sin(angle)
            z = center[2]
            
            target_pose = [x, y, z, 0, 0, 0, 1]
            robot.set_pose_target(target_pose)
            time.sleep(0.1)
        
        robot.stop_online_control()
        
        # 夹爪序列控制
        print("\n夹爪序列控制...")
        gripper_angles = [0, 25, 50, 75, 100, 75, 50, 25, 0]
        for angle in gripper_angles:
            robot.gripper_control(angle_deg=angle, wait_for_completion=True)
            time.sleep(0.5)
        
        # 返回初始位置
        print("\n返回初始位置...")
        robot.moveHome()
        
        print("\n高级控制示例完成！")
        
    except KeyboardInterrupt:
        print("\n用户中断")
        robot.emergency_stop()
    except Exception as e:
        print(f"\n发生错误: {e}")
        robot.emergency_stop()
    finally:
        # 断开连接
        robot.disconnect()
        print("已断开连接")


if __name__ == "__main__":
    main()