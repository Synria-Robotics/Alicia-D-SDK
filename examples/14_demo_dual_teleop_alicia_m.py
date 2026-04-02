#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

"""Dual Teleoperation Demo: 2x Alicia-D (Leader) -> 2x Alicia-M (Follower)

Runs two independent leader-follower loops in the same process:
    left leader  -> left follower
    right leader -> right follower

Usage:
    python 14_demo_dual_teleop_alicia_m.py \
      --left-leader-port /dev/ttyUSB0 \
      --left-follower-port /dev/ttyUSB1 \
      --right-leader-port /dev/ttyUSB2 \
      --right-follower-port /dev/ttyUSB3 \
      --mit --verbose
"""

import argparse
import builtins
from datetime import datetime
import threading
import time
import numpy as np

import alicia_d_sdk
import alicia_m_sdk
from alicia_d_sdk.utils import precise_sleep
from robocore.utils.beauty_logger import beauty_print


def install_timestamped_print():
    """Prefix all print output with a local timestamp."""
    original_print = builtins.print

    def timestamped_print(*args, **kwargs):
        sep = kwargs.get("sep", " ")
        end = kwargs.get("end", "\n")
        file = kwargs.get("file", None)
        flush = kwargs.get("flush", False)

        message = sep.join(str(arg) for arg in args)
        timestamp = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}]"
        original_print(f"{timestamp} {message}", end=end, file=file, flush=flush)

    builtins.print = timestamped_print


def map_joints(leader_joints):
    joint_signs = [1.0, 1.0, -1.0, -1.0, 1.0, -1.0]
    return [sign * angle for angle, sign in zip(leader_joints, joint_signs)]


def map_gripper(leader_gripper):
    return max(0.0, min(1000.0, float(leader_gripper)))


def wait_for_enter(stop_event):
    try:
        input("\nDual teleoperation active. Press Enter to stop...\n")
    except KeyboardInterrupt:
        print()
    finally:
        stop_event.set()


def connect_arm_pair(side, leader_port, follower_port, follower_version, use_mit):
    beauty_print(f"Connecting {side} leader arm (Alicia-D)...", type="info")
    leader = alicia_d_sdk.create_robot(port=leader_port)
    if not leader.is_connected():
        raise RuntimeError(f"Failed to connect {side} leader arm")

    beauty_print(f"Connecting {side} follower arm (Alicia-M)...", type="info")
    follower = alicia_m_sdk.create_robot(
        port=follower_port,
        version=follower_version,
        control_mode='mit' if use_mit else None,
    )
    if not follower.is_connected():
        leader.disconnect()
        raise RuntimeError(f"Failed to connect {side} follower arm")

    return leader, follower


def print_initial_states(side, leader, follower):
    leader_joints = leader.get_robot_state("joint")
    follower_joints = follower.get_robot_state("joint")
    if leader_joints is not None:
        beauty_print(f"{side} leader joints (deg):   {np.round(np.degrees(leader_joints), 1).tolist()}")
    if follower_joints is not None:
        beauty_print(f"{side} follower joints (deg): {np.round(np.degrees(follower_joints), 1).tolist()}")


def disable_follower_auto_query(side, follower):
    comm_manager = getattr(follower.servo_driver, "comm_manager", None)
    if comm_manager is not None:
        comm_manager.disable_auto_query()
        beauty_print(f"Disabled {side} follower auto query during teleoperation", type="info")


