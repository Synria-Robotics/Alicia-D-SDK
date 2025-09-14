#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MuJoCo集成测试脚本

用于验证MuJoCo仿真集成是否正常工作。
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'alicia_d_sdk'))

def test_imports():
    """测试导入"""
    print("=== 测试导入 ===")
    
    try:
        from alicia_d_sdk import create_simulation_robot, MuJoCoManager, RobotSimulator, SimulationInterface
        print("✅ 仿真模块导入成功")
        return True
    except ImportError as e:
        print(f"❌ 仿真模块导入失败: {e}")
        return False

def test_mujoco_installation():
    """测试MuJoCo安装"""
    print("\n=== 测试MuJoCo安装 ===")
    
    try:
        import mujoco
        print(f"✅ MuJoCo版本: {mujoco.__version__}")
        
        import mujoco_viewer
        print("✅ MuJoCo Viewer可用")
        
        return True
    except ImportError as e:
        print(f"❌ MuJoCo安装失败: {e}")
        print("请运行: pip install mujoco>=2.3.0 mujoco-python-viewer>=0.1.0")
        return False

def test_model_loading():
    """测试模型加载"""
    print("\n=== 测试模型加载 ===")
    
    try:
        from alicia_d_sdk import MuJoCoManager
        
        manager = MuJoCoManager(enable_viewer=False)
        
        if manager.load_model():
            print("✅ 模型加载成功")
            print(f"   关节数量: {len(manager.joint_names)}")
            print(f"   关节名称: {manager.joint_names}")
            return True
        else:
            print("❌ 模型加载失败")
            return False
            
    except Exception as e:
        print(f"❌ 模型加载测试失败: {e}")
        return False

def test_simulation_interface():
    """测试仿真接口"""
    print("\n=== 测试仿真接口 ===")
    
    try:
        from alicia_d_sdk import create_simulation_robot
        
        # 创建仿真机器人（不启用可视化）
        robot = create_simulation_robot(enable_viewer=False)
        
        # 测试连接
        if robot.connect():
            print("✅ 仿真环境连接成功")
            
            # 测试状态查询
            joint_angles = robot.get_joint_angles()
            gripper_angle = robot.get_gripper_angle()
            end_effector_pose = robot.get_end_effector_pose()
            
            print(f"   关节角度: {joint_angles}")
            print(f"   夹爪角度: {gripper_angle}")
            print(f"   末端位姿: {end_effector_pose}")
            
            # 测试运动控制
            success = robot.moveJ([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])
            if success:
                print("✅ 关节运动测试成功")
            else:
                print("❌ 关节运动测试失败")
            
            # 断开连接
            robot.disconnect()
            print("✅ 仿真环境断开成功")
            
            return True
        else:
            print("❌ 仿真环境连接失败")
            return False
            
    except Exception as e:
        print(f"❌ 仿真接口测试失败: {e}")
        return False

def test_api_compatibility():
    """测试API兼容性"""
    print("\n=== 测试API兼容性 ===")
    
    try:
        from alicia_d_sdk import create_simulation_robot
        
        robot = create_simulation_robot(enable_viewer=False)
        
        if robot.connect():
            # 测试所有主要API
            apis_to_test = [
                ('get_joint_angles', robot.get_joint_angles),
                ('get_gripper_angle', robot.get_gripper_angle),
                ('get_end_effector_pose', robot.get_end_effector_pose),
                ('is_moving', robot.is_moving),
                ('is_online_control_active', robot.is_online_control_active),
                ('is_emergency_stop', robot.is_emergency_stop),
                ('moveJ', lambda: robot.moveJ([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])),
                ('moveGripper', lambda: robot.moveGripper(0.5)),
                ('start_online_control', robot.start_online_control),
                ('stop_online_control', robot.stop_online_control),
            ]
            
            success_count = 0
            for api_name, api_func in apis_to_test:
                try:
                    result = api_func()
                    print(f"   ✅ {api_name}: 可用")
                    success_count += 1
                except Exception as e:
                    print(f"   ❌ {api_name}: 失败 - {e}")
            
            robot.disconnect()
            
            print(f"   API兼容性: {success_count}/{len(apis_to_test)} 通过")
            return success_count == len(apis_to_test)
        else:
            print("❌ 无法连接仿真环境")
            return False
            
    except Exception as e:
        print(f"❌ API兼容性测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("=== Alicia-D SDK MuJoCo集成测试 ===\n")
    
    tests = [
        ("导入测试", test_imports),
        ("MuJoCo安装测试", test_mujoco_installation),
        ("模型加载测试", test_model_loading),
        ("仿真接口测试", test_simulation_interface),
        ("API兼容性测试", test_api_compatibility),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"执行: {test_name}")
        print('='*50)
        
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} 执行异常: {e}")
            results.append((test_name, False))
    
    # 输出测试结果
    print(f"\n{'='*50}")
    print("测试结果总结")
    print('='*50)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\n总体结果: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试都通过了！MuJoCo集成正常工作。")
        print("\n下一步:")
        print("1. 运行 python examples/11_demo_simulation.py 查看完整演示")
        print("2. 阅读 MUJOCO_INTEGRATION_GUIDE.md 了解详细使用方法")
    else:
        print(f"\n⚠️ {total - passed} 个测试失败，请检查错误信息并修复问题。")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)