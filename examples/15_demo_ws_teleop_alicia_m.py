#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""WebSocket Teleoperation Demo: Alicia-D (WS) -> Alicia-M (WS)

Leader:
    Send {"type": "get.state"} to the leader WebSocket at the configured rate.

Follower:
    Send {"type": "cmd.movej", "joints_deg": [...], "gripper": ..., "speed": ...}
    to the follower WebSocket.
"""

import argparse
import asyncio
import builtins
from datetime import datetime
import json
import threading
import time
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

import numpy as np
import websockets
from robocore.utils.beauty_logger import beauty_print


def install_timestamped_print():
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


def extract_device_id_from_ws_url(ws_url):
    parsed = urlparse(ws_url)
    marker = "/robots/ws/"
    if marker not in parsed.path:
        raise ValueError(f"Invalid WebSocket URL: {ws_url}")
    return unquote(parsed.path.split(marker, 1)[1])


def connect_device_via_rest(ws_url, arm_type):
    parsed = urlparse(ws_url)
    http_scheme = "https" if parsed.scheme == "wss" else "http"
    base_url = f"{http_scheme}://{parsed.netloc}"
    device_id = extract_device_id_from_ws_url(ws_url)
    payload = json.dumps({
        "arm_type": arm_type,
        "device_id": device_id,
    }).encode("utf-8")
    request = Request(
        f"{base_url}/robots/connect",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=5.0) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)


def map_joints(leader_joints_deg):
    joint_signs = [1.0, 1.0, -1.0, -1.0, 1.0, -1.0]
    return [sign * angle for angle, sign in zip(leader_joints_deg, joint_signs)]


def map_gripper(leader_gripper):
    return max(0.0, min(1000.0, float(leader_gripper)))


def wait_for_enter(stop_event):
    try:
        input("\nWS teleoperation active. Press Enter to stop...\n")
    except KeyboardInterrupt:
        print()
    finally:
        stop_event.set()


async def recv_json(ws):
    raw = await ws.recv()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw)


async def expect_hello(ws, role):
    hello = await recv_json(ws)
    if hello.get("type") != "hello":
        raise RuntimeError(f"Unexpected {role} hello message: {hello}")
    beauty_print(f"{role} WebSocket connected: {hello.get('device_id', 'unknown')}", type="success")


async def main_async(args):
    install_timestamped_print()
    beauty_print("WebSocket Teleoperation: Alicia-D (WS) -> Alicia-M (WS)", type="module")

    leader_device_id = extract_device_id_from_ws_url(args.leader_ws)
    follower_device_id = extract_device_id_from_ws_url(args.follower_ws)
    if leader_device_id == follower_device_id:
        raise RuntimeError(f"Leader and follower must not be the same device: {leader_device_id}")

    beauty_print(f"Registering leader in backend: {leader_device_id}", type="info")
    leader_connect_result = await asyncio.to_thread(connect_device_via_rest, args.leader_ws, "alicia_d")
    beauty_print(f"Leader backend registration OK: {leader_connect_result.get('device_id', leader_device_id)}", type="success")

    beauty_print(f"Registering follower in backend: {follower_device_id}", type="info")
    follower_connect_result = await asyncio.to_thread(connect_device_via_rest, args.follower_ws, "alicia_m")
    beauty_print(f"Follower backend registration OK: {follower_connect_result.get('device_id', follower_device_id)}", type="success")

    if args.mit:
        beauty_print("Warning: follower WS cmd.movej path currently does not enable a dedicated MIT control path; speed will still be sent normally.", type="warning")

    beauty_print(f"Connecting leader WebSocket: {args.leader_ws}", type="info")
    beauty_print(f"Connecting follower WebSocket: {args.follower_ws}", type="info")

    async with websockets.connect(args.leader_ws, ping_interval=None) as leader_ws:
        async with websockets.connect(args.follower_ws, ping_interval=None) as follower_ws:
            await expect_hello(leader_ws, "Leader")
            await expect_hello(follower_ws, "Follower")

            if not args.skip_home:
                beauty_print("Sending follower home command via WebSocket...", type="info")
                await follower_ws.send(json.dumps({
                    "type": "cmd.movej",
                    "joints_deg": [0.0] * 6,
                    "gripper": 0.0,
                    "speed": 20.0,
                }))
                home_reply = await recv_json(follower_ws)
                if home_reply.get("type") != "movej.ok":
                    raise RuntimeError(f"Follower home command failed: {home_reply}")
                beauty_print("Follower home command accepted", type="success")
                await asyncio.sleep(2.0)

            beauty_print(f"Starting WS teleoperation at {args.frequency} Hz (cmd.movej speed={args.speed})", type="module")
            beauty_print("Leader state is polled from WebSocket and forwarded to follower WebSocket")
            beauty_print("Press Enter or Ctrl+C to stop\n")

            stop_event = threading.Event()
            input_thread = threading.Thread(target=wait_for_enter, args=(stop_event,), daemon=True)
            input_thread.start()

            interval = 1.0 / args.frequency
            loop_count = 0

            while not stop_event.is_set():
                loop_start = time.perf_counter()

                await leader_ws.send(json.dumps({"type": "get.state"}))
                leader_msg = await recv_json(leader_ws)

                if leader_msg.get("type") == "state":
                    joints_deg = leader_msg.get("joints_deg")
                    gripper = leader_msg.get("gripper", 0.0)
                    if joints_deg is not None and len(joints_deg) >= 6:
                        follower_cmd = {
                            "type": "cmd.movej",
                            "joints_deg": map_joints(joints_deg[:6]),
                            "gripper": map_gripper(gripper),
                            "speed": args.speed,
                        }
                        await follower_ws.send(json.dumps(follower_cmd))
                        follower_reply = await recv_json(follower_ws)
                        if follower_reply.get("type") != "movej.ok":
                            beauty_print(f"Follower move error: {follower_reply}", type="warning")

                        loop_count += 1
                        if args.verbose and loop_count % max(1, int(args.frequency)) == 0:
                            deg = np.round(joints_deg[:6], 1).tolist()
                            print(f"  [{loop_count:6d}] joints={deg}  gripper={gripper:.0f}")
                elif leader_msg.get("type") == "state.error":
                    beauty_print(f"Leader state error: {leader_msg.get('msg', 'unknown error')}", type="warning")

                elapsed = time.perf_counter() - loop_start
                await asyncio.sleep(max(0.0, interval - elapsed))


def main():
    parser = argparse.ArgumentParser(
        description="WebSocket Teleoperation: Alicia-D (WS) -> Alicia-M (WS)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        '--leader-ws',
        type=str,
        default="ws://localhost:8000/robots/ws//dev/cu.usbmodem5B7B0460781",
        help="Leader WebSocket URL.",
    )
    parser.add_argument(
        '--follower-ws',
        type=str,
        required=True,
        help="Follower WebSocket URL.",
    )
    parser.add_argument('--frequency', type=float, default=60.0,
                        help="WebSocket poll/control loop frequency in Hz (default: 60)")
    parser.add_argument('--speed', type=float, default=200,
                        help="Follower cmd.movej speed (default: 573)")
    parser.add_argument('--skip-home', action='store_true',
                        help="Skip sending follower home command before starting")
    parser.add_argument('--mit', action='store_true',
                        help="Retained for compatibility; follower WS cmd.movej path does not enable dedicated MIT handling")
    parser.add_argument('--verbose', '-v', action='store_true',
                        help="Print leader joint states once per second")

    asyncio.run(main_async(parser.parse_args()))


if __name__ == "__main__":
    main()
