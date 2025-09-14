#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例8: 扭矩控制 - 展示如何进行扭矩控制

这个示例展示了如何使用torque_control进行扭矩开关控制。
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'alicia_d_sdk'))

from alicia_d_sdk import create_robot
import time


def main():
    """主函数"""
    print("=== Alicia-D SDK 扭矩控制示例 ===")
    
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
        
        # 扭矩控制演示
        print("\n扭矩控制演示...")
        
        # 关闭扭矩（注意安全）
        print("关闭机械臂扭矩（注意安全）...")
        print("现在可以手动移动机械臂进行示教")
        robot.torque_control(command='off')
        
        # 等待用户确认
        input("按下回车键打开扭矩...")
        
        # 打开扭矩
        print("打开机械臂扭矩...")
        robot.torque_control(command='on')
        
        # 验证扭矩状态
        print("验证扭矩状态...")
        time.sleep(1)
        
        # 尝试移动验证扭矩已开启
        print("尝试移动验证扭矩已开启...")
        target_joints = [0.1, 0.1, 0.1, 0.0, 0.0, 0.0]
        robot.moveJ(target_joints=target_joints, joint_format='rad', speed_factor=0.3)
        
        time.sleep(2)
        
        # 返回初始位置
        print("返回初始位置...")
        robot.moveHome()
        
        # 扭矩控制与运动结合
        print("\n扭矩控制与运动结合...")
        
        # 关闭扭矩进行示教
        print("关闭扭矩进行示教...")
        robot.torque_control(command='off')
        
        print("请手动移动机械臂到目标位置，然后按回车...")
        input("按回车键继续...")
        
        # 记录当前位置
        current_joints = robot.get_joints()
        if current_joints:
            print(f"记录的位置: {[round(j, 3) for j in current_joints]}")
        
        # 打开扭矩
        print("打开扭矩...")
        robot.torque_control(command='on')
        
        # 移动到记录的位置
        if current_joints:
            print("移动到记录的位置...")
            robot.moveJ(target_joints=current_joints, joint_format='rad', speed_factor=0.5)
        
        time.sleep(2)
        
        # 返回初始位置
        print("\n返回初始位置...")
        robot.moveHome()
        
        print("\n扭矩控制示例完成！")
        
    except KeyboardInterrupt:
        print("\n用户中断")
        # 确保扭矩开启
        robot.torque_control(command='on')
    except Exception as e:
        print(f"\n发生错误: {e}")
        # 确保扭矩开启
        robot.torque_control(command='on')
    finally:
        # 确保扭矩开启
        robot.torque_control(command='on')
        # 断开连接
        robot.disconnect()
        print("已断开连接")


if __name__ == "__main__":
    main()