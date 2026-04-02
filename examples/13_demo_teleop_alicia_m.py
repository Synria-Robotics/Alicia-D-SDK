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

"""Teleoperation Demo: Alicia-D (Leader) → Alicia-M (Follower)

Uses the Alicia-D servo teaching arm as leader to control
the Alicia-M motor operation arm as follower in real-time.

Both arms should be connected to the same computer via USB serial.

Usage:
    # Auto-detect both ports
    python 13_demo_teleop_alicia_m.py

    # Specify ports explicitly
    python 13_demo_teleop_alicia_m.py --leader-port /dev/ttyUSB0 --follower-port /dev/ttyUSB1

    # Adjust control frequency and speed
    python 13_demo_teleop_alicia_m.py --frequency 100 --speed 300

    # Get help
    python 13_demo_teleop_alicia_m.py --help
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
        input("\nTeleoperation active. Press Enter to stop...\n")
    except KeyboardInterrupt:
        print()
    finally:
        stop_event.set()


def main(args):
    install_timestamped_print()
    beauty_print("Teleoperation: Alicia-D → Alicia-M", type="module")

    # --- Connect leader (Alicia-D teaching arm) ---
    beauty_print("Connecting leader arm (Alicia-D)...", type="info")
    leader = alicia_d_sdk.create_robot(port=args.leader_port)
    if not leader.is_connected():
        beauty_print("Failed to connect leader arm", type="error")
        return

    # --- Connect follower (Alicia-M operation arm) ---
    beauty_print("Connecting follower arm (Alicia-M)...", type="info")
    follower_control_mode = 'mit' if args.mit else None
    follower = alicia_m_sdk.create_robot(port=args.follower_port, version=args.follower_version,
                                         control_mode=follower_control_mode)
    if not follower.is_connected():
        beauty_print("Failed to connect follower arm", type="error")
        leader.disconnect()
        return

    beauty_print("Both arms connected successfully", type="success")

    # --- Print initial states ---
    leader_joints = leader.get_robot_state("joint")
    follower_joints = follower.get_robot_state("joint")
    if leader_joints is not None:
        beauty_print(f"Leader joints (deg):   {np.round(np.degrees(leader_joints), 1).tolist()}")
    if follower_joints is not None:
        beauty_print(f"Follower joints (deg): {np.round(np.degrees(follower_joints), 1).tolist()}")

    # --- Optional: move follower to home first ---
    if not args.skip_home:
        beauty_print("Moving follower to home position...", type="info")
        follower.go_home(speed=20)
        beauty_print("Follower at home position", type="success")

    mode_str = "MIT" if args.mit else f"PV (speed={args.speed} deg/s)"
    beauty_print(f"Starting teleoperation at {args.frequency} Hz ({mode_str})", type="module")
    beauty_print("Drag the leader arm (Alicia-D) to control the follower arm (Alicia-M)")
    beauty_print("Press Enter or Ctrl+C to stop\n")

    follower_comm_manager = getattr(follower.servo_driver, "comm_manager", None)
    if follower_comm_manager is not None:
        follower_comm_manager.disable_auto_query()
        beauty_print("Disabled follower auto query during teleoperation", type="info")

    stop_event = threading.Event()
    input_thread = threading.Thread(target=wait_for_enter, args=(stop_event,), daemon=True)

    try:
        beauty_print("Disabling leader arm torque for free movement...", type="info")
        input_thread.start()

        interval = 1.0 / args.frequency
        spin_threshold = 0.002 if interval <= 0.010 else 0.010
        loop_count = 0
        speed = 0 if args.mit else args.speed

        while not stop_event.is_set():
            loop_start = time.perf_counter()

            state = leader.get_robot_state("joint_gripper")
            if state is None or state.angles is None:
                precise_sleep(interval, spin_threshold=spin_threshold)
                continue

            follower.set_robot_state(
                target_joints=map_joints(state.angles),
                gripper_value=map_gripper(state.gripper),
                joint_format='rad',
                speed=speed,
                gripper_speed=speed,
                wait_for_completion=False,
            )

            loop_count += 1
            if args.verbose and loop_count % max(1, int(args.frequency)) == 0:
                deg = np.round(np.degrees(state.angles), 1).tolist()
                print(f"  [{loop_count:6d}] joints={deg}  gripper={state.gripper:.0f}")

            elapsed = time.perf_counter() - loop_start
            precise_sleep(interval - elapsed, spin_threshold=spin_threshold)
    except KeyboardInterrupt:
        print()
    finally:
        stop_event.set()
        beauty_print("Re-enabling leader arm torque...", type="info")
        leader.torque_control('on')
        beauty_print("Disconnecting...", type="info")
        leader.disconnect()
        follower.disconnect()
        beauty_print("Done", type="success")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Teleoperation: Alicia-D (Leader) → Alicia-M (Follower)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('--leader-port', type=str, default="",
                        help="Serial port for leader arm (Alicia-D). Auto-detect if empty.")
    parser.add_argument('--follower-port', type=str, default="",
                        help="Serial port for follower arm (Alicia-M). Auto-detect if empty.")
    parser.add_argument('--follower-version', type=str, default="v1_1",
                        help="Alicia-M version (default: v1_1)")
    parser.add_argument('--frequency', type=float, default=60.0,
                        help="Control loop frequency in Hz (default: 60)")
    parser.add_argument('--speed', type=float, default=573.0,
                        help="Follower joint speed in deg/s (default: 573, ~10 rad/s for real-time following)")
    parser.add_argument('--skip-home', action='store_true',
                        help="Skip moving follower to home position before starting")
    parser.add_argument('--mit', action='store_true',
                        help="Use MIT position mode instead of PV mode (better real-time tracking)")
    parser.add_argument('--verbose', '-v', action='store_true',
                        help="Print joint states during teleoperation")

    main(parser.parse_args())
