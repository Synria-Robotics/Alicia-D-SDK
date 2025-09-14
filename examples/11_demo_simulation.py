#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例11: MuJoCo仿真演示

这个示例展示了如何使用MuJoCo仿真环境进行机械臂控制。
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'alicia_d_sdk'))

from alicia_d_sdk import create_simulation_robot
import time
import numpy as np


def demo_basic_simulation():
    """基本仿真演示"""
    print("=== MuJoCo仿真基本演示 ===")
    
    # 创建仿真机械臂
    robot = create_simulation_robot(enable_viewer=True)
    
    try:
        # 连接仿真环境
        print("正在连接仿真环境...")
        if not robot.connect():
            print("连接仿真环境失败")
            return False
        
        print("仿真环境连接成功！")
        
        # 获取初始状态
        print("\n获取初始状态...")
        joint_angles = robot.get_joint_angles()
        gripper_angle = robot.get_gripper_angle()
        end_effector_pose = robot.get_end_effector_pose()
        
        print(f"初始关节角度: {[f'{angle:.3f}' for angle in joint_angles]}")
        print(f"初始夹爪角度: {gripper_angle:.3f}")
        print(f"初始末端位姿: {[f'{pos:.3f}' for pos in end_effector_pose]}")
        
        # 基本关节运动
        print("\n=== 基本关节运动 ===")
        target_joints = [0.2, 0.1, 0.1, 0.0, 0.0, 0.0]
        print(f"目标关节角度: {target_joints}")
        
        success = robot.moveJ(
            target_joints=target_joints,
            joint_format='rad',
            speed_factor=0.5
        )
        
        if success:
            print("关节运动完成")
        else:
            print("关节运动失败")
        
        # 夹爪运动
        print("\n=== 夹爪运动 ===")
        target_gripper = 0.5
        print(f"目标夹爪角度: {target_gripper}")
        
        success = robot.moveGripper(
            target_angle=target_gripper,
            joint_format='rad',
            speed_factor=0.3
        )
        
        if success:
            print("夹爪运动完成")
        else:
            print("夹爪运动失败")
        
        # 获取运动后状态
        print("\n获取运动后状态...")
        joint_angles = robot.get_joint_angles()
        gripper_angle = robot.get_gripper_angle()
        end_effector_pose = robot.get_end_effector_pose()
        
        print(f"运动后关节角度: {[f'{angle:.3f}' for angle in joint_angles]}")
        print(f"运动后夹爪角度: {gripper_angle:.3f}")
        print(f"运动后末端位姿: {[f'{pos:.3f}' for pos in end_effector_pose]}")
        
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
        print("仿真环境已断开")


def demo_trajectory_simulation():
    """轨迹仿真演示"""
    print("\n=== 轨迹仿真演示 ===")
    
    robot = create_simulation_robot(enable_viewer=True)
    
    try:
        if not robot.connect():
            print("连接仿真环境失败")
            return False
        
        print("仿真环境连接成功！")
        
        # 多点轨迹运动
        print("\n=== 多点轨迹运动 ===")
        waypoints = [
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.2, 0.1, 0.1, 0.0, 0.0, 0.0],
            [0.3, 0.2, 0.2, 0.0, 0.0, 0.0],
            [0.2, 0.3, 0.1, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        ]
        
        print(f"执行{len(waypoints)}个轨迹点的运动...")
        
        success = robot.moveJ_waypoints(
            waypoints=waypoints,
            joint_format='rad',
            speed_factor=0.3,
            interpolation_type='cubic'
        )
        
        if success:
            print("多点轨迹运动完成")
        else:
            print("多点轨迹运动失败")
        
        return True
        
    except Exception as e:
        print(f"轨迹仿真演示失败: {e}")
        return False
    finally:
        robot.disconnect()


