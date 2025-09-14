#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例10: 在线控制 - 展示如何进行在线实时控制

这个示例展示了如何使用在线控制功能进行实时控制。
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'alicia_d_sdk'))

from alicia_d_sdk import create_robot
import time
import numpy as np


def main():
    """主函数"""
    print("=== Alicia-D SDK 在线控制示例 ===")
    
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
        
        # 在线控制演示
        print("\n在线控制演示...")
        
        # 启动在线控制
        print("启动在线控制...")
        robot.start_online_control(command_rate_hz=100)
        
        # 关节空间在线控制
        print("\n关节空间在线控制...")
        print("执行正弦波轨迹...")
        
        for i in range(100):
            t = i * 0.1
            # 生成正弦波轨迹
            joint1 = 0.2 * np.sin(t)
            joint2 = 0.1 * np.sin(t * 1.5)
            joint3 = 0.15 * np.sin(t * 0.8)
            joint4 = 0.1 * np.sin(t * 2.0)
            joint5 = 0.1 * np.sin(t * 1.2)
            joint6 = 0.1 * np.sin(t * 0.5)
            
            target_joints = [joint1, joint2, joint3, joint4, joint5, joint6]
            robot.set_joint_target(target_joints)
            
            if i % 10 == 0:
                print(f"时间: {t:.1f}s, 目标: {[round(j, 3) for j in target_joints]}")
            
            time.sleep(0.1)
        
        # 笛卡尔空间在线控制
        print("\n笛卡尔空间在线控制...")
        print("执行圆形轨迹...")
        
        center = [0.3, 0.0, 0.25]
        radius = 0.05
        
        for i in range(50):
            angle = i * 2 * np.pi / 50
            x = center[0] + radius * np.cos(angle)
            y = center[1] + radius * np.sin(angle)
            z = center[2]
            
            target_pose = [x, y, z, 0, 0, 0, 1]
            robot.set_pose_target(target_pose)
            
            if i % 10 == 0:
                print(f"角度: {angle:.2f}rad, 位置: [{x:.3f}, {y:.3f}, {z:.3f}]")
            
            time.sleep(0.1)
        
        # 停止在线控制
        print("\n停止在线控制...")
        robot.stop_online_control()
        
        # 返回初始位置
        print("返回初始位置...")
        robot.moveHome()
        
        # 高级在线控制演示
        print("\n高级在线控制演示...")
        
        # 启动高频率在线控制
        print("启动高频率在线控制...")
        robot.start_online_control(command_rate_hz=200)
        
        # 执行复杂轨迹
        print("执行复杂轨迹...")
        
        for i in range(200):
            t = i * 0.05
            
            # 生成复杂轨迹
            x = 0.3 + 0.05 * np.sin(t) * np.cos(t * 0.5)
            y = 0.05 * np.sin(t * 1.5) * np.cos(t * 0.3)
            z = 0.25 + 0.02 * np.sin(t * 2.0)
            
            # 生成旋转
            qx = 0.1 * np.sin(t * 0.8)
            qy = 0.1 * np.cos(t * 0.6)
            qz = 0.1 * np.sin(t * 1.2)
            qw = np.sqrt(1 - qx*qx - qy*qy - qz*qz)
            
            target_pose = [x, y, z, qx, qy, qz, qw]
            robot.set_pose_target(target_pose)
            
            if i % 40 == 0:
                print(f"时间: {t:.2f}s, 位置: [{x:.3f}, {y:.3f}, {z:.3f}]")
            
            time.sleep(0.05)
        
        # 停止在线控制
        print("\n停止在线控制...")
        robot.stop_online_control()
        
        # 返回初始位置
        print("返回初始位置...")
        robot.moveHome()
        
        print("\n在线控制示例完成！")
        
    except KeyboardInterrupt:
        print("\n用户中断")
        robot.stop_online_control()
    except Exception as e:
        print(f"\n发生错误: {e}")
        robot.stop_online_control()
    finally:
        # 确保停止在线控制
        robot.stop_online_control()
        # 断开连接
        robot.disconnect()
        print("已断开连接")


if __name__ == "__main__":
    main()