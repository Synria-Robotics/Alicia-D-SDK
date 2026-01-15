"""
Demo: Multi-Joint Loop Test with Recorded Trajectory (my_demo)
基于2_demo_multi_joint_loop.py，使用09_demo录制的my_demo轨迹

Usage:
python 2_demo_my_demo_loop.py
python 2_demo_my_demo_loop.py --loops 5
python 2_demo_my_demo_loop.py --motion my_demo --loops 10 --speed 200
"""

import argparse
import csv
import json
import threading
import time
import os
from datetime import datetime
from collections import deque
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

import alicia_d_sdk


class TelemetryRecorder:
    """
    遥测数据记录器
    
    功能：
    - 后台线程实时记录机器人的目标位置、实际位置、温度等数据
    - 数据存储到CSV文件用于后续分析
    - 保留最近N个样本用于实时绘图
    - 过热保护：检测舵机温度是否超过安全阈值
    
    参数：
        robot: 机器人实例
        log_path: CSV日志文件保存路径
        poll_interval: 关节位置读取间隔(秒)，默认0.2s
        temp_interval: 温度读取间隔(秒)，默认3.0s
        temp_timeout: 温度读取超时(秒)，默认1.5s
        temp_retries: 温度读取重试次数，默认2次
        temp_backoff_max: 温度读取失败后最大退避时间(秒)
        max_samples_for_plot: 绘图用的最大样本数，超过后丢弃旧数据
    """

    def __init__(
        self,
        robot,
        log_path: Path,
        poll_interval: float = 0.2,
        temp_interval: float = 3.0,
        temp_timeout: float = 1.5,
        temp_retries: int = 2,
        temp_backoff_max: float = 8.0,
        max_samples_for_plot: int = 2000,
    ):
        self.robot = robot
        self.log_path = log_path
        self.poll_interval = poll_interval
        self.temp_interval = temp_interval
        self.temp_timeout = temp_timeout
        self.temp_retries = max(1, temp_retries)
        self.temp_backoff_max = temp_backoff_max
        self.records = deque(maxlen=max_samples_for_plot)

        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._csv_file = None
        self._csv_writer = None

        self._current_target_deg = [0.0] * 6
        self._current_phase = ""
        self._current_loop_idx = 0
        self._last_temperature = []
        self._temp_backoff = temp_interval
        self._temp_failures = 0
        
        # 过热保护相关
        self._overheat_threshold = 85.0  # 过热阈值
        self._overheat_confirm_count = 10  # 连续确认次数
        self._overheat_counters = {}  # 每个舵机的过热计数器 {舵机索引: 连续过热次数}
        self._overheat_triggered = False  # 是否已触发过热保护
        self._overheat_servo_id = None  # 触发过热的舵机ID

    def start(self):
        """
        启动遥测记录器
        
        作用：
        1. 创建并打开CSV文件
        2. 启动后台记录线程，开始定期读取机器人状态
        """
        self._running = True
        self._csv_file = open(self.log_path, "w", newline="", buffering=1)
        fieldnames = [
            "timestamp",
            "loop_idx",
            "phase",
            "target_joints_deg",
            "actual_joints_deg",
            "temperatures",
            "run_status",
        ]
        self._csv_writer = csv.DictWriter(self._csv_file, fieldnames=fieldnames)
        self._csv_writer.writeheader()

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """
        停止遥测记录器
        
        作用：
        1. 停止后台线程
        2. 关闭CSV文件
        """
        self._running = False
        if self._thread:
            self._thread.join()
        if self._csv_file:
            self._csv_file.close()

    def set_target(self, joints_deg, phase: str = "", loop_idx: int = 0):
        """
        设置当前目标位置（由主程序调用）
        
        参数：
            joints_deg: 6个关节的目标角度(度)
            phase: 当前阶段名称，如 "Trajectory 100/759"
            loop_idx: 当前循环索引
        """
        with self._lock:
            self._current_target_deg = list(joints_deg)
            self._current_phase = phase
            self._current_loop_idx = loop_idx

    def get_recent_records(self):
        """
        获取最近的遥测记录（用于绘图）
        
        返回：
            list: 最近max_samples_for_plot条记录的列表
        """
        with self._lock:
            return list(self.records)
    
    def check_overheat(self):
        """检查是否触发过热保护，返回 (是否过热, 过热舵机ID)"""
        with self._lock:
            return self._overheat_triggered, self._overheat_servo_id

    def _run(self):
        next_temp_time = 0.0
        while self._running:
            now = time.time()
            temps = None

            if now >= next_temp_time:
                for attempt in range(self.temp_retries):
                    try:
                        temps = self.robot.get_robot_state(info_type="temperature", timeout=self.temp_timeout)
                        if temps is not None:
                            self._last_temperature = temps
                            self._temp_failures = 0
                            self._temp_backoff = self.temp_interval
                            break
                    except Exception as exc:
                        if self._temp_failures == 0:
                            print(f"[Telemetry] Temperature read failed: {exc}")
                        self._temp_failures += 1
                        time.sleep(0.05)

                if temps is None:
                    self._temp_backoff = min(self.temp_backoff_max, self._temp_backoff * 1.6)
                else:
                    self._temp_backoff = self.temp_interval

                next_temp_time = now + self._temp_backoff

            try:
                joints = self.robot.get_robot_state(info_type="joint")
            except Exception as exc:
                print(f"[Telemetry] Read failed: {exc}")
                time.sleep(self.poll_interval)
                continue

            if joints is None:
                time.sleep(self.poll_interval)
                continue

            actual_deg = [np.rad2deg(x) for x in joints]

            with self._lock:
                target_deg = list(self._current_target_deg)
                phase = self._current_phase
                loop_idx = self._current_loop_idx

            temps_to_use = temps if temps is not None else self._last_temperature
            
            # 过热保护检测
            if temps_to_use and not self._overheat_triggered:
                for idx, temp in enumerate(temps_to_use):
                    if temp >= self._overheat_threshold:
                        self._overheat_counters[idx] = self._overheat_counters.get(idx, 0) + 1
                        if self._overheat_counters[idx] >= self._overheat_confirm_count:
                            with self._lock:
                                self._overheat_triggered = True
                                self._overheat_servo_id = idx + 1  # 舵机编号从1开始
                            print(f"\n[过热警告] 舵机 T{idx + 1} 连续 {self._overheat_confirm_count} 次超过 {self._overheat_threshold}°C!")
                    else:
                        # 温度恢复正常，重置计数器
                        self._overheat_counters[idx] = 0

            record = {
                "timestamp": now,
                "loop_idx": loop_idx,
                "phase": phase,
                "target_joints_deg": target_deg,
                "actual_joints_deg": actual_deg,
                "temperatures": temps_to_use,
                "run_status": "Running",
            }

            with self._lock:
                self.records.append(record)

            if self._csv_writer:
                self._csv_writer.writerow(
                    {
                        "timestamp": f"{now:.3f}",
                        "loop_idx": loop_idx,
                        "phase": phase,
                        "target_joints_deg": ";".join(f"{v:.2f}" for v in target_deg),
                        "actual_joints_deg": ";".join(f"{v:.2f}" for v in actual_deg),
                        "temperatures": "" if not temps_to_use else ";".join(f"{t:.1f}" for t in temps_to_use),
                        "run_status": "Running",
                    }
                )

            time.sleep(self.poll_interval)


