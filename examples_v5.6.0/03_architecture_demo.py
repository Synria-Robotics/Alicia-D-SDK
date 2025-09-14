#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例3: 架构演示 - 展示新架构的分层设计

这个示例展示了如何直接使用各层组件，了解分层架构的设计。
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'alicia_d_sdk_v5.6.0'))

from alicia_d_sdk_v5_6_0 import (
    ServoDriver, RobotModel, IKController,
    HardwareExecutor, MotionController, StateManager,
    TrajectoryPlanner, OnlineInterpolator
)
import time


def main():
    """主函数"""
    print("=== Alicia-D SDK v5.6.0 架构演示 ===")
    
    # 创建各层组件
    print("1. 创建硬件层...")
    servo_driver = ServoDriver(port="COM6", baudrate=1000000, debug_mode=True)
    
    print("2. 创建运动学层...")
    robot_model = RobotModel()
    ik_controller = IKController(robot_model)
    
    print("3. 创建执行层...")
    hardware_executor = HardwareExecutor(servo_driver)
    
    print("4. 创建控制层...")
    motion_controller = MotionController(
        servo_driver=servo_driver,
        robot_model=robot_model,
        ik_controller=ik_controller,
        hardware_executor=hardware_executor
    )
    
    print("5. 创建状态管理层...")
    state_manager = StateManager(
        servo_driver=servo_driver,
        robot_model=robot_model
    )
    
    print("6. 创建规划层...")
    trajectory_planner = TrajectoryPlanner(
        robot_model=robot_model,
        ik_controller=ik_controller
    )
    
    print("7. 创建在线插值器...")
    online_interpolator = OnlineInterpolator(servo_driver)
    
    try:
        # 连接硬件
        print("\n连接硬件...")
        if not servo_driver.connect():
            print("连接失败")
            return
        
        # 启动状态监控
        print("启动状态监控...")
        state_manager.start_monitoring()
        
        # 演示各层功能
        print("\n=== 硬件层演示 ===")
        print("读取关节角度...")
        joints = servo_driver.get_joint_angles()
        print(f"当前关节角度: {joints}")
        
        print("\n=== 运动学层演示 ===")
        if joints:
            pos, quat = robot_model.forward_kinematics(joints)
            print(f"正运动学结果: 位置={pos}, 姿态={quat}")
            
            # IK求解
            pose = list(pos) + list(quat)
            ik_result = ik_controller.solve_ik([pose], joints, output_format='as_list')
            print(f"IK求解结果: {ik_result}")
        
        print("\n=== 规划层演示 ===")
        if joints:
            target_joints = [j + 0.1 for j in joints]
            trajectory = trajectory_planner.plan_joint_trajectory(
                start_angles=joints,
                target_angles=target_joints,
                steps=50,
                interpolation_type="cubic"
            )
            print(f"规划轨迹点数: {len(trajectory)}")
        
        print("\n=== 执行层演示 ===")
        if joints and trajectory:
            print("执行轨迹...")
            hardware_executor.execute_trajectory(
                joint_trajectory=trajectory,
                progress_callback=lambda step, total, angles: print(f"执行进度: {step}/{total}"),
                completion_callback=lambda total: print(f"执行完成: {total}个点")
            )
        
        print("\n=== 控制层演示 ===")
        print("启动在线控制...")
        motion_controller.start_online_control(command_rate_hz=50)
        
        # 设置一些目标
        for i in range(5):
            target = [j + i * 0.05 for j in joints]
            motion_controller.set_online_target(joint_angles=target)
            time.sleep(1)
        
        motion_controller.stop_online_control()
        
        print("\n=== 状态管理层演示 ===")
        print("获取状态历史...")
        history = state_manager.get_state_history(max_count=10)
        print(f"状态历史记录数: {len(history)}")
        
        if history:
            latest_state = history[-1]
            print(f"最新状态: 时间={latest_state.timestamp:.3f}, 关节={latest_state.joint_angles}")
        
        print("\n=== 在线插值器演示 ===")
        print("启动在线插值器...")
        online_interpolator.start()
        
        # 设置目标
        target_joints = [j + 0.2 for j in joints] if joints else [0.1, 0.1, 0.1, 0.1, 0.1, 0.1]
        online_interpolator.set_joint_target(target_joints)
        
        # 等待到达目标
        while not online_interpolator.is_target_reached():
            time.sleep(0.1)
        
        print("目标已到达")
        online_interpolator.stop()
        
        print("\n=== 架构演示完成 ===")
        
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"\n发生错误: {e}")
    finally:
        # 清理资源
        print("\n清理资源...")
        online_interpolator.stop()
        motion_controller.stop_online_control()
        state_manager.stop_monitoring()
        servo_driver.disconnect()
        print("已断开连接")


if __name__ == "__main__":
    main()