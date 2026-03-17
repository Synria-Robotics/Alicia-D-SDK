# Copyright (c) 2025 Synria Robotics Co., Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# Author: Synria Robotics Team
# Website: https://synriarobotics.ai

"""
Teleoperation Module - Leader-Follower Control

Uses Alicia-D (servo teaching arm) as leader to control
Alicia-M (motor operation arm) as follower in real-time.
"""

import time
import threading
import numpy as np
from typing import Optional, List, Callable

from alicia_d_sdk.utils import precise_sleep
from alicia_d_sdk.utils import logger


class Teleoperation:
    """Real-time leader-follower teleoperation controller.

    Reads joint states from the leader arm (Alicia-D) and mirrors them
    to the follower arm (Alicia-M) at a configurable frequency.

    :param leader: Alicia-D SynriaRobotAPI instance (teaching arm)
    :param follower: Alicia-M SynriaRobotAPI instance (operation arm)
    :param frequency_hz: Control loop frequency in Hz (default: 60.0)
    :param follower_speed_deg_s: Speed sent to follower arm in deg/s (default: 200)
    :param gripper_scale: Scaling factor from leader gripper to follower gripper.
        Alicia-D gripper range is 0-1000, Alicia-M is 0-100, so default is 0.1.
    :param joint_signs: Optional list of 6 sign multipliers (+1/-1) for joint direction mapping.
        Used to compensate if leader and follower have opposite joint directions.
    :param joint_offsets_rad: Optional list of 6 radian offsets added to leader joints.
    """

    def __init__(
        self,
        leader,
        follower,
        frequency_hz: float = 60.0,
        follower_speed_deg_s: float = 200,
        gripper_scale: float = 0.1,
        joint_signs: Optional[List[float]] = None,
        joint_offsets_rad: Optional[List[float]] = None,
    ):
        self.leader = leader
        self.follower = follower
        self.frequency_hz = frequency_hz
        self.follower_speed_deg_s = follower_speed_deg_s
        self.gripper_scale = gripper_scale
        self.joint_signs = joint_signs or [1.0] * 6
        self.joint_offsets_rad = joint_offsets_rad or [0.0] * 6

        self._running = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._on_state_callback: Optional[Callable] = None
        self._loop_count = 0
        self._error_count = 0

    def set_state_callback(self, callback: Callable):
        """Register a callback invoked each loop with (leader_joints, leader_gripper, loop_count).

        :param callback: Function(leader_joints, leader_gripper, loop_count)
        """
        self._on_state_callback = callback

    def _map_joints(self, leader_joints: List[float]) -> List[float]:
        """Apply sign and offset mapping from leader to follower joint space.

        :param leader_joints: Leader joint angles in radians
        :return: Follower joint angles in radians
        """
        return [
            sign * angle + offset
            for angle, sign, offset in zip(leader_joints, self.joint_signs, self.joint_offsets_rad)
        ]

    def _map_gripper(self, leader_gripper: float) -> float:
        """Map leader gripper value to follower gripper range.

        :param leader_gripper: Leader gripper value (0-1000)
        :return: Follower gripper value (0-100)
        """
        return max(0.0, min(100.0, leader_gripper * self.gripper_scale))

    def _control_loop(self):
        """Main teleoperation control loop running in background thread."""
        interval = 1.0 / self.frequency_hz
        spin_threshold = 0.002 if interval <= 0.010 else 0.010

        logger.info(f"Teleoperation loop started at {self.frequency_hz} Hz")

        while self._running.is_set():
            loop_start = time.perf_counter()
            try:
                state = self.leader.get_robot_state("joint_gripper")
                if state is None or state.angles is None:
                    self._error_count += 1
                    continue

                follower_joints = self._map_joints(state.angles)
                follower_gripper = self._map_gripper(state.gripper)

                self.follower.set_robot_state(
                    target_joints=follower_joints,
                    gripper_value=follower_gripper,
                    joint_format='rad',
                    speed_deg_s=self.follower_speed_deg_s,
                    wait_for_completion=False,
                )

                self._loop_count += 1
                if self._on_state_callback:
                    self._on_state_callback(state.angles, state.gripper, self._loop_count)

            except Exception as e:
                self._error_count += 1
                if self._error_count <= 5:
                    logger.warning(f"Teleoperation loop error: {e}")
                elif self._error_count == 6:
                    logger.warning("Suppressing further teleoperation error messages")

            elapsed = time.perf_counter() - loop_start
            precise_sleep(interval - elapsed, spin_threshold=spin_threshold)

        logger.info(f"Teleoperation loop stopped (sent {self._loop_count} commands, {self._error_count} errors)")

    def start(self):
        """Start teleoperation in a background thread.

        The leader arm's torque is disabled so it can be freely dragged.
        The follower arm will mirror the leader's joint positions.
        """
        if self._running.is_set():
            logger.warning("Teleoperation is already running")
            return

        logger.info("Disabling leader arm torque for free movement...")
        self.leader.torque_control('off')

        self._loop_count = 0
        self._error_count = 0
        self._running.set()
        self._thread = threading.Thread(target=self._control_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop teleoperation and re-enable leader arm torque."""
        if not self._running.is_set():
            return

        self._running.clear()
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

        logger.info("Re-enabling leader arm torque...")
        self.leader.torque_control('on')

    def run_interactive(self):
        """Run teleoperation interactively until user presses Enter.

        Convenience method that starts teleoperation, waits for user input,
        then stops cleanly.
        """
        self.start()
        try:
            input("\nTeleoperation active. Press Enter to stop...\n")
        except KeyboardInterrupt:
            print()
        finally:
            self.stop()