class RealtimePlotter:
    """
    实时绘图器
    
    功能：
    - 实时绘制目标关节角度、实际关节角度、温度曲线
    - 显示当前最高温度及对应舵机
    - 支持保存图片到文件
    
    参数：
        recorder: TelemetryRecorder实例，用于获取数据
        update_interval: 图表更新间隔(秒)，默认0.5s
    """

    def __init__(self, recorder: TelemetryRecorder, update_interval: float = 0.5):
        self.recorder = recorder
        self.update_interval = update_interval
        self._start_time = time.time()
        self._last_update = 0.0

        self._fig, (self._ax_target, self._ax_actual, self._ax_temp) = plt.subplots(3, 1, figsize=(10, 10))
        self._fig.suptitle("Alicia-D Telemetry (Target vs Actual vs Temp)")

        colors = plt.cm.tab10(np.linspace(0, 1, 6))
        
        # 1. Target Plot
        self._lines_target = []
        for idx in range(6):
            target_line, = self._ax_target.plot(
                [], [], color=colors[idx], linestyle="--", alpha=0.8, label=f"J{idx + 1} target"
            )
            self._lines_target.append(target_line)
        self._ax_target.set_ylabel("Target Angle (deg)")
        self._ax_target.grid(True, alpha=0.2)
        self._ax_target.legend(ncol=6, fontsize=8, loc="upper right")

        # 2. Actual Plot
        self._lines_actual = []
        for idx in range(6):
            actual_line, = self._ax_actual.plot(
                [], [], color=colors[idx], linestyle="-", label=f"J{idx + 1} actual"
            )
            self._lines_actual.append(actual_line)
        self._ax_actual.set_ylabel("Actual Angle (deg)")
        self._ax_actual.grid(True, alpha=0.2)

        # 3. Temp Plot
        self._temp_lines = []
        self._ax_temp.set_ylabel("Temperature (°C)")
        self._ax_temp.set_xlabel("Time (s)")
        self._ax_temp.grid(True, alpha=0.2)
        
        # 最高温度文本框
        self._max_temp_text = self._ax_temp.text(
            1.02, 0.5, "",
            transform=self._ax_temp.transAxes,
            fontsize=10,
            verticalalignment='center',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', edgecolor='orange', alpha=0.9)
        )

    def start(self):
        """
        启动绘图器
        
        作用：开启交互模式并显示图表窗口
        """
        plt.ion()
        self._fig.tight_layout(rect=[0, 0, 0.88, 1])  # 右侧留空间给最高温度文本框
        self._fig.show()

    def save(self, path):
        """
        保存图表到文件
        
        参数：
            path: 图片保存路径 (如 xxx_plot.png)
        """
        try:
            self._fig.savefig(path)
            print(f"[Plotter] Saved plot to {path}")
        except Exception as e:
            print(f"[Plotter] Failed to save plot: {e}")

    def stop(self, keep_open=False):
        """
        停止绘图器
        
        参数：
            keep_open: 是否保持图表窗口打开
                - True: 保持打开，程序结束后图片不关闭
                - False: 关闭图表窗口
        """
        plt.ioff()  # 关闭交互模式
        if not keep_open:
            plt.close(self._fig)

    def update(self):
        """
        更新图表显示
        
        作用：
        1. 从记录器获取最新数据
        2. 更新目标/实际关节角度曲线
        3. 更新温度曲线
        4. 计算并显示最高温度(使用滑动窗口中位数过滤异常值)
        
        注意：此方法有频率限制，不会每次调用都更新
        """
        now = time.time()
        if now - self._last_update < self.update_interval:
            return
        self._last_update = now

        data = self.recorder.get_recent_records()
        if not data:
            return
        
        # Update Loop Count in Title
        last_item = data[-1]
        current_loop_idx = last_item.get("loop_idx", 0)
        self._fig.suptitle(f"Alicia-D Telemetry - Current Loop: {current_loop_idx}")

        times = np.array([item["timestamp"] - self._start_time for item in data])
        actual = np.array([item["actual_joints_deg"] for item in data])
        target = np.array([item["target_joints_deg"] for item in data])

        if actual.ndim == 2 and target.ndim == 2:
            for idx in range(6):
                self._lines_target[idx].set_data(times, target[:, idx])
                self._lines_actual[idx].set_data(times, actual[:, idx])
            
            self._ax_target.relim()
            self._ax_target.autoscale_view()
            self._ax_actual.relim()
            self._ax_actual.autoscale_view()

        temp_samples = [item["temperatures"] for item in data if item["temperatures"]]
        if temp_samples:
            temp_array = np.array(temp_samples)
            temp_time = times[-temp_array.shape[0]:]

            if not self._temp_lines:
                for idx in range(temp_array.shape[1]):
                    (line,) = self._ax_temp.plot([], [], label=f"T{idx + 1}")
                    self._temp_lines.append(line)
                self._ax_temp.legend(ncol=6, fontsize=8, loc="upper right")

            for idx, line in enumerate(self._temp_lines):
                line.set_data(temp_time, temp_array[:, idx])
            
            # 计算并更新最高温度信息（使用滑动窗口中位数过滤瞬间异常）
            # 取最近5个样本的中位数作为稳定温度
            WINDOW_SIZE = 5
            if temp_array.shape[0] >= WINDOW_SIZE:
                # 对每个舵机计算最近WINDOW_SIZE个样本的中位数
                recent_temps = temp_array[-WINDOW_SIZE:, :]
                median_temps = np.median(recent_temps, axis=0)
                
                # 找出稳定的最高温度
                max_idx = np.argmax(median_temps)
                max_temp_value = median_temps[max_idx]
                self._max_temp_text.set_text(f"the highest temp: \nT{max_idx + 1}: {max_temp_value:.1f}°C")

            self._ax_temp.relim()
            self._ax_temp.autoscale_view()

        self._fig.canvas.draw_idle()
        self._fig.canvas.flush_events()
        plt.pause(0.001)


