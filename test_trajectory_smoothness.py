#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试轨迹平滑性修复

这个脚本用于测试修复后的轨迹平滑性功能是否正常工作。
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'alicia_d_sdk'))

from alicia_d_sdk import create_robot
import time
import numpy as np


def test_trajectory_smoothness():
    """测试轨迹平滑性功能"""
    print("=== 测试轨迹平滑性修复 ===")
    
    # 创建机械臂实例
    robot = create_robot(port="COM6", baudrate=1000000, debug_mode=True)
    
    try:
        # 连接到机械臂
        print("正在连接机械臂...")
        if not robot.connect():
            print("连接失败，请检查串口设置")
            return False
        
        print("连接成功！")
        
        # 测试1: 检查执行模式配置
        print("\n=== 测试1: 执行模式配置 ===")
        
        # 测试平滑执行模式
        print("设置平滑执行模式...")
        robot.set_execution_mode("smooth")
        
        # 测试快速执行模式
        print("设置快速执行模式...")
        robot.set_execution_mode("fast")
        
        # 测试精确执行模式
        print("设置精确执行模式...")
        robot.set_execution_mode("precise")
        
        # 测试2: 单点关节运动平滑性
        print("\n=== 测试2: 单点关节运动平滑性 ===")
        
        # 启用平滑执行
        robot.set_smooth_execution(True)
        print("启用平滑执行")
        
        target_joints = [0.2, 0.1, 0.1, 0.0, 0.0, 0.0]
        print(f"目标关节角度: {target_joints}")
        
        print("开始平滑运动...")
        start_time = time.time()
        success = robot.moveJ(target_joints=target_joints, joint_format='rad', speed_factor=0.5)
        end_time = time.time()
        
        if success:
            print(f"平滑运动完成，耗时: {end_time - start_time:.2f}秒")
        else:
            print("平滑运动失败")
        
        # 测试3: 多点轨迹平滑性
        print("\n=== 测试3: 多点轨迹平滑性 ===")
        
        waypoints = [
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.1, 0.1, 0.1, 0.0, 0.0, 0.0],
            [0.2, 0.2, 0.2, 0.0, 0.0, 0.0],
            [0.1, 0.1, 0.1, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        ]
        
        print("开始多点平滑轨迹...")
        start_time = time.time()
        success = robot.moveJ_waypoints(
            waypoints=waypoints,
            joint_format='rad',
            speed_factor=0.3,
            interpolation_type="cubic"
        )
        end_time = time.time()
        
        if success:
            print(f"多点平滑轨迹完成，耗时: {end_time - start_time:.2f}秒")
        else:
            print("多点平滑轨迹失败")
        
        # 测试4: 对比平滑执行和固定延迟执行
        print("\n=== 测试4: 执行方式对比 ===")
        
        # 平滑执行
        print("测试平滑执行...")
        robot.set_smooth_execution(True)
        start_time = time.time()
        robot.moveJ([0.1, 0.1, 0.1, 0.0, 0.0, 0.0], speed_factor=0.5)
        smooth_time = time.time() - start_time
        print(f"平滑执行耗时: {smooth_time:.2f}秒")
        
        # 固定延迟执行
        print("测试固定延迟执行...")
        robot.set_smooth_execution(False)
        start_time = time.time()
        robot.moveJ([0.1, 0.1, 0.1, 0.0, 0.0, 0.0], speed_factor=0.5)
        fixed_time = time.time() - start_time
        print(f"固定延迟执行耗时: {fixed_time:.2f}秒")
        
        # 测试5: 笛卡尔空间运动平滑性
        print("\n=== 测试5: 笛卡尔空间运动平滑性 ===")
        
        # 启用平滑执行
        robot.set_smooth_execution(True)
        
        # 圆形轨迹
        center = [0.3, 0.0, 0.25]
        radius = 0.05
        num_points = 16
        
        circle_waypoints = []
        for i in range(num_points + 1):
            angle = i * 2 * np.pi / num_points
            x = center[0] + radius * np.cos(angle)
            y = center[1] + radius * np.sin(angle)
            z = center[2]
            circle_waypoints.append([x, y, z, 0, 0, 0, 1])
        
        print(f"开始圆形轨迹（{len(circle_waypoints)}个点）...")
        start_time = time.time()
        success = robot.moveCartesian(
            waypoints=circle_waypoints,
            speed_factor=0.2,
            interpolation_type="cubic"
        )
        end_time = time.time()
        
        if success:
            print(f"圆形轨迹完成，耗时: {end_time - start_time:.2f}秒")
        else:
            print("圆形轨迹失败")
        
        # 测试6: 运动状态监控
        print("\n=== 测试6: 运动状态监控 ===")
        
        print("测试运动状态监控...")
        robot.set_smooth_execution(True)
        
        # 启动轨迹
        robot.moveJ([0.1, 0.1, 0.1, 0.0, 0.0, 0.0], speed_factor=0.3)
        
        # 监控运动状态
        print("监控运动状态...")
        for i in range(20):
            is_moving = robot.is_moving()
            print(f"  第{i+1}次检查: 运动状态 = {is_moving}")
            time.sleep(0.1)
        
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


def test_execution_modes():
    """测试不同执行模式"""
    print("\n=== 测试不同执行模式 ===")
    
    robot = create_robot(port="COM6", baudrate=1000000, debug_mode=False)
    
    try:
        if not robot.connect():
            print("连接失败")
            return False
        
        modes = ["smooth", "fast", "precise"]
        
        for mode in modes:
            print(f"\n测试 {mode} 模式...")
            robot.set_execution_mode(mode)
            
            start_time = time.time()
            robot.moveJ([0.1, 0.1, 0.1, 0.0, 0.0, 0.0], speed_factor=0.5)
            execution_time = time.time() - start_time
            
            print(f"{mode} 模式执行时间: {execution_time:.2f}秒")
        
        return True
        
    except Exception as e:
        print(f"测试执行模式失败: {e}")
        return False
    finally:
        robot.disconnect()


if __name__ == "__main__":
    print("开始轨迹平滑性测试...")
    
    # 基本功能测试
    success1 = test_trajectory_smoothness()
    
    # 执行模式测试
    success2 = test_execution_modes()
    
    if success1 and success2:
        print("\n✅ 轨迹平滑性测试通过")
    else:
        print("\n❌ 轨迹平滑性测试失败")