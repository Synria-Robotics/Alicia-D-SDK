"""ID3 电流位置模式的连续行程测试。

总行程可以较大，但每次只下发一个安全的小目标；每段到位并稳定后才继续。
"""

import argparse
import time

from alicia_d_sdk.hardware.servo_driver import ServoDriver


def print_status(prefix: str, status: dict) -> None:
    """打印足够判断到位、重力项和积分项的关键状态。"""
    print(
        f"{prefix}: state={status['state_name']} fault={status['fault_name']} "
        f"ID2_I={status['current_id2']:+d} "
        f"ID3 actual={status['actual_id3']} target={status['targets'][2]} "
        f"error={status['error_id3_ticks']:+d} current={status['current_id3']:+d} "
        f"G={status['gravity_current_id3']:+d} "
        f"PD={status['pd_current_id3']:+d} BIAS={status['bias_current_id3']:+d}"
    )


def wait_until_stage_reached(
    driver: ServoDriver,
    args: argparse.Namespace,
    stage_index: int,
    stage_count: int,
    travel_direction: int,
) -> dict:
    """等待当前小段稳定到位；只以位置误差判断，不要求保持电流变小。"""
    deadline = time.monotonic() + args.stage_timeout
    settled_samples = 0
    latest_status = None

    while time.monotonic() < deadline:
        time.sleep(args.poll_period)
        status = driver.get_current_position_control_status(timeout=args.timeout)
        if status is None:
            raise RuntimeError("行程测试期间未收到 0x22 状态回包")
        if status["state_name"] == "FAULT":
            raise RuntimeError(f"板端进入故障状态: {status['fault_name']}")

        latest_status = status
        print_status(f"第 {stage_index}/{stage_count} 段", status)
        overshoot_ticks = -status["error_id3_ticks"] * travel_direction
        if overshoot_ticks > args.max_stage_overshoot:
            raise RuntimeError(
                f"第 {stage_index}/{stage_count} 段越过目标 {overshoot_ticks} tick，已安全停止测试"
            )
        if abs(status["error_id3_ticks"]) <= args.tolerance:
            settled_samples += 1
            if settled_samples >= args.settle_samples:
                return status
        else:
            settled_samples = 0

    if latest_status is None:
        raise RuntimeError("行程测试未获取到 ID3 状态")
    raise RuntimeError(
        f"第 {stage_index}/{stage_count} 段在 {args.stage_timeout:.1f} 秒内未到位，"
        f"最后误差={latest_status['error_id3_ticks']:+d} tick"
    )


