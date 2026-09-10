# Copyright (c) 2025 Synria Robotics Co., Ltd.
# Licensed under the MIT License.
#
# Author: Synria Robotics Team
# Website: https://synriarobotics.ai

import os
import json
import time
import threading
from typing import List, Dict, Any, Optional
from datetime import datetime
import numpy as np

from alicia_d_sdk.utils.trajectory_utils import (
    prepare_position_mode_for_teaching,
    record_waypoints_manual,
)
from alicia_d_sdk.utils import precise_sleep


class DragTeaching:
    """简化的拖动示教类 - 直接记录关节状态"""

    def __init__(self, args, controller):
        self.args = args
        self.controller = controller

    def setup(self):
        """初始化设置"""
        if self.args.save_motion:
            print(f"Motion name: {self.args.save_motion}")
        if self.args.mode == 'auto':
            print(f"Sampling frequency: {getattr(self.args, 'sample_hz', 100.0)} Hz")
        # Display replay/motion speed
        if hasattr(self.args, "speed_deg_s"):
            print(f"Joint speed: {self.args.speed_deg_s} deg/s")
        print("=" * 30)

    def manual_mode(self) -> List[Dict[str, Any]]:
        """手动模式 - 记录关键点"""
        return record_waypoints_manual(self.controller)

    def auto_mode(self) -> List[Dict[str, Any]]:
        """自动模式 - 连续记录"""
        print("\n=== Auto Mode ===")
        print("After disabling torque, drag the robot arm and the system will automatically record the trajectory")

        if not prepare_position_mode_for_teaching(self.controller):
            print("[安全] 未确认位置模式，已取消录制")
            return []

        input("Press Enter to start...")
        self.controller.torque_control('off')
        print("[Safety] Torque disabled, you can drag the robot arm")

        # 记录变量
        trajectory = []
        recording = threading.Event()

        def record_loop():
            """后台记录线程"""
            sample_hz = getattr(self.args, 'sample_hz', 100.0)
            interval = 1.0 / sample_hz
            # For high frequency (>= 100 Hz), use smaller spin_threshold for better efficiency
            # For lower frequencies, use larger spin_threshold to reduce CPU usage
            spin_threshold = 0.002 if interval <= 0.010 else 0.010  # 2ms for high freq, 10ms for low freq
            recording_start_time = time.time()

            while recording.is_set():
                loop_start = time.perf_counter()
                try:
                    state = self.controller.get_robot_state("joint_gripper")
                    if state is not None and state.angles is not None:
                        trajectory.append({
                            "t": time.time() - recording_start_time,
                            "q": state.angles,
                            "grip": state.gripper
                        })
                except Exception as e:
                    print(f"[Warning] Recording failed: {e}")

                # Calculate time taken by the sampling operation and use precise_sleep
                precise_sleep(interval - (time.perf_counter() - loop_start), spin_threshold=spin_threshold)

        try:
            input("Start dragging, press Enter to start recording...")
            recording.set()
            thread = threading.Thread(target=record_loop, daemon=True)
            thread.start()

            input("Press Enter to stop recording...")
            recording.clear()
            thread.join(timeout=1.0)

        finally:
            if not prepare_position_mode_for_teaching(self.controller):
                print("[安全] 未确认位置模式，扭矩保持关闭")
            else:
                self.controller.torque_control('on')
                print("[Safety] Torque re-enabled")

        print(f"[Complete] Recorded {len(trajectory)} points")
        return trajectory

    def replay_only_mode(self) -> Optional[List[Dict[str, Any]]]:
        """仅回放模式 - 加载已有数据"""
        print("\n=== Replay Only Mode ===")

        # 加载数据
        save_dir = os.path.join("example_motions", self.args.save_motion)
        traj_path = os.path.join(save_dir, "joint_traj.json")
        meta_path = os.path.join(save_dir, "meta.json")

        # 检查目录和文件是否存在
        if not os.path.exists(save_dir):
            print(f"[Error] Motion directory not found: {save_dir}")
            print("\nAvailable motions:")
            available = list_available_motions()
            if available:
                for motion in available[:5]:  # Show only first 5
                    print(f"  - {motion}")
                if len(available) > 5:
                    print(f"  ... and {len(available)-5} more motions")
                print(f"\nUse --list-motions to view full list")
            else:
                print("  No recorded motions found")
                print("  Please record a motion using auto or manual mode first")
            return None

        if not os.path.exists(traj_path):
            print(f"[Error] Trajectory file not found: {traj_path}")
            print("This motion may be corrupted or incomplete")
            return None

        if not os.path.exists(meta_path):
            print(f"[Warning] Metadata file not found: {meta_path}")
            print("Will continue loading with default settings")

        # 读取数据和元信息
        try:
            with open(traj_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"[Error] Failed to read trajectory file: {e}")
            return None

        # 读取元信息
        meta = {}
        if os.path.exists(meta_path):
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
            except Exception as e:
                print(f"[Warning] Failed to read metadata: {e}")

        # 更新模式为原始记录模式
        original_mode = meta.get('mode', 'auto')
        print(f"[Load] Trajectory: {len(data)} points")
        print(f"[Load] Original mode: {original_mode}")
        print(f"[Load] Created at: {meta.get('created_at', 'Unknown')}")
        print(f"[Load] Sampling frequency: {meta.get('sample_hz', 'Unknown')} Hz")

        # 临时保存原始参数并设置为原始模式
        self._original_mode = self.args.mode
        self.args.mode = original_mode

        return data

    def save_data(self, data: List[Dict[str, Any]]) -> Optional[str]:
        """保存数据"""
        if not data:
            print("[Save] No data")
            return None

        # 创建保存目录
        save_dir = os.path.join("example_motions", self.args.save_motion)
        os.makedirs(save_dir, exist_ok=True)

        # 保存关节轨迹
        traj_path = os.path.join(save_dir, "joint_traj.json")
        with open(traj_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 保存元信息
        meta = {
            "motion": self.args.save_motion,
            "mode": self.args.mode,  # 保存记录时的模式
            "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "count": len(data),
            "description": "拖动示教轨迹"
        }
        # 只有auto模式才保存采样频率
        if self.args.mode == 'auto':
            meta["sample_hz"] = getattr(self.args, 'sample_hz', 100.0)

        meta_path = os.path.join(save_dir, "meta.json")
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        print(f"[Save] Trajectory: {traj_path}")
        print(f"[Save] Metadata: {meta_path}")

        return save_dir

    def replay(self, data: List[Dict[str, Any]]):
        """根据模式回放轨迹"""
        if not data:
            return

        speed_deg_s = getattr(self.args, "speed_deg_s", 10)
        manual_speed_deg_s = getattr(
            self.args, "manual_speed_deg_s", 0.5
        )
        auto_speed_limit_deg_s = getattr(
            self.args, "auto_speed_limit_deg_s", 90.0
        )
        playback_rate = getattr(self.args, "playback_rate", 1.0)
        if auto_speed_limit_deg_s <= 0:
            raise ValueError("auto_speed_limit_deg_s must be positive")
        if manual_speed_deg_s <= 0:
            raise ValueError("manual_speed_deg_s must be positive")
        if playback_rate <= 0:
            raise ValueError("playback_rate must be positive")
        arrival_tolerance = np.deg2rad(3.0)

        print(f"\n=== Trajectory Replay ===")
        print(f"Replay mode: {self.args.mode}")
        replay = input(f"Replay trajectory ({len(data)} points)? (y/n): ").strip().lower()
        if replay != 'y':
            return

        print("[Replay] Starting...")

        if not prepare_position_mode_for_teaching(self.controller):
            print("[安全] 未确认位置模式，已取消回放")
            return

        # Move to starting point
        first_point = data[0]
        print(f"[Replay] Moving to starting point (speed {speed_deg_s} deg/s)...")
        try:
            current_joints = self.controller.get_robot_state("joint")
            first_joints = np.asarray(first_point["q"], dtype=float)
            if current_joints is None:
                raise RuntimeError("Unable to read current joints before replay")
            measured_travel_deg = float(np.max(np.abs(
                np.degrees(first_joints - np.asarray(current_joints, dtype=float))
            )))
            # Immediately after recording, the SDK feedback cache can still
            # contain an older sample. The final recorded point is a reliable
            # conservative reference for the move back to the first point.
            recorded_travel_deg = float(np.max(np.abs(np.degrees(
                first_joints - np.asarray(data[-1]["q"], dtype=float)
            ))))
            start_travel_deg = max(measured_travel_deg, recorded_travel_deg)
            # Add both fixed transition time and a low-speed scale margin. A
            # nominal 1 deg/s command maps to about 0.97 deg/s in the register.
            start_timeout = max(
                15.0,
                start_travel_deg / max(speed_deg_s * 0.9, 0.01) + 8.0,
            )
            print(
                f"[Replay] Starting-point travel {start_travel_deg:.1f} deg, "
                f"timeout {start_timeout:.1f} s"
            )
            reached = self.controller.set_robot_state(
                target_joints=first_point["q"],
                gripper_value=None,
                joint_format='rad',
                speed_deg_s=speed_deg_s,
                tolerance=arrival_tolerance,
                timeout=start_timeout,
                wait_for_completion=True,
            )
            if not reached:
                print("[Warning] Starting point was not reached; replay cancelled")
                return
        except Exception as e:
            print(f"[Warning] Failed to move to starting point: {e}")
            return

        time.sleep(0.001)
        print("[Replay] Starting trajectory playback...")

        # 初始化前一个点的关节角度为第一个点
        prev_joints = data[0]["q"]

        if self.args.mode == 'auto':
            # Follow the recorded timestamps directly. The low-speed setting
            # used to approach the first point must not stretch the trajectory.
            print(
                "[Replay] Using original-timing streaming mode "
                f"({playback_rate:.2f}x, speed limit "
                f"{auto_speed_limit_deg_s:.1f} deg/s)"
            )
            playback_start = time.perf_counter()
            scheduled_time = 0.0
            for i, point in enumerate(data):
                try:
                    if i > 0:
                        previous = data[i - 1]
                        recorded_dt = max(
                            0.0,
                            float(point.get("t", 0.0)) -
                            float(previous.get("t", 0.0)),
                        )
                        scheduled_time += recorded_dt / playback_rate
                        precise_sleep(
                            scheduled_time -
                            (time.perf_counter() - playback_start),
                            spin_threshold=0.002,
                        )

                    self.controller.set_robot_state(
                        target_joints=point["q"],
                        gripper_value=None,
                        joint_format='rad',
                        speed_deg_s=auto_speed_limit_deg_s,
                        wait_for_completion=False,
                    )
                    prev_joints = point["q"]

                    if i == len(data) - 1 or i % max(1, len(data) // 20) == 0:
                        print(f"[Replay] {i+1}/{len(data)}")
                except Exception as e:
                    print(f"[Error] Failed to replay point {i+1}: {e}")

            final_point = data[-1]
            final_joints = np.asarray(final_point["q"], dtype=float)
            current_joints = self.controller.get_robot_state("joint")
            final_timeout = 10.0
            if current_joints is not None:
                final_travel_deg = float(np.max(np.abs(np.degrees(
                    final_joints - np.asarray(current_joints, dtype=float)
                ))))
                final_timeout = max(
                    10.0,
                    final_travel_deg / auto_speed_limit_deg_s + 5.0,
                )
            if not self.controller.set_robot_state(
                target_joints=final_point["q"],
                gripper_value=None,
                joint_format='rad',
                speed_deg_s=auto_speed_limit_deg_s,
                tolerance=arrival_tolerance,
                timeout=final_timeout,
                wait_for_completion=True,
            ):
                print("[Warning] Final replay point was not reached")

        elif self.args.mode == 'manual':
            print(
                "[Replay] Using feedback-based waypoint mode "
                f"({manual_speed_deg_s:.2f} deg/s)"
            )
            # The first point was reached above; start from the second point to
            # avoid sending the same target twice and pausing unnecessarily.
            for i, point in enumerate(data[1:], start=2):
                try:
                    target_joints = np.asarray(point["q"], dtype=float)
                    previous_joints = np.asarray(prev_joints, dtype=float)
                    travel_deg = float(np.max(np.abs(np.degrees(
                        target_joints - previous_joints
                    ))))
                    point_timeout = max(
                        15.0,
                        travel_deg /
                        max(manual_speed_deg_s * 0.9, 0.01) + 8.0,
                    )
                    reached = self.controller.set_robot_state(
                        target_joints=point["q"],
                        gripper_value=None,
                        joint_format='rad',
                        speed_deg_s=manual_speed_deg_s,
                        tolerance=arrival_tolerance,
                        timeout=point_timeout,
                        wait_for_completion=True,
                    )
                    if not reached:
                        print(
                            f"[Warning] Point {i} was not reached; "
                            "replay cancelled"
                        )
                        return

                    prev_joints = point["q"]
                    print(f"[Replay] {i}/{len(data)}")
                except Exception as e:
                    print(f"[Error] Failed to replay point {i}: {e}")
                    return

        print("[Replay] Complete")

    def run(self):
        """运行主程序"""
        try:
            # 对于replay_only模式，在setup之前先验证动作是否存在
            if self.args.mode == 'replay_only':
                if not self.args.save_motion:
                    print("[Error] Replay mode requires --save-motion parameter")
                    print("Use --list-motions to view available motions")
                    return

                # 检查动作是否存在
                save_dir = os.path.join("example_motions", self.args.save_motion)
                if not os.path.exists(save_dir):
                    print(f"[Error] Motion '{self.args.save_motion}' does not exist")
                    print("\nHint:")
                    available = list_available_motions()
                    if available:
                        print("Available motions:")
                        for motion in available[:3]:
                            print(f"  {motion}")
                        if len(available) > 3:
                            print(f"  ... and {len(available)-3} more")
                    else:
                        print("No recorded motions found, please record first")
                    return

            self.setup()

            # 根据模式执行不同操作
            if self.args.mode == 'manual':
                data = self.manual_mode()
            elif self.args.mode == 'auto':
                data = self.auto_mode()
            elif self.args.mode == 'replay_only':
                data = self.replay_only_mode()
            else:
                raise ValueError(f"Unsupported mode: {self.args.mode}")

            if data:
                # 只有非replay_only模式才保存数据
                if self.args.mode != 'replay_only':
                    save_dir = self.save_data(data)

                    if save_dir:
                        print(f"\n[Complete] Drag teaching completed!")
                        print(f"Data saved to: {save_dir}")
                else:
                    print(f"\n[Complete] Trajectory loading completed!")

                # 回放
                self.replay(data)

                # 恢复原始模式（对于replay_only）
                if hasattr(self, '_original_mode'):
                    self.args.mode = self._original_mode

            else:
                print("[Complete] No data recorded or loading failed")

        except KeyboardInterrupt:
            print("\n[Interrupted] User interrupted")
        except Exception as e:
            print(f"[Error] Run failed: {e}")


def list_available_motions() -> List[str]:
    """列出所有可用的动作"""
    motions_dir = "example_motions"
    if not os.path.exists(motions_dir):
        return []

    motions = []
    for item in os.listdir(motions_dir):
        motion_path = os.path.join(motions_dir, item)
        if os.path.isdir(motion_path):
            # 检查是否有轨迹数据
            traj_file = os.path.join(motion_path, "joint_traj.json")
            if os.path.exists(traj_file):
                motions.append(item)

    return sorted(motions)


def print_available_motions():
    """打印所有可用的动作"""
    motions = list_available_motions()

    print("=== Available Motions List ===")
    if not motions:
        print("No recorded motions found")
        print("Please record a motion using auto or manual mode first")
        return

    print(f"Found {len(motions)} motions in example_motions/ directory:")

    for i, motion in enumerate(motions, 1):
        motion_dir = os.path.join("example_motions", motion)
        meta_path = os.path.join(motion_dir, "meta.json")

        # 读取动作信息
        info = f"{i:2d}. {motion}"
        if os.path.exists(meta_path):
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                mode = meta.get('mode', 'unknown')
                created = meta.get('created_at', 'unknown')
                count = meta.get('count', 0)
                info += f" (mode: {mode}, points: {count}, created: {created})"
            except:
                pass

        print(info)

    print(f"\nUsage example:")
    print(f"python 08_demo_drag_teaching.py --mode replay_only --save-motion {motions[0]}")
