#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例7: 夹爪控制 - 展示如何进行夹爪控制

这个示例展示了如何使用gripper_control进行夹爪控制。
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'alicia_d_sdk'))

from alicia_d_sdk import create_robot
import time


def main():
    """主函数"""
    print("=== Alicia-D SDK 夹爪控制示例 ===")
    
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
        
        # 基本夹爪控制
        print("\n基本夹爪控制...")
        
        # 打开夹爪
        print("打开夹爪...")
        robot.gripper_control(command="open")
        time.sleep(2)
        
        # 关闭夹爪
        print("关闭夹爪...")
        robot.gripper_control(command="close")
        time.sleep(2)
        
        # 角度控制
        print("\n角度控制...")
        angles = [0, 25, 50, 75, 100, 75, 50, 25, 0]
        for angle in angles:
            print(f"设置夹爪角度: {angle}°")
            robot.gripper_control(angle_deg=angle, wait_for_completion=True)
            time.sleep(1)
        
        # 连续角度控制
        print("\n连续角度控制...")
        for angle in range(0, 101, 10):
            print(f"设置夹爪角度: {angle}°")
            robot.gripper_control(angle_deg=angle, wait_for_completion=False)
            time.sleep(0.5)
        
        # 反向控制
        for angle in range(100, -1, -10):
            print(f"设置夹爪角度: {angle}°")
            robot.gripper_control(angle_deg=angle, wait_for_completion=False)
            time.sleep(0.5)
        
        # 夹爪状态读取
        print("\n夹爪状态读取...")
        for i in range(5):
            gripper_angle = robot.get_gripper()
            if gripper_angle is not None:
                print(f"当前夹爪角度: {gripper_angle:.1f}°")
            time.sleep(1)
        
        # 夹爪与运动结合
        print("\n夹爪与运动结合...")
        
        # 移动到抓取位置
        print("移动到抓取位置...")
        robot.movePose([0.3, 0.1, 0.2, 0, 0, 0, 1])
        
        # 打开夹爪
        print("打开夹爪准备抓取...")
        robot.gripper_control(command="open")
        time.sleep(1)
        
        # 移动到目标位置
        print("移动到目标位置...")
        robot.movePose([0.3, 0.1, 0.15, 0, 0, 0, 1])
        
        # 关闭夹爪抓取
        print("关闭夹爪抓取...")
        robot.gripper_control(command="close")
        time.sleep(1)
        
        # 抬起
        print("抬起...")
        robot.movePose([0.3, 0.1, 0.25, 0, 0, 0, 1])
        
        # 移动到放置位置
        print("移动到放置位置...")
        robot.movePose([0.3, -0.1, 0.25, 0, 0, 0, 1])
        
        # 放下
        print("放下...")
        robot.movePose([0.3, -0.1, 0.15, 0, 0, 0, 1])
        
        # 打开夹爪释放
        print("打开夹爪释放...")
        robot.gripper_control(command="open")
        time.sleep(1)
        
        # 返回初始位置
        print("\n返回初始位置...")
        robot.moveHome()
        
        print("\n夹爪控制示例完成！")
        
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