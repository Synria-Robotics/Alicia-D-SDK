"""
Module: Trajectory Tester for Alicia-D
供后端集成的轨迹老化/稳定性测试模块。

Features:
- 后台线程运行，不阻塞主程序
- 支持有限循环次数配置
- 实时记录温度、错误、进度
- 线程安全的状态查询接口

Usage:
    from 3_trajectory_test_module import TrajectoryTester
    import alicia_d_sdk

    robot = alicia_d_sdk.create_robot(port="COMx")
    tester = TrajectoryTester(robot)
    
    # 开始测试 (配置 10 次循环)
    tester.start(cycles=10, speed=100)
    
    # 查询状态
    while tester.is_running():
        print(tester.get_status())
        time.sleep(1)
"""

import threading
import time
import numpy as np
from datetime import datetime
from collections import deque
import logging

# 配置 logging，如果后端已有 logging 配置，这里可以去掉
logging.basicConfig(level=logging.INFO, format='[TestModule] %(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TrajectoryTester")

class TrajectoryTester:
    def __init__(self, robot_instance):
        """
        初始化测试器
        :param robot_instance: 已经初始化的 ALicia-D 机器人实例
        """
        self.robot = robot_instance
        self._running = False
        self._test_thread = None
        self._control_thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        
        # 默认测试轨迹 (8 points, complex movements, no zeros, backward reach)
        self.default_waypoints = [
            # 1. Home-Ready (Non-zero start)
            {"name": "Home-Ready",   "coords": [0.1, -10.5, 20.5, 0.1, 10.5, 0.1]},
            # 2. Left-Forward
            {"name": "Left-Fwd",     "coords": [-40.5, -20.5, 50.5, -30.5, -20.5, -30.5]},
            # 3. Left-Extreme (Side)
            {"name": "Left-Side",    "coords": [-85.5, -40.5, 90.5, -80.5, -30.5, -60.5]},
            # 4. Left-Backward (New: J1=-130)
            {"name": "Left-Back",    "coords": [-130.5, -30.5, 80.5, -60.5, -30.5, -45.5]},
            # 5. Right-Backward (New: J1=130)
            {"name": "Right-Back",   "coords": [130.5, 30.5, 80.5, 60.5, 30.5, 45.5]},
            # 6. Right-Extreme (Side)
            {"name": "Right-Side",   "coords": [85.5, 40.5, -15.5, 80.5, 30.5, 60.5]},
            # 7. Right-Forward
            {"name": "Right-Fwd",    "coords": [40.5, 20.5, 40.5, 30.5, 20.5, 30.5]},
            # 8. Complex Recovery
            {"name": "Recovery",     "coords": [-15.5, 10.5, -10.5, -20.5, 15.5, -10.5]},
        ]
        
        # 实时控制变量 (Shared between Control Thread and Test Logic)
        self._target_joints = [0.0] * 6
        self._target_speed = 100.0
        self._gripper_val = 1000.0
        self._gripper_dir = -1 # -1: Closing, 1: Opening
        
        # 状态数据
        self.status = {
            "is_running": False,
            "current_cycle": 0,
            "total_cycles_target": 0,
            "start_time": None,
            "end_time": None,
            "last_error": None,
            "current_stage": "Idle",
            "temperatures": [], 
            "completed": False,
            "error_count": 0
        }
        self.history_errors = []

    def start(self, cycles: int = 4, speed: float = 100.0, waypoints: list = None):
        if self._running:
            logger.warning("Test is already running.")
            return

        self._stop_event.clear()
        self.status.update({
            "is_running": True,
            "current_cycle": 0,
            "total_cycles_target": cycles,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "last_error": None,
            "current_stage": "Initializing",
            "completed": False,
            "temperatures": [],
            "error_count": 0
        })
        self.history_errors = []
        
        target_waypoints = list(waypoints if waypoints else self.default_waypoints)
        
        # 启动控制线程 (负责 20Hz 发送指令，实现夹爪和关节同步动)
        self._control_thread = threading.Thread(target=self._control_loop, daemon=True)
        self._control_thread.start()
            
        # 启动测试逻辑线程 (负责切换路点)
        self._test_thread = threading.Thread(
            target=self._run_test_logic,
            args=(cycles, speed, target_waypoints),
            daemon=True
        )
        self._test_thread.start()
        self._running = True
        logger.info(f"Test started: {cycles} cycles, speed {speed}")

    def stop(self):
        if self._running:
            logger.info("Stopping test...")
            self._stop_event.set()

    def is_running(self):
        return self._running

    def get_status(self):
        with self._lock:
            return self.status.copy()

    def get_result(self):
        with self._lock:
            return {
                "completed": self.status["completed"],
                "total_cycles_configured": self.status["total_cycles_target"],
                "cycles_finished": self.status["current_cycle"],
                "error_count": self.status.get("error_count", 0),
                "last_temperature": self.status["temperatures"],
                "errors": list(self.history_errors),
                "start_time": self.status["start_time"],
                "end_time": self.status.get("end_time"),
                "passed": self.status["completed"] and self.status.get("error_count", 0) == 0
            }

    def _update_status(self, **kwargs):
        with self._lock:
            self.status.update(kwargs)

    def _record_error(self, error_msg):
        full_msg = f"{datetime.now().isoformat()}: {error_msg}"
        logger.error(full_msg)
        with self._lock:
            self.status["last_error"] = full_msg
            self.status["error_count"] = self.status.get("error_count", 0) + 1
            self.history_errors.append(full_msg)

    def _control_loop(self):
        """高频发送指令线程 (25Hz) - 实现夹爪不断开合 + 关节运动"""
        while self.status["is_running"]:
            if self._stop_event.is_set():
                break
                
            # 1. 更新夹爪逻辑 (模拟不断闭合/张开)
            # 每次步进 20 (约 1-2秒完成一次开合)
            step = 30 
            self._gripper_val += step * self._gripper_dir
            if self._gripper_val <= 0:
                self._gripper_val = 0
                self._gripper_dir = 1 # 反向张开
            elif self._gripper_val >= 1000:
                self._gripper_val = 1000
                self._gripper_dir = -1 # 反向闭合
            
            # 2. 发送组合指令
            try:
                # 注意：这里使用非阻塞发送
                # _target_joints 由 Test Logic 线程更新
                self.robot.set_robot_target(
                    target_joints=self._target_joints,
                    gripper_value=int(self._gripper_val),
                    joint_format='deg',
                    speed_deg_s=self._target_speed, 
                    wait_for_completion=False 
                )
            except Exception:
                pass # 忽略发送错误，避免刷屏
                
            time.sleep(0.04) # ~25Hz

    def _run_test_logic(self, total_cycles, speed, waypoints):
        """测试流程控制线程"""
        try:
            if not self.robot.is_connected():
                 if not self.robot.connect():
                     raise Exception("Failed to connect to robot")

            # 初始数据
            self._target_speed = speed
            self._target_joints = [0.0] * 6

            # 归位阶段
            self._update_status(current_stage="Homing")
            # 此时 control_loop 已经在跑了，所以只需要设置 target_joints 即可
            # 但为了确保归位完成，我们需要手动 check 
            self._wait_for_joints([0.0]*6)

            for i in range(total_cycles):
                if self._stop_event.is_set(): break

                self._update_status(current_cycle=i + 1, current_stage=f"Cycle {i+1} Set Started")
                
                for wp in waypoints:
                    if self._stop_event.is_set(): break
                    name = wp.get("name", "Unknown")
                    coords = wp["coords"]
                    
                    self._update_status(current_stage=f"Moving to {name}")
                    
                    # 更新控制目标，Control Loop 会自动执行
                    self._target_joints = coords
                    
                    # 等待到达 (替代 wait_for_completion=True)
                    if not self._wait_for_joints(coords):
                        self._record_error(f"Timeout moving to {name}")
                    
                    # 读取温度
                    try:
                        temps = self.robot.get_temperature()
                        if temps: self._update_status(temperatures=temps)
                    except: pass

            self._update_status(current_stage="Finishing", completed=True)

        except Exception as e:
            self._record_error(f"Test logic error: {e}")
            self._update_status(current_stage="Error", completed=False)
        finally:
            # 停止测试
            self._running = False #这会停止 Control Loop
            self._update_status(is_running=False, end_time=datetime.now().isoformat())
            
            # 最后一步：确保夹爪张开到 1000
            # 等待 Control Loop 退出
            if self._control_thread:
                self._control_thread.join(timeout=1.0)
            
            logger.info("Finalizing: Opening Gripper to 1000")
            try:
                # 发送最终指令 (此时 Control Loop 已停，可以直接调用阻塞指令)
                self.robot.set_robot_target(
                    target_joints=[0.0]*6, # 回零
                    gripper_value=1000,
                    joint_format='deg',
                    speed_deg_s=speed,
                    wait_for_completion=True
                )
            except Exception as e:
                logger.error(f"Final open failed: {e}")

    def _wait_for_joints(self, target_deg, tolerance=2.0, timeout=10.0):
        """手动等待关节到达 (因为 set_robot_target 被 Control Loop 占用了)"""
        start = time.time()
        while time.time() - start < timeout:
            if self._stop_event.is_set(): return False
            try:
                current = self.robot.get_joints() # rad
                if current:
                    curr_deg = [np.rad2deg(x) for x in current]
                    # 检查 6 个关节是否都在误差范围内
                    diffs = [abs(c - t) for c, t in zip(curr_deg, target_deg)]
                    if all(d < tolerance for d in diffs):
                        time.sleep(0.2) # 稳定一下
                        return True
            except: pass
            time.sleep(0.1)
        return False


# ==========================================
# 独立运行入口 (CLI Mode)
# ==========================================
if __name__ == "__main__":
    import argparse
    import alicia_d_sdk
    import sys

    # 简单的命令行参数解析
    parser = argparse.ArgumentParser(description="Alicia-D Trajectory Tester Module")
    parser.add_argument('--port', type=str, default="", help="Serial port")
    parser.add_argument('--cycles', type=int, default=1, help="Number of test cycles")
    parser.add_argument('--speed', type=float, default=100.0, help="Movement speed (deg/s)")
    args = parser.parse_args()

    print("--- Initializing Robot ---")
    robot = alicia_d_sdk.create_robot(port=args.port)
    
    if not robot.is_connected():
        print("Connecting...")
        if not robot.connect():
            print("Failed to connect!")
            sys.exit(1)

    print(f"--- Starting Tester Service (Cycles: {args.cycles}) ---")
    tester = TrajectoryTester(robot)
    tester.start(cycles=args.cycles, speed=args.speed)

    try:
        while tester.is_running():
            status = tester.get_status()
            
            # 简单的单行打印状态
            cycle_str = f"{status['current_cycle']}/{status['total_cycles_target']}"
            stage = status['current_stage']
            temps = status.get('temperatures', [])
            error_count = status.get('error_count', 0)
            temp_str = f"MaxTemp: {max(temps)}°C" if temps else "Temp: N/A"
            error_str = f"| Errors: {error_count}" if error_count > 0 else ""
            
            print(f"\rStatus: [{stage}] | Cycle: {cycle_str} | {temp_str} {error_str}     ", end="", flush=True)
            time.sleep(0.5)
            
        print("\n--- Test Finished ---")
        result = tester.get_result()
        print("Final Result Summary:")
        print(f"  Passed: {result['passed']}")
        print(f"  Completed: {result['completed']}")
        print(f"  Errors: {result['error_count']}")
        if result['error_count'] > 0:
            print(f"  Last Error: {result['errors'][-1]}")

    except KeyboardInterrupt:
        print("\nStopping...")
        tester.stop()
        # 等待线程结束
        time.sleep(1)
        
    robot.disconnect()
