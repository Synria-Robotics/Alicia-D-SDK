#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例5: 关节空间运动 - 展示如何进行关节空间运动控制

这个示例展示了如何使用moveJ和moveJ_waypoints进行关节空间运动控制。
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'alicia_d_sdk'))

from alicia_d_sdk import create_robot
import time


def main():
    """主函数"""
    print("=== Alicia-D SDK 关节空间运动示例 ===")
    
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
        
        # 单点关节运动
        print("\n单点关节运动...")
        target_joints = [0.5, -0.3, 0.2, 0.0, 0.5, 0.0]  # 弧度
        print(f"目标关节角度: {[round(j, 3) for j in target_joints]}")
        robot.moveJ(target_joints=target_joints, joint_format='rad', speed_factor=0.5)
        
        time.sleep(2)
        
        # 多点关节轨迹
        print("\n多点关节轨迹...")
        waypoints = [
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],      # 初始位置
            [0.3, -0.2, 0.1, 0.0, 0.3, 0.0],     # 中间点1
            [0.6, -0.4, 0.3, 0.0, 0.6, 0.0],     # 中间点2
            [0.3, 0.2, 0.1, 0.0, -0.3, 0.0],     # 中间点3
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]       # 回到初始位置
        ]
        
        print("轨迹点:")
        for i, wp in enumerate(waypoints):
            print(f"  点{i+1}: {[round(j, 3) for j in wp]}")
        
        robot.moveJ_waypoints(
            waypoints=waypoints,
            joint_format='rad',
            speed_factor=0.3,
            interpolation_type="cubic"
        )
        
        time.sleep(2)
        
        # 使用度数的关节运动
        print("\n使用度数的关节运动...")
        target_degrees = [30, -45, 60, 0, 90, 0]  # 度数
        print(f"目标关节角度: {target_degrees}°")
        robot.moveJ(target_joints=target_degrees, joint_format='deg', speed_factor=0.4)
        
        time.sleep(2)
        
        # 返回初始位置
        print("\n返回初始位置...")
        robot.moveHome()
        
        print("\n关节空间运动示例完成！")
        
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