def main(args: argparse.Namespace) -> None:
    driver = ServoDriver(port=args.port, debug_mode=args.debug)
    enabled = False

    try:
        if not driver.connect():
            raise RuntimeError("串口连接失败")

        initial = driver.enable_current_position_control(timeout=args.timeout)
        if initial is None:
            raise RuntimeError("未收到 0x22 开启回包，请确认已烧录支持电流位置控制的固件")
        enabled = True
        start_id3 = initial["targets"][2]
        print_status("锁存当前姿态", initial)

        final_id3 = start_id3 + args.travel
        if final_id3 < 0 or final_id3 > 4095:
            raise ValueError(
                f"ID3 目标 {final_id3} 超出单圈有效范围 0~4095；"
                "请先用普通位置模式回到安全区间后再测试。"
            )

        direction = 1 if args.travel > 0 else -1
        stage_count = (abs(args.travel) + args.segment_ticks - 1) // args.segment_ticks
        stage_target = start_id3
        print(
            f"ID3 连续行程: {start_id3} -> {final_id3}，总计 {args.travel:+d} tick，"
            f"每段最多 {args.segment_ticks} tick，共 {stage_count} 段。"
        )
        print("请全程托住机械臂；任意异常立即 Ctrl+C，脚本会发送关闭指令。")

        if args.continuous:
            targets = list(initial["targets"])
            targets[2] = final_id3

            status = driver.set_current_position_targets(targets, timeout=args.timeout)
            if status is None:
                raise RuntimeError("连续目标未收到目标回包")
            if status["fault_name"] != "NONE":
                raise RuntimeError(f"连续目标被板端拒绝: {status['fault_name']}")
            print_status("连续目标已下发", status)
            wait_until_stage_reached(driver, args, 1, 1, direction)
        else:
            for stage_index in range(1, stage_count + 1):
                remaining = abs(final_id3 - stage_target)
                stage_target += direction * min(args.segment_ticks, remaining)
                targets = list(initial["targets"])
                targets[2] = stage_target

                status = driver.set_current_position_targets(targets, timeout=args.timeout)
                if status is None:
                    raise RuntimeError(f"第 {stage_index}/{stage_count} 段未收到目标回包")
                if status["fault_name"] != "NONE":
                    raise RuntimeError(f"第 {stage_index}/{stage_count} 段被板端拒绝: {status['fault_name']}")
                print_status(f"下发第 {stage_index}/{stage_count} 段", status)
                wait_until_stage_reached(
                    driver,
                    args,
                    stage_index,
                    stage_count,
                    direction,
                )

        if args.keep_holding:
            print("已到最终目标：将持续保留重力补偿和保持电流。按 Ctrl+C 才会关闭控制。")
            hold_deadline = None
        else:
            print(f"已到最终目标，继续保持 {args.final_hold:.1f} 秒观察是否回落。")
            hold_deadline = time.monotonic() + args.final_hold

        while hold_deadline is None or time.monotonic() < hold_deadline:
            time.sleep(args.poll_period)
            status = driver.get_current_position_control_status(timeout=args.timeout)
            if status is None:
                raise RuntimeError("最终保持期间未收到状态回包")
            if status["state_name"] == "FAULT":
                raise RuntimeError(f"最终保持期间故障: {status['fault_name']}")
            print_status("最终保持", status)
            if abs(status["error_id3_ticks"]) > args.post_reach_max_error:
                raise RuntimeError(
                    f"最终到位后误差扩大到 {status['error_id3_ticks']:+d} tick，已停止测试"
                )
    finally:
        if enabled and driver.serial_comm.is_connected():
            status = driver.disable_current_position_control(timeout=args.timeout)
            if status is not None:
                print_status("关闭确认", status)
        driver.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="0x06/0x22 ID3 连续工作区行程测试")
    parser.add_argument("--port", default="COM11")
    parser.add_argument("--timeout", type=float, default=1.0)
    parser.add_argument("--travel", type=int, required=True, help="ID3 相对锁存位置的总行程 tick，例如 300 或 -300")
    parser.add_argument("--segment-ticks", type=int, default=25, help="每一小段的最大目标变化，默认 25")
    parser.add_argument("--continuous", action="store_true", help="一次下发最终目标，由板端内部轨迹连续限速")
    parser.add_argument("--stage-timeout", type=float, default=15.0, help="单段允许的最长到位时间，默认 15 秒")
    parser.add_argument("--tolerance", type=int, default=3, help="单段到位误差，默认 ±3 tick")
    parser.add_argument("--settle-samples", type=int, default=3, help="连续到位采样次数，默认 3")
    parser.add_argument("--poll-period", type=float, default=0.2, help="状态轮询间隔，默认 0.2 秒")
    parser.add_argument("--final-hold", type=float, default=10.0, help="最终目标的观察时间，默认 10 秒")
    parser.add_argument(
        "--keep-holding",
        action="store_true",
        help="到位后持续保持重力补偿和位置保持，直到 Ctrl+C 才关闭",
    )
    parser.add_argument("--post-reach-max-error", type=int, default=30, help="最终到位后允许的最大误差，默认 30")
    parser.add_argument("--max-stage-overshoot", type=int, default=12, help="单段越过目标的安全上限，默认 12 tick")
    parser.add_argument("--allow-large-travel", action="store_true", help="允许 600~1000 tick 的总行程")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    if args.travel == 0:
        parser.error("--travel 不能为 0")
    if abs(args.travel) > 1000:
        parser.error("ID3 单次总行程不能超过 ±1000 tick")
    if abs(args.travel) > 600 and not args.allow_large_travel:
        parser.error("超过 ±600 tick 的大行程需要明确使用 --allow-large-travel")
    if not args.continuous and (args.segment_ticks <= 0 or args.segment_ticks > 40):
        parser.error("--segment-ticks 必须在 1~40，确保每次目标更新小于板端 50 tick 限制")
    if args.stage_timeout <= 0 or args.final_hold < 0 or args.poll_period <= 0:
        parser.error("时间参数必须为正数，--final-hold 可以为 0")
    if args.tolerance < 0 or args.settle_samples <= 0:
        parser.error("到位参数无效")
    if args.post_reach_max_error <= args.tolerance:
        parser.error("--post-reach-max-error 必须大于 --tolerance")
    if args.max_stage_overshoot <= args.tolerance:
        parser.error("--max-stage-overshoot 必须大于 --tolerance")

    main(args)
