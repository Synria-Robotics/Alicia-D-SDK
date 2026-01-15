"""
Demo: Multi-Joint Complex Loop Test with Gripper
Usage:
python 1_demo_multi_joint_loop.py
"""

import argparse
import csv
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
    Lightweight background logger for targets, actual joints, gripper, and temperature.
    Stores recent samples for plotting and streams full history to CSV.
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
        self._current_gripper_target = None
        self._current_phase = ""
        self._current_loop_idx = 0
        self._last_temperature = []
        self._temp_backoff = temp_interval
        self._temp_failures = 0

    def start(self):
        self._running = True
        self._csv_file = open(self.log_path, "w", newline="", buffering=1)
        fieldnames = [
            "timestamp",
            "loop_idx",
            "phase",
            "target_joints_deg",
            "actual_joints_deg",
            "target_gripper",
            "actual_gripper",
            "temperatures",
            "run_status",
        ]
        self._csv_writer = csv.DictWriter(self._csv_file, fieldnames=fieldnames)
        self._csv_writer.writeheader()

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()
        if self._csv_file:
            self._csv_file.close()

    def set_target(self, joints_deg, gripper_value=None, phase: str = "", loop_idx: int = 0):
        with self._lock:
            self._current_target_deg = list(joints_deg)
            self._current_gripper_target = gripper_value
            self._current_phase = phase
            self._current_loop_idx = loop_idx

    def get_recent_records(self):
        with self._lock:
            return list(self.records)

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
                        # Only log the first failure in a streak to reduce noise
                        if self._temp_failures == 0:
                            print(f"[Telemetry] Temperature read failed: {exc}")
                        self._temp_failures += 1
                        # Short pause between retries to avoid bus saturation
                        time.sleep(0.05)

                # Increase backoff after consecutive failures, capped
                if temps is None:
                    self._temp_backoff = min(self.temp_backoff_max, self._temp_backoff * 1.6)
                else:
                    self._temp_backoff = self.temp_interval

                next_temp_time = now + self._temp_backoff

            try:
                joints = self.robot.get_robot_state(info_type="joint")
                gripper_val = self.robot.get_robot_state(info_type="gripper")
            except Exception as exc:
                print(f"[Telemetry] Read failed: {exc}")
                time.sleep(self.poll_interval)
                continue

            if joints is None:
                time.sleep(self.poll_interval)
                continue

            # Assume get_joints returns radians, convert to degrees
            actual_deg = [np.rad2deg(x) for x in joints]

            with self._lock:
                target_deg = list(self._current_target_deg)
                target_gripper = self._current_gripper_target
                phase = self._current_phase
                loop_idx = self._current_loop_idx

            temps_to_use = temps if temps is not None else self._last_temperature

            record = {
                "timestamp": now,
                "loop_idx": loop_idx,
                "phase": phase,
                "target_joints_deg": target_deg,
                "actual_joints_deg": actual_deg,
                "target_gripper": target_gripper,
                "actual_gripper": f"{gripper_val:.1f}" if gripper_val is not None else "",
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
                        "target_gripper": "" if target_gripper is None else int(target_gripper),
                        "actual_gripper": f"{gripper_val:.1f}" if gripper_val is not None else "",
                        "temperatures": "" if not temps_to_use else ";".join(f"{t:.1f}" for t in temps_to_use),
                        "run_status": "Running",
                    }
                )

            time.sleep(self.poll_interval)


class RealtimePlotter:
    """Non-blocking Matplotlib plotter for recent telemetry."""

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
        # self._ax_actual.legend(ncol=6, fontsize=8, loc="upper right") # Optional, saving space

        # 3. Temp Plot
        self._temp_lines = []
        self._ax_temp.set_ylabel("Temperature (°C)")
        self._ax_temp.set_xlabel("Time (s)")
        self._ax_temp.grid(True, alpha=0.2)

    def start(self):
        plt.ion()
        self._fig.tight_layout()
        self._fig.show()

    def save(self, path):
        try:
            self._fig.savefig(path)
            print(f"[Plotter] Saved plot to {path}")
        except Exception as e:
            print(f"[Plotter] Failed to save plot: {e}")

    def stop(self):
        plt.close(self._fig)

    def update(self):
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
        loop_indices = np.array([item.get("loop_idx", 0) for item in data])

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

            # Initialize temperature lines lazily based on available sensor count
            if not self._temp_lines:
                for idx in range(temp_array.shape[1]):
                    (line,) = self._ax_temp.plot([], [], label=f"T{idx + 1}")
                    self._temp_lines.append(line)
                self._ax_temp.legend(ncol=6, fontsize=8, loc="upper right")

            for idx, line in enumerate(self._temp_lines):
                line.set_data(temp_time, temp_array[:, idx])

            self._ax_temp.relim()
            self._ax_temp.autoscale_view()

        self._fig.canvas.draw_idle()
        self._fig.canvas.flush_events()
        plt.pause(0.001)