def main(args):
    install_timestamped_print()
    beauty_print("Dual Teleoperation: Alicia-D x2 -> Alicia-M x2", type="module")

    left_leader = left_follower = right_leader = right_follower = None

    try:
        left_leader, left_follower = connect_arm_pair(
            "left",
            args.left_leader_port,
            args.left_follower_port,
            args.left_follower_version,
            args.mit,
        )
        right_leader, right_follower = connect_arm_pair(
            "right",
            args.right_leader_port,
            args.right_follower_port,
            args.right_follower_version,
            args.mit,
        )

        beauty_print("Both arm pairs connected successfully", type="success")
        print_initial_states("Left", left_leader, left_follower)
        print_initial_states("Right", right_leader, right_follower)

        if not args.skip_home:
            beauty_print("Moving both followers to home position...", type="info")
            left_follower.go_home(speed=20)
            right_follower.go_home(speed=20)
            beauty_print("Both followers at home position", type="success")

        disable_follower_auto_query("left", left_follower)
        disable_follower_auto_query("right", right_follower)

        mode_str = "MIT" if args.mit else f"PV (speed={args.speed} deg/s)"
        beauty_print(f"Starting dual teleoperation at {args.frequency} Hz ({mode_str})", type="module")
        beauty_print("Drag both leader arms to control both follower arms")
        beauty_print("Press Enter or Ctrl+C to stop\n")

        beauty_print("Disabling both leader arm torques for free movement...", type="info")
        left_leader.torque_control('off')
        right_leader.torque_control('off')

        stop_event = threading.Event()
        input_thread = threading.Thread(target=wait_for_enter, args=(stop_event,), daemon=True)
        input_thread.start()

        interval = 1.0 / args.frequency
        spin_threshold = 0.002 if interval <= 0.010 else 0.010
        loop_count = 0
        speed = 0 if args.mit else args.speed

        while not stop_event.is_set():
            loop_start = time.perf_counter()

            left_state = left_leader.get_robot_state("joint_gripper")
            if left_state is not None and left_state.angles is not None:
                left_follower.set_robot_state(
                    target_joints=map_joints(left_state.angles),
                    gripper_value=map_gripper(left_state.gripper),
                    joint_format='rad',
                    speed=speed,
                    gripper_speed=speed,
                    wait_for_completion=False,
                )

            right_state = right_leader.get_robot_state("joint_gripper")
            if right_state is not None and right_state.angles is not None:
                right_follower.set_robot_state(
                    target_joints=map_joints(right_state.angles),
                    gripper_value=map_gripper(right_state.gripper),
                    joint_format='rad',
                    speed=speed,
                    gripper_speed=speed,
                    wait_for_completion=False,
                )

            loop_count += 1
            if args.verbose and loop_count % max(1, int(args.frequency)) == 0:
                if left_state is not None and left_state.angles is not None:
                    left_deg = np.round(np.degrees(left_state.angles), 1).tolist()
                    print(f"  [L {loop_count:6d}] joints={left_deg}  gripper={left_state.gripper:.0f}")
                if right_state is not None and right_state.angles is not None:
                    right_deg = np.round(np.degrees(right_state.angles), 1).tolist()
                    print(f"  [R {loop_count:6d}] joints={right_deg}  gripper={right_state.gripper:.0f}")

            elapsed = time.perf_counter() - loop_start
            precise_sleep(interval - elapsed, spin_threshold=spin_threshold)

    except KeyboardInterrupt:
        print()
    finally:
        beauty_print("Re-enabling leader arm torques...", type="info")
        if left_leader is not None:
            left_leader.torque_control('on')
        if right_leader is not None:
            right_leader.torque_control('on')

        beauty_print("Disconnecting...", type="info")
        if left_leader is not None:
            left_leader.disconnect()
        if left_follower is not None:
            left_follower.disconnect()
        if right_leader is not None:
            right_leader.disconnect()
        if right_follower is not None:
            right_follower.disconnect()
        beauty_print("Done", type="success")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Dual Teleoperation: Alicia-D x2 -> Alicia-M x2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('--left-leader-port', type=str, default="",
                        help="Serial port for left leader arm (Alicia-D).")
    parser.add_argument('--left-follower-port', type=str, default="",
                        help="Serial port for left follower arm (Alicia-M).")
    parser.add_argument('--right-leader-port', type=str, default="",
                        help="Serial port for right leader arm (Alicia-D).")
    parser.add_argument('--right-follower-port', type=str, default="",
                        help="Serial port for right follower arm (Alicia-M).")
    parser.add_argument('--left-follower-version', type=str, default="v1_1",
                        help="Left Alicia-M version (default: v1_1)")
    parser.add_argument('--right-follower-version', type=str, default="v1_1",
                        help="Right Alicia-M version (default: v1_1)")
    parser.add_argument('--frequency', type=float, default=60.0,
                        help="Control loop frequency in Hz (default: 60)")
    parser.add_argument('--speed', type=float, default=573.0,
                        help="Follower joint speed in deg/s for PV mode (default: 573)")
    parser.add_argument('--skip-home', action='store_true',
                        help="Skip moving both followers to home position before starting")
    parser.add_argument('--mit', action='store_true',
                        help="Use MIT position mode instead of PV mode")
    parser.add_argument('--verbose', '-v', action='store_true',
                        help="Print joint states for both leaders once per second")

    main(parser.parse_args())
