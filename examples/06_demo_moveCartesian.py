#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例6: 笛卡尔空间运动 - 展示如何进行笛卡尔空间运动控制

这个示例展示了如何使用movePose和moveCartesian进行笛卡尔空间运动控制。
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'alicia_d_sdk'))

from alicia_d_sdk import create_robot
import time
import numpy as np


def main():
    """主函数"""
    print("=== Alicia-D SDK 笛卡尔空间运动示例 ===")
    
    # 创建机械臂实例
    robot = create_robot(port="COM6", baudrate=1000000, debug_mode=True)
    
    try:
        # 连接到机械臂
        print("正在连接机械臂...")
        if not robot.connect():
            print("连接失败，请检查串口设置")
            return
        
        print("连接成功！")
        
        # 移动到初始位置
        print("\n移动到初始位置...")
        robot.moveHome()
        
        # 单点位姿运动
        print("\n单点位姿运动...")
        target_pose = [0.3, 0.1, 0.2, 0, 0, 0, 1]  # [x, y, z, qx, qy, qz, qw]
        print(f"目标位姿: 位置=[{target_pose[0]:.3f}, {target_pose[1]:.3f}, {target_pose[2]:.3f}], "
              f"姿态=[{target_pose[3]:.3f}, {target_pose[4]:.3f}, {target_pose[5]:.3f}, {target_pose[6]:.3f}]")
        robot.movePose(target_pose=target_pose, speed_factor=0.5)
        
        time.sleep(2)
        
        # 多点笛卡尔轨迹 - 矩形路径
        print("\n多点笛卡尔轨迹 - 矩形路径...")
        pose_waypoints = [
            [0.3, 0.0, 0.2, 0, 0, 0, 1],  # 起点
            [0.3, 0.1, 0.2, 0, 0, 0, 1],  # 右上
            [0.3, 0.1, 0.3, 0, 0, 0, 1],  # 右上高
            [0.3, 0.0, 0.3, 0, 0, 0, 1],  # 左上高
            [0.3, 0.0, 0.2, 0, 0, 0, 1]   # 回到起点
        ]
        
        print("轨迹点:")
        for i, wp in enumerate(pose_waypoints):
            print(f"  点{i+1}: 位置=[{wp[0]:.3f}, {wp[1]:.3f}, {wp[2]:.3f}], "
                  f"姿态=[{wp[3]:.3f}, {wp[4]:.3f}, {wp[5]:.3f}, {wp[6]:.3f}]")
        
        robot.moveCartesian(
            waypoints=pose_waypoints,
            speed_factor=0.3,
            interpolation_type="linear"
        )
        
        time.sleep(2)
        
        # 圆形轨迹
        print("\n圆形轨迹...")
        center = [0.3, 0.0, 0.25]
        radius = 0.05
        num_points = 16
        
        circle_waypoints = []
        for i in range(num_points + 1):  # +1 回到起点
            angle = i * 2 * np.pi / num_points
            x = center[0] + radius * np.cos(angle)
            y = center[1] + radius * np.sin(angle)
            z = center[2]
            circle_waypoints.append([x, y, z, 0, 0, 0, 1])
        
        print(f"圆形轨迹: 中心={center}, 半径={radius}, 点数={len(circle_waypoints)}")
        robot.moveCartesian(
            waypoints=circle_waypoints,
            speed_factor=0.2,
            interpolation_type="cubic"
        )
        
        time.sleep(2)
        
        # 螺旋轨迹
        print("\n螺旋轨迹...")
        spiral_waypoints = []
        for i in range(20):
            angle = i * 2 * np.pi / 10
            x = center[0] + radius * np.cos(angle)
            y = center[1] + radius * np.sin(angle)
            z = center[2] + i * 0.01  # 逐渐上升
            spiral_waypoints.append([x, y, z, 0, 0, 0, 1])
        
        print(f"螺旋轨迹: 点数={len(spiral_waypoints)}")
        robot.moveCartesian(
            waypoints=spiral_waypoints,
            speed_factor=0.15,
            interpolation_type="cubic"
        )
        
        time.sleep(2)
        
        # 返回初始位置
        print("\n返回初始位置...")
        robot.moveHome()
        
        print("\n笛卡尔空间运动示例完成！")
        
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