class GripperController:
    """
    Background controller to oscillate gripper while maintaining robot joint target.
    Because the protocol sends Joint+Gripper in one packet, we must control both together.
    """
    def __init__(self, robot, initial_speed):
        self.robot = robot
        self.running = False
        self.active = False  # If True, sends commands. If False, idles.
        self.thread = None
        
        # Shared State
        self.current_joint_target = [0.0] * 6
        self.speed = initial_speed
        
        # Gripper oscillation state
        self.gripper_value = 1.0
        self.gripper_dir = 1  # 1 for opening, -1 for closing
        self.gripper_step = 20 # Speed of gripper movement per tick
        
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
            
    def set_active(self, active: bool):
        self.active = active
        
    def set_target(self, target_joints, speed):
        self.current_joint_target = target_joints
        self.speed = speed
        
    def _run(self):
        while self.running:
            if self.active:
                # Update gripper logic
                self.gripper_value += self.gripper_step * self.gripper_dir
                
                # Check bounds and reverse
                if self.gripper_value >= 999:
                    self.gripper_value = 999
                    self.gripper_dir = -1
                elif self.gripper_value <= 1:
                    self.gripper_value = 1
                    self.gripper_dir = 1
                
                # Send combined command
                # Note: non-blocking send
                try:
                    self.robot.set_robot_state(
                        target_joints=self.current_joint_target,
                        gripper_value=int(self.gripper_value),
                        joint_format='deg',
                        speed_deg_s=self.speed,
                        wait_for_completion=False 
                    )
                except Exception as e:
                    print(f"Error in gripper thread: {e}")
                
                time.sleep(0.04) # ~25Hz control loop
            else:
                time.sleep(0.05)


def main(args):
    """Control robot joint movements in a multi-point loop with gripper."""
    
    # Initialize robot instance
    robot = alicia_d_sdk.create_robot(port=args.port)

    # Motion Parameters
    speed = 100  # deg/s
    loop_count = 2
    
    # Pose A
    # pose_a = [-90.0, -45.0, 100.0, -90.0, -30.0, -60.0]
    pose_a = [-20.0, -20.0, 20.0, -20.0, -20.0, 20.0]
    # Pose B
    # pose_b = [90.0, 45.0, -20.0, 90.0, 30.0, 60.0]
    pose_b = [20.0, 20.0, -20.0, 20.0, 20.0, -20.0]
    # Zero Position
    pose_zero = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    controller = None
    recorder = None
    plotter = None

    try:
        # Connect to robot
        if not robot.connect():
            print("✗ Connection failed. Please check serial port settings.")
            return
            
        print(f"Starting Multi-Joint Loop Test with Gripper: {loop_count} iterations")
        
        # Create log directory with date structure
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        time_str = now.strftime("%H%M%S")
        
        # Use the script's directory as base to ensure demo_log is created in examples/benchmark/
        script_dir = Path(__file__).resolve().parent
        base_dir = script_dir / "demo_log" / date_str
        base_dir.mkdir(parents=True, exist_ok=True)
        
        log_path = base_dir / f"{time_str}_data.csv"
        plot_path = base_dir / f"{time_str}_plot.png"
        
        print(f"Logging data to: {log_path}")
        
        # Telemetry recorder and realtime plotter
        recorder = TelemetryRecorder(
            robot,
            log_path=log_path,
            poll_interval=0.2,
            temp_interval=2.0,
            max_samples_for_plot=2500,
        )
        recorder.set_target(pose_zero, gripper_value=None, phase="Init Zero")
        recorder.start()

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
        
        # Start Gripper Controller
        controller = GripperController(robot, speed)
        controller.start()

        for i in range(loop_count):
            print(f"--- Loop {i+1}/{loop_count} ---")
            
            # --- Active Phase (A <-> B) ---
            print("  Activating gripper motion...")
            controller.set_active(True)
            
            # Step 1: Move to Pose A
            print(f"  Moving to Pose A")
            controller.set_target(pose_a, speed)
            recorder.set_target(pose_a, gripper_value=controller.gripper_value, phase="Pose A", loop_idx=i+1)
            # Use internal wait logic because send_robot_target is hijacked by thread
            robot._wait_for_joint_target(
                target_joints=[np.deg2rad(x) for x in pose_a],
                tolerance=0.1,
                timeout=10.0
            )
            time.sleep(0.5)
            if plotter:
                plotter.update()
            
            # Step 2: Move to Pose B
            print(f"  Moving to Pose B")
            controller.set_target(pose_b, speed)
            recorder.set_target(pose_b, gripper_value=controller.gripper_value, phase="Pose B", loop_idx=i+1)
            robot._wait_for_joint_target(
                target_joints=[np.deg2rad(x) for x in pose_b],
                tolerance=0.1,
                timeout=10.0
            ) 
            time.sleep(0.5)
            if plotter:
                plotter.update()
            
            # --- Return Phase (Zero) ---
            # Stop gripper oscillation for return to zero
            print("  Stopping gripper motion for Return...")
            controller.set_active(False)
            time.sleep(0.1) # Wait for thread to pause
            
            # Step 3: Return to Zero
            print("  Returning to Zero...")
            recorder.set_target(pose_zero, gripper_value=1000, phase="Return Zero", loop_idx=i+1)
            robot.set_robot_state(
                target_joints=pose_zero,
                gripper_value=1000,
                joint_format='deg',
                speed_deg_s=speed,
                wait_for_completion=True
            )
            
            time.sleep(1)
            if plotter:
                plotter.update()

    except KeyboardInterrupt:
        print("\n✗ Processing interrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
    finally:
        if controller:
            controller.stop()
        if plotter:
            # Save the plot before closing
            try:
                plotter.save(plot_path)
            except Exception as e:
                print(f"Could not save plot: {e}")
            plotter.stop()
        if recorder:
            recorder.stop()
        robot.disconnect()
        print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Joint Loop Test")
    parser.add_argument('--port', type=str, default="", help="Serial port")
    args = parser.parse_args()
    main(args)