def load_trajectory(motion_name: str) -> list:
    """
    加载录制的轨迹数据
    
    参数：
        motion_name: 轨迹名称（对应文件夹名，如 "my_demo_action"）
    
    返回：
        list: 轨迹点列表，每个点包含 {"q": [关节6个弧度值]}
        None: 如果找不到轨迹文件
    
    说明：
        会在多个路径中搜索 joint_traj.json 文件
    """
    # 获取当前脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    possible_paths = [
        # benchmark/my_demo 目录（脚本同级目录）
        os.path.join(script_dir, motion_name, "joint_traj.json"),
        # 直接在benchmark目录
        os.path.join("benchmark", motion_name, "joint_traj.json"),
        # 相对于examples目录
        os.path.join("Alicia-D-SDK", "examples", "benchmark", motion_name, "joint_traj.json"),
        # 旧的example_motions路径（兼容）
        os.path.join("example_motions", motion_name, "joint_traj.json"),
        os.path.join(script_dir, "..", "example_motions", motion_name, "joint_traj.json"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"[加载] 找到轨迹文件: {path}")
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"[加载] 轨迹包含 {len(data)} 个点")
            return data
    
    # 如果都找不到，显示错误
    print(f"[错误] 找不到轨迹 '{motion_name}'")
    print("尝试过的路径:")
    for path in possible_paths:
        print(f"  - {path}")
    return None


