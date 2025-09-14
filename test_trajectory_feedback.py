#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试轨迹执行反馈功能

这个脚本用于测试修复后的轨迹执行反馈功能是否正常工作。
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'alicia_d_sdk'))

from alicia_d_sdk import create_robot
import time


def test_trajectory_feedback():
    """测试轨迹执行反馈功能"""
    print("=== 测试轨迹执行反馈功能 ===")
    
    # 创建机械臂实例
    robot = create_robot(port="COM6", baudrate=1000000, debug_mode=True)
    
    try:
        # 连接到机械臂
        print("正在连接机械臂...")
        if not robot.connect():
            print("连接失败，请检查串口设置")
            return False
        
        print("连接成功！")
        
        # 测试1: 检查初始状态
        print("\n=== 测试1: 检查初始状态 ===")
        print(f"初始运动状态: {robot.is_moving()}")
        print(f"初始在线控制状态: {robot.is_online_control_active()}")
        
        # 测试2: 单点关节运动
        print("\n=== 测试2: 单点关节运动 ===")
        target_joints = [0.1, 0.1, 0.1, 0.0, 0.0, 0.0]
        print(f"目标关节角度: {target_joints}")
        
        # 开始运动
        print("开始运动...")
        success = robot.moveJ(target_joints=target_joints, joint_format='rad', speed_factor=0.5)
        
        if success:
            print("运动命令发送成功")
            
            # 监控运动状态
            print("监控运动状态...")
            for i in range(20):  # 监控2秒
                is_moving = robot.is_moving()
                print(f"  第{i+1}次检查: 运动状态 = {is_moving}")
                time.sleep(0.1)
        else:
            print("运动命令发送失败")
        
        # 测试3: 多点关节轨迹
        print("\n=== 测试3: 多点关节轨迹 ===")
        waypoints = [
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.2, 0.1, 0.1, 0.0, 0.0, 0.0],
            [0.1, 0.2, 0.1, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        ]
        
        print("开始多点轨迹...")
        success = robot.moveJ_waypoints(
            waypoints=waypoints,
            joint_format='rad',
            speed_factor=0.3
        )
        
        if success:
            print("多点轨迹命令发送成功")
            
            # 监控运动状态
            print("监控运动状态...")
            for i in range(50):  # 监控5秒
                is_moving = robot.is_moving()
                print(f"  第{i+1}次检查: 运动状态 = {is_moving}")
                time.sleep(0.1)
        else:
            print("多点轨迹命令发送失败")
        
        # 测试4: 在线控制
        print("\n=== 测试4: 在线控制 ===")
        print("启动在线控制...")
        success = robot.start_online_control(command_rate_hz=50)
        
        if success:
            print("在线控制启动成功")
            print(f"在线控制状态: {robot.is_online_control_active()}")
            
            # 设置目标
            target_joints = [0.1, 0.1, 0.1, 0.0, 0.0, 0.0]
            robot.set_joint_target(target_joints)
            
            # 监控状态
            for i in range(20):
                is_moving = robot.is_moving()
                is_online = robot.is_online_control_active()
                print(f"  第{i+1}次检查: 运动状态 = {is_moving}, 在线控制 = {is_online}")
                time.sleep(0.1)
            
            # 停止在线控制
            robot.stop_online_control()
            print("在线控制已停止")
            print(f"在线控制状态: {robot.is_online_control_active()}")
        else:
            print("在线控制启动失败")
        
        # 测试5: 状态查询
        print("\n=== 测试5: 状态查询 ===")
        joints = robot.get_joints()
        pose = robot.get_pose()
        gripper = robot.get_gripper()
        
        print(f"当前关节角度: {joints}")
        print(f"当前位姿: {pose}")
        print(f"当前夹爪角度: {gripper}")
        print(f"运动状态: {robot.is_moving()}")
        print(f"在线控制状态: {robot.is_online_control_active()}")
        
        print("\n=== 测试完成 ===")
        return True
        
    except KeyboardInterrupt:
        print("\n用户中断")
        return False
    except Exception as e:
        print(f"\n发生错误: {e}")
        return False
    finally:
        # 断开连接
        robot.disconnect()
        print("已断开连接")


if __name__ == "__main__":
    success = test_trajectory_feedback()
    if success:
        print("\n✅ 轨迹执行反馈功能测试通过")
    else:
        print("\n❌ 轨迹执行反馈功能测试失败")