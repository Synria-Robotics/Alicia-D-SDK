# Copyright (c) 2026 Synria Robotics Co., Ltd.
# Licensed under the MIT License.

"""Demo: HLS direct current input and six-axis current diagnostics."""

import argparse
import sys
import time
from pathlib import Path

import serial.tools.list_ports


SDK_ROOT = Path(__file__).resolve().parents[1]
sdk_root = str(SDK_ROOT)
if sdk_root in sys.path:
    sys.path.remove(sdk_root)
sys.path.insert(0, sdk_root)

import alicia_d_sdk
from alicia_d_sdk.utils.logger import logger


JOINT_COUNT = 6
MAX_CURRENT_MA = 6000


def _parse_currents(args):
    if args.currents:
        currents = [int(value.strip(), 0) for value in args.currents.split(",")]
        if len(currents) != JOINT_COUNT:
            raise ValueError("--currents 必须刚好包含 6 个逗号分隔的 mA 值")
    else:
        currents = [0] * JOINT_COUNT
        currents[args.joint - 1] = args.current_ma

    for current in currents:
        if current < -MAX_CURRENT_MA or current > MAX_CURRENT_MA:
            raise ValueError(f"电流 {current}mA 超出 +/-{MAX_CURRENT_MA}mA")
    return currents


def _show_diagnostics(label, diagnostics, ack=None):
    if diagnostics is None:
        logger.warning(f"{label}：未收到 0x06/0x24 诊断")
        return

    axes = diagnostics.get("axes", [])
    axis_text = " ".join(
        f"J{axis['joint']} out={axis['output_current_a']:+.3f}A "
        f"meas={axis['measured_current_a']:+.3f}A"
        for axis in axes
    )
    ack_text = ""
    if ack is not None:
        ack_text = (
            f"，ACK accepted={ack.get('accepted')} "
            f"result={ack.get('result')} mask=0x{ack.get('accepted_mask', 0):02X}"
        )
    logger.info(
        f"{label}：mode={diagnostics.get('mode')} "
        f"valid=0x{diagnostics.get('feedback_valid_mask', 0):02X}"
        f"{ack_text} | {axis_text}"
    )


def _stop_safely(robot, leave_current_mode=False):
    logger.info("安全收尾：发送 0mA、关闭扭矩。")
    zero = [0] * JOINT_COUNT
    for _ in range(5):
        try:
            robot.set_direct_current(zero, timeout=0.2)
        except Exception:
            pass
        time.sleep(0.02)

    robot.torque_control("off", timeout=1.0)
    if not leave_current_mode:
        if robot.set_control_mode("position", timeout=2.0):
            logger.info("已切回 position 模式。")
        else:
            logger.warning("未确认切回 position 模式，请重新上电或再次检查模式。")


def _available_ports_text():
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        return "未发现串口"
    return "；".join(f"{port.device} {port.description}" for port in ports)


def main(args):
    currents = _parse_currents(args)
    if args.period >= 0.10:
        raise ValueError("--period 必须小于 0.10 秒，固件直控电流刷新超时为 100ms")

    logger.info(f"当前 SDK 路径：{Path(alicia_d_sdk.__file__).resolve()}")
    logger.info(f"目标电流 mA：{currents}")
    logger.warning(
        "直控电流会让对应关节产生力矩，请先用小电流测试，并确认运动范围内无人和障碍物。"
    )
    if not args.no_prompt:
        input("确认安全后按 Enter 开始；按 Ctrl+C 取消...")

    try:
        robot = alicia_d_sdk.create_robot(port=args.port)
    except Exception as exc:
        logger.warning(f"串口连接失败：{exc}")
        logger.warning(f"当前可见串口：{_available_ports_text()}")
        logger.warning(
            "请关闭串口助手/其它占用程序，重新插拔 CH343/USB 转串口，"
            "确认设备管理器中端口状态正常后再运行。"
        )
        raise SystemExit(2)

    try:
        _show_diagnostics("初始诊断", robot.get_hls_current_diagnostics(timeout=1.0))

        logger.info("切换到 current 模式。")
        if not robot.set_control_mode("current", timeout=3.0):
            raise RuntimeError("切换 current 模式失败")

        logger.info("开启扭矩。")
        if not robot.torque_control("on", timeout=1.0):
            raise RuntimeError("扭矩开启命令发送失败")
        time.sleep(0.20)

        deadline = time.monotonic() + args.duration
        last_print = 0.0
        while time.monotonic() < deadline:
            cycle_started = time.monotonic()
            ack = robot.set_direct_current(currents, timeout=args.timeout)
            diagnostics = robot.get_hls_current_diagnostics(timeout=args.timeout)
            now = time.monotonic()
            if ack is None:
                logger.warning("未收到 0x05/0x02 直控电流 ACK")
            elif not ack.get("accepted", False):
                logger.warning(f"直控电流被拒绝：{ack}")
            if now - last_print >= args.print_period:
                _show_diagnostics("运行中", diagnostics, ack)
                last_print = now

            remaining = args.period - (time.monotonic() - cycle_started)
            if remaining > 0:
                time.sleep(remaining)
    finally:
        _stop_safely(robot, leave_current_mode=args.leave_current_mode)
        robot.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="输入指定 HLS 关节电流，并监视六轴输出/测量电流"
    )
    parser.add_argument("--port", type=str, default="", help="串口，例如 COM11")
    parser.add_argument("--joint", type=int, default=2, choices=range(1, 7))
    parser.add_argument("--current-ma", type=int, default=300)
    parser.add_argument(
        "--currents",
        help="六轴 mA 值，例如 0,300,0,0,0,0；设置后覆盖 --joint/--current-ma",
    )
    parser.add_argument("--duration", type=float, default=5.0, help="运行时长，秒")
    parser.add_argument("--period", type=float, default=0.05, help="电流刷新周期，秒")
    parser.add_argument("--print-period", type=float, default=0.20, help="打印周期，秒")
    parser.add_argument("--timeout", type=float, default=0.2, help="单次回包超时，秒")
    parser.add_argument("--leave-current-mode", action="store_true")
    parser.add_argument("--no-prompt", action="store_true")
    main(parser.parse_args())