def wait_for_serial_port(robot, check_interval=1.0):
    """
    等待串口重新连接
    
    参数：
        robot: 机器人实例
        check_interval: 检查间隔(秒)，默认1.0s
    
    返回：
        True: 重新连接成功
    
    说明：
        此函数会无限循环，直到串口连接成功
    """
    print("\n[等待] 等待串口重新连接...")
    while True:
        try:
            # 尝试连接
            if robot.connect():
                print("[连接] 串口已连接，等待2秒后继续...")
                time.sleep(2)
                return True
        except Exception as e:
            pass
        
        print(".", end="", flush=True)
        time.sleep(check_interval)


def try_return_to_zero(robot, speed, timeout=5.0):
    """
    尝试将机器人回到零点位置
    
    参数：
        robot: 机器人实例
        speed: 移动速度(deg/s)
        timeout: 超时时间(秒)，默认5.0s
    
    返回：
        True: 成功回到零点
        False: 回零失败(串口断开等)
    
    说明：
        用于程序结束或异常时的安全回零
    """
    pose_zero = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    try:
        print("\n[安全] 尝试回到零点...")
        robot.set_robot_state(
            target_joints=pose_zero,
            joint_format='deg',
            speed_deg_s=50,  # 回零速度固定50 deg/s
            wait_for_completion=True
        )
        print("[安全] 已回到零点")
        return True
    except Exception as e:
        print(f"[警告] 回零点失败: {e}")
        return False


