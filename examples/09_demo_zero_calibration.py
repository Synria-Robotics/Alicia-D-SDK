#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例9: 零点校准 - 展示如何进行零点校准

这个示例展示了如何使用zero_calibration进行零点校准。
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'alicia_d_sdk'))

from alicia_d_sdk import create_robot
import time


def main():
    """主函数"""
    print("=== Alicia-D SDK 零点校准示例 ===")
    
    # 创建机械臂实例
    robot = create_robot(port="COM6", baudrate=1000000, debug_mode=True)
    
    try:
        # 连接到机械臂
        print("正在连接机械臂...")
        if not robot.connect():
            print("连接失败，请检查串口设置")
            return
        
        print("连接成功！")
        
        # 显示当前状态
        print("\n当前状态:")
        robot.print_state()
        
        # 零点校准
        print("\n开始零点校准...")
        print("注意: 零点校准会将当前位置设置为新的零点")
        print("请确保机械臂处于合适的零点位置")
        
        # 确认操作
        confirm = input("确认进行零点校准? (y/N): ")
        if confirm.lower() != 'y':
            print("取消零点校准")
            return
        
        print("正在进行零点校准...")
        robot.zero_calibration()
        print("零点校准完成！")
        
        # 显示校准后状态
        print("\n校准后状态:")
        robot.print_state()
        
        # 测试校准结果
        print("\n测试校准结果...")
        
        # 移动到初始位置（应该是零点）
        print("移动到初始位置（零点）...")
        robot.moveHome()
        
        # 读取当前位置
        current_joints = robot.get_joints()
        if current_joints:
            print(f"当前位置: {[round(j, 3) for j in current_joints]}")
            print("所有关节角度应该接近0")
        
        # 测试运动
        print("\n测试运动...")
        test_joints = [0.1, 0.1, 0.1, 0.0, 0.0, 0.0]
        print(f"移动到测试位置: {[round(j, 3) for j in test_joints]}")
        robot.moveJ(target_joints=test_joints, joint_format='rad', speed_factor=0.3)
        
        time.sleep(2)
        
        # 返回零点
        print("返回零点...")
        robot.moveHome()
        
        print("\n零点校准示例完成！")
        
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