def demo_online_control():
    """在线控制演示"""
    print("\n=== 在线控制演示 ===")
    
    robot = create_simulation_robot(enable_viewer=True)
    
    try:
        if not robot.connect():
            print("连接仿真环境失败")
            return False
        
        print("仿真环境连接成功！")
        
        # 启动在线控制
        print("启动在线控制...")
        if not robot.start_online_control(command_rate_hz=100.0):
            print("启动在线控制失败")
            return False
        
        print("在线控制已启动")
        
        # 在线控制演示
        print("执行在线控制演示...")
        
        # 设置回调函数
        def progress_callback(current, total, joint_point):
            print(f"  进度: {current}/{total}, 当前关节角度: {[f'{angle:.3f}' for angle in joint_point]}")
        
        def completion_callback():
            print("  运动完成")
        
        robot.set_callbacks(
            progress_callback=progress_callback,
            completion_callback=completion_callback
        )
        
        # 执行几个在线控制命令
        targets = [
            [0.1, 0.1, 0.1, 0.0, 0.0, 0.0],
            [0.2, 0.2, 0.2, 0.0, 0.0, 0.0],
            [0.1, 0.2, 0.1, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        ]
        
        for i, target in enumerate(targets):
            print(f"\n执行第{i+1}个在线控制目标: {target}")
            
            success = robot.set_joint_target(target, joint_format='rad')
            if success:
                print(f"  目标{i+1}设置成功")
                time.sleep(2)  # 等待运动完成
            else:
                print(f"  目标{i+1}设置失败")
        
        # 停止在线控制
        print("\n停止在线控制...")
        robot.stop_online_control()
        print("在线控制已停止")
        
        return True
        
    except Exception as e:
        print(f"在线控制演示失败: {e}")
        return False
    finally:
        robot.disconnect()


def demo_advanced_features():
    """高级功能演示"""
    print("\n=== 高级功能演示 ===")
    
    robot = create_simulation_robot(enable_viewer=True)
    
    try:
        if not robot.connect():
            print("连接仿真环境失败")
            return False
        
        print("仿真环境连接成功！")
        
        # 设置运动参数
        print("设置运动参数...")
        robot.set_motion_parameters(
            max_velocity=1.0,  # 降低最大速度
            max_acceleration=4.0  # 降低最大加速度
        )
        
        # 设置关节限位
        print("设置关节限位...")
        custom_limits = [
            (-2.0, 2.0),  # 关节1
            (-1.0, 1.0),  # 关节2
            (-2.0, 2.0),  # 关节3
            (-2.0, 2.0),  # 关节4
            (-1.0, 1.0),  # 关节5
            (-2.0, 2.0),  # 关节6
        ]
        robot.set_joint_limits(custom_limits)
        
        # 测试限位检查
        print("测试限位检查...")
        invalid_joints = [3.0, 0.0, 0.0, 0.0, 0.0, 0.0]  # 超出限位
        success = robot.moveJ(invalid_joints, joint_format='rad')
        if not success:
            print("限位检查正常工作")
        
        # 测试有效运动
        print("测试有效运动...")
        valid_joints = [0.5, 0.3, 0.2, 0.0, 0.0, 0.0]
        success = robot.moveJ(valid_joints, joint_format='rad')
        if success:
            print("有效运动执行成功")
        
        # 重置仿真
        print("重置仿真...")
        robot.reset_simulation()
        print("仿真已重置")
        
        return True
        
    except Exception as e:
        print(f"高级功能演示失败: {e}")
        return False
    finally:
        robot.disconnect()


def main():
    """主函数"""
    print("=== Alicia-D SDK MuJoCo仿真演示 ===")
    
    # 基本仿真演示
    success1 = demo_basic_simulation()
    
    # 轨迹仿真演示
    success2 = demo_trajectory_simulation()
    
    # 在线控制演示
    success3 = demo_online_control()
    
    # 高级功能演示
    success4 = demo_advanced_features()
    
    # 总结
    print("\n=== 演示总结 ===")
    print(f"基本仿真演示: {'✅ 成功' if success1 else '❌ 失败'}")
    print(f"轨迹仿真演示: {'✅ 成功' if success2 else '❌ 失败'}")
    print(f"在线控制演示: {'✅ 成功' if success3 else '❌ 失败'}")
    print(f"高级功能演示: {'✅ 成功' if success4 else '❌ 失败'}")
    
    if all([success1, success2, success3, success4]):
        print("\n🎉 所有演示都成功完成！")
    else:
        print("\n⚠️ 部分演示失败，请检查错误信息")


if __name__ == "__main__":
    main()