def main(args):
    """
    主程序入口
    
    功能：
    1. 加载录制的轨迹数据(my_demo)
    2. 循环播放轨迹并每次回到零点
    3. 实时记录遥测数据并绘图
    4. 支持串口断开重连
    5. 过热保护：舵机连续10次超过85°C时缓慢回零并停止
    
    参数 (args):
        port: 串口号，空字符串表示自动检测
        motion: 轨迹名称，默认 "my_demo_action"
        loops: 循环次数，默认 9999999999
        speed: 运动速度(deg/s)，默认 200
    """
    
    # Motion Parameters
    speed = args.speed  # deg/s
    loop_count = args.loops
    motion_name = args.motion
    
    # 加载录制的轨迹
    trajectory = load_trajectory(motion_name)
    if trajectory is None:
        print("无法加载轨迹，退出")
        return
    
    if len(trajectory) < 2:
        print("轨迹点数不足，至少需要2个点")
        return
    
    # 从轨迹中提取起点和终点（弧度转角度）
    start_point = trajectory[0]
    end_point = trajectory[-1]
    
    pose_a = [np.rad2deg(x) for x in start_point["q"]]
    pose_b = [np.rad2deg(x) for x in end_point["q"]]
    pose_zero = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    
    print(f"轨迹起点 (Pose A): {[f'{x:.1f}' for x in pose_a]}")
    print(f"轨迹终点 (Pose B): {[f'{x:.1f}' for x in pose_b]}")

    recorder = None
    plotter = None
    robot = None
    current_loop = 0  # 当前循环索引
    last_overheat_servo = None  # 上一次循环检测到过热的舵机ID
    
    # 外层循环：处理断开重连
    while True:
        try:
            # Initialize robot instance
            robot = alicia_d_sdk.create_robot(port=args.port)
            
            # Connect to robot
            if not robot.connect():
                print("✗ Connection failed. Waiting for serial port...")
                time.sleep(2)
                continue
                
            print(f"\nStarting Multi-Joint Loop Test with {motion_name}: {loop_count} iterations")
            print(f"当前从第 {current_loop + 1} 个循环开始")
            
            # Create log directory with date structure
            now = datetime.now()
            date_str = now.strftime("%Y%m%d")
            time_str = now.strftime("%H%M%S")
            
            # 获取脚本所在目录，在同级创建demo_log
            script_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = Path(script_dir) / "demo_log" / date_str
            base_dir.mkdir(parents=True, exist_ok=True)
            
            log_path = base_dir / f"{time_str}_data.csv"
            plot_path = base_dir / f"{time_str}_plot.png"
            
            print(f"Logging data to: {log_path}")
            
            # Telemetry recorder and realtime plotter
            if recorder is None:
                recorder = TelemetryRecorder(
                    robot,
                    log_path=log_path,
                    poll_interval=0.2,
                    temp_interval=2.0,
                    max_samples_for_plot=2500,
                )
                recorder.set_target(pose_zero, phase="Init Zero")
                recorder.start()
            else:
                # 更新recorder的robot引用并重启后台线程
                recorder.robot = robot
                if not recorder._running:
                    recorder._running = True
                    recorder._thread = threading.Thread(target=recorder._run, daemon=True)
                    recorder._thread.start()
                    print("[Telemetry] Recorder resumed")

            if plotter is None:
                plotter = RealtimePlotter(recorder, update_interval=0.5)
                plotter.start()

            # Initial safe move to zero
            print("Moving to start position (Zero)...")
            robot.set_robot_state(
                target_joints=pose_zero,
                joint_format='deg',
                speed_deg_s=speed,
                wait_for_completion=True
            )
            time.sleep(1)

            # 内层循环：执行轨迹
            for i in range(current_loop, loop_count):
                print(f"--- Loop {i+1}/{loop_count} ---")
                
                try:
                    # --- 正向播放轨迹（极简化，减少开销实现丝滑回放）---
                    print(f"  播放轨迹: {len(trajectory)} 个点")
                    for j, point in enumerate(trajectory):
                        # 记录目标值（低开销，不影响性能）
                        joints_deg = [np.rad2deg(x) for x in point["q"]]
                        recorder.set_target(joints_deg, phase=f"Traj", loop_idx=i+1)
                        
                        # 发送命令
                        robot.set_robot_state(
                            target_joints=point["q"],
                            joint_format='rad',
                            speed_deg_s=speed,
                            tolerance=0.3,
                            wait_for_completion=True
                        )
                        
                        # 每200个点打印一次进度（极低开销）
                        if j % 200 == 0:
                            print(f"    [{j}/{len(trajectory)}]", end="\r")
                    
                    print(f"    [{len(trajectory)}/{len(trajectory)}] 完成")
                    
                    # 轨迹播放完成后更新一次绘图
                    time.sleep(0.3)
                    if plotter:
                        plotter.update()
                    
                    # 循环结束后检查过热（连续2次循环同一舵机超过85°C才触发）
                    if recorder:
                        records = recorder.get_recent_records()
                        if records:
                            # 获取最近的温度记录
                            last_temps = records[-1].get("temperatures", [])
                            if last_temps:
                                # 检查哪个舵机超过85度
                                current_overheat_servo = None
                                for idx, temp in enumerate(last_temps):
                                    if temp >= 85.0:
                                        current_overheat_servo = idx + 1
                                        print(f"  [温度警告] 舵机 T{idx + 1} 温度: {temp:.1f}°C")
                                        break
                                
                                # 如果连续两次循环同一舵机超过85度，触发过热保护
                                if current_overheat_servo and current_overheat_servo == last_overheat_servo:
                                    print(f"\n[过热保护] 舵机 T{current_overheat_servo} 连续2次循环超过 85°C，触发安全停止!")
                                    print("[安全] 正在缓慢回到零点...")
                                    robot.set_robot_state(
                                        target_joints=pose_zero,
                                        joint_format='deg',
                                        speed_deg_s=50,
                                        wait_for_completion=True
                                    )
                                    raise Exception(f"OVERHEAT_STOP:T{current_overheat_servo}")
                                
                                # 更新上一次过热舵机记录
                                last_overheat_servo = current_overheat_servo
                    
                    # --- Return Phase (Zero) ---
                    print("  Returning to Zero...")
                    recorder.set_target(pose_zero, phase="Return Zero", loop_idx=i+1)
                    robot.set_robot_state(
                        target_joints=pose_zero,
                        joint_format='deg',
                        speed_deg_s=50,  # 回零速度固定50 deg/s
                        wait_for_completion=True
                    )
                    
                    time.sleep(1)
                    if plotter:
                        plotter.update()
                    
                    # 更新当前循环索引
                    current_loop = i + 1
                    
                except (PermissionError, OSError, Exception) as e:
                    error_msg = str(e)
                    
                    # 检测过热停止
                    if "OVERHEAT_STOP" in error_msg:
                        servo_info = error_msg.split(":")[-1]
                        print(f"\n[程序结束] 因舵机 {servo_info} 过热保护停止运行")
                        # 设置标志位跳出所有循环
                        raise SystemExit(f"过热保护停止: {servo_info}")
                    
                    error_msg_lower = error_msg.lower()
                    # 检测串口断开错误
                    if "permission" in error_msg_lower or "拒绝访问" in error_msg_lower or "serial" in error_msg_lower or "write" in error_msg_lower:
                        print(f"\n[断开] 检测到串口断开: {e}")
                        
                        # 尝试回到零点
                        print("[安全] 尝试回到零点...")
                        try_return_to_zero(robot, speed)
                        
                        # 暂停recorder（不销毁，避免重建时plotter引用丢失）
                        if recorder:
                            recorder._running = False
                        
                        # 尝试断开连接
                        try:
                            robot.disconnect()
                        except:
                            pass
                        
                        # 等待重新连接
                        print("[等待] 请重新连接USB，2秒后尝试重连...")
                        time.sleep(2)
                        
                        # 跳出内层循环，回到外层循环等待重连
                        break
                    else:
                        # 其他错误，继续抛出
                        raise
            else:
                # 所有循环正常完成
                print("\n✓ 所有循环已完成!")
                break

        except KeyboardInterrupt:
            print("\n✗ Processing interrupted by user")
            # 尝试回零点
            if robot:
                try_return_to_zero(robot, speed)
            break
            
        except Exception as e:
            error_msg = str(e).lower()
            # 检测串口断开错误
            if "permission" in error_msg or "拒绝访问" in error_msg or "serial" in error_msg:
                print(f"\n[断开] 串口连接丢失: {e}")
                try:
                    robot.disconnect()
                except:
                    pass
                print("[等待] 2秒后尝试重新连接...")
                time.sleep(2)
                continue
            else:
                print(f"\n✗ Error: {e}")
                import traceback
                traceback.print_exc()
                break
                
        finally:
            pass
    
    # 清理资源
    if plotter:
        try:
            plotter.save(plot_path)
        except Exception as e:
            print(f"Could not save plot: {e}")
        plotter.stop(keep_open=True)  # 保持图片窗口打开
    if recorder:
        recorder.stop()
    if robot:
        try:
            robot.disconnect()
        except:
            pass
    print("Done.")
    
    # 保持图片窗口打开，等待用户手动关闭
    print("图片窗口已打开，请手动关闭窗口退出程序...")
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Joint Loop Test with Recorded Trajectory")
    parser.add_argument('--port', type=str, default="", help="Serial port")
    parser.add_argument('--motion', type=str, default="my_demo", help="Motion name (default: my_demo)")
    parser.add_argument('--loops', type=int, default=9999999999, help="Number of loops (default: 2)")
    parser.add_argument('--speed', type=int, default=150, help="Speed in deg/s (default: 100)")
    args = parser.parse_args()
    main(args)
