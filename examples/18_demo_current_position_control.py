"""验证 0x06/0x22：当前版本只对 ID3 进行重力前馈 + 低增益 PD 电流位置控制。"""

import argparse
import time

from alicia_d_sdk.hardware.servo_driver import ServoDriver


def print_status(title: str, status: dict) -> None:
    print(
        f"{title}: state={status['state_name']} fault={status['fault_name']} "
        f"targets={status['targets']} ID3_actual={status['actual_id3']} "
        f"ID2_current={status['current_id2']} "
        f"ID3_error={status['error_id3_ticks']} ID3_current={status['current_id3']} "
        f"ID3_G={status['gravity_current_id3']} ID3_PD={status['pd_current_id3']} "
        f"ID3_BIAS={status['bias_current_id3']} "
        f"ID5_actual={status['actual_id5']} ID5_error={status['error_id5_ticks']} "
        f"ID5_current={status['current_id5']}"
    )


def signed_current_bar(value: int, limit: int = 900, width: int = 17) -> str:
    """用中线表示 0，左侧为负电流，右侧为正电流。"""
    value = max(-limit, min(limit, value))
    center = width // 2
    cells = [" "] * width
    cells[center] = "|"

    if value < 0:
        count = round(abs(value) / limit * center)
        for index in range(center - count, center):
            cells[index] = "<"
    elif value > 0:
        count = round(value / limit * center)
        for index in range(center + 1, center + 1 + count):
            cells[index] = ">"
    return "".join(cells)


def current_breakdown(status: dict) -> str:
    """显示 ID3 的重力基线、位置额外电流和实际输出电流。"""
    gravity = status["gravity_current_id3"]
    position_pd = status["pd_current_id3"]
    bias = status["bias_current_id3"]
    command = gravity + position_pd + bias
    output = status["current_id3"]
    return (
        f"G={gravity:+4d}[{signed_current_bar(gravity)}] "
        f"PD={position_pd:+4d}[{signed_current_bar(position_pd)}] "
        f"BIAS={bias:+4d} CMD={command:+4d} OUT={output:+4d}[{signed_current_bar(output)}]"
    )


def print_id3_progress(start: int, target: int, status: dict, tolerance: int) -> None:
    """在终端单行显示 ID3 从锁存起点到目标位置的实时进度。"""
    actual = status["actual_id3"]
    error = status["error_id3_ticks"]
    distance = target - start
    width = 28

    progress = 1.0 if distance == 0 else (actual - start) / distance
    progress = max(0.0, min(1.0, progress))
    completed = int(round(progress * width))
    bar = "#" * completed + "." * (width - completed)
    state_text = "已到位" if abs(error) <= tolerance else "移动中"
    print(
        f"\rID3 [{bar}] {progress * 100:6.1f}%  "
        f"actual={actual:4d} target={target:4d} err={error:+4d} "
        f"{state_text}\n"
        f"    {current_breakdown(status)}",
        end="",
        flush=True,
    )


def main(args: argparse.Namespace) -> None:
    driver = ServoDriver(port=args.port, debug_mode=args.debug)
    armed = False
    try:
        if not driver.connect():
            raise RuntimeError("串口连接失败")

        status = driver.get_current_position_control_status(timeout=args.timeout)
        if status is None:
            raise RuntimeError("未收到 0x06/0x22 初始状态回包，请确认已烧录最新固件")
        print_status("初始状态", status)

        status = driver.enable_current_position_control(timeout=args.timeout)
        if status is None:
            raise RuntimeError("未收到开启回包")
        armed = True
        print_status("锁存当前姿态", status)

        targets = args.targets
        if args.id3_offset is not None:
            if abs(args.id3_offset) > 50 and not args.allow_large_offset:
                raise ValueError(
                    "当前仅允许 -50~+50 tick 的 ID3 相对测试；"
                    "大偏移会在未完成安全验证的控制器下产生危险动作。"
                )
            targets = list(status["targets"])
            targets[2] += args.id3_offset
            if targets[2] < 0 or targets[2] > 4095:
                raise ValueError(f"ID3 相对目标越界: {targets[2]}")
            print(f"ID3 相对当前锁存值偏移 {args.id3_offset:+d} tick: {targets[2]}")

        if targets is None:
            print("未指定 --targets：只验证模式切换和安全退出，不要求机械臂移动。")
            return

        # 分段目标只用于 ID3 相对偏移测试：其余关节一直保持锁存值。
        target_sequence = [list(targets)]
        if args.id3_step:
            if args.id3_offset is None:
                raise ValueError("--id3-step 只能与 --id3-offset 一起使用")
            start_id3 = status["targets"][2]
            final_id3 = targets[2]
            direction = 1 if final_id3 >= start_id3 else -1
            next_id3 = start_id3
            target_sequence = []
            while next_id3 != final_id3:
                remaining = abs(final_id3 - next_id3)
                next_id3 += direction * min(args.id3_step, remaining)
                stage_targets = list(targets)
                stage_targets[2] = next_id3
                target_sequence.append(stage_targets)
            print(
                f"ID3 分段轨迹: {start_id3} -> {final_id3}，"
                f"每段最多 {args.id3_step} tick，共 {len(target_sequence)} 段"
            )

        stage_index = 0
        active_targets = target_sequence[stage_index]
        status = driver.set_current_position_targets(active_targets, timeout=args.timeout)
        if status is None:
            raise RuntimeError("未收到目标更新回包")
        if status["fault_name"] != "NONE":
            raise RuntimeError(f"板端拒绝目标: {status['fault_name']}")
        print_status(f"目标已写入（第 {stage_index + 1}/{len(target_sequence)} 段）", status)
        print(f"开始保持 {args.hold_time:.1f} 秒。请托住机械臂，观察 ID3 主动运动和 ID5 是否稳定。")

        id3_start = status["actual_id3"]
        id3_target = active_targets[2]
        reached_samples = 0
        reached_once = False

        deadline = time.monotonic() + args.hold_time
        while time.monotonic() < deadline:
            time.sleep(0.2)
            status = driver.get_current_position_control_status(timeout=args.timeout)
            if status is None:
                raise RuntimeError("保持期间未收到状态回包")
            if status["state_name"] == "FAULT":
                raise RuntimeError(f"控制已安全退出: {status['fault_name']}")
            if abs(status["error_id3_ticks"]) <= args.reach_tolerance:
                reached_once = True
            if reached_once and abs(status["error_id3_ticks"]) > args.post_reach_max_error:
                raise RuntimeError(
                    "ID3 已到位后误差再次扩大到 "
                    f"{status['error_id3_ticks']} tick，已自动停止测试"
                )
            if args.visual:
                print_id3_progress(id3_start, id3_target, status, args.reach_tolerance)
            else:
                print_status("运行中", status)

            stage_ready = (
                abs(status["error_id3_ticks"]) <= args.stage_tolerance
                and abs(status["current_id3"]) <= args.stage_max_current
            )
            if stage_ready:
                reached_samples += 1
            else:
                reached_samples = 0

            # 连续三次误差小且电流已退到保持范围，才切换下一小段。
            if stage_index < len(target_sequence) - 1 and reached_samples >= 3:
                stage_index += 1
                active_targets = target_sequence[stage_index]
                status = driver.set_current_position_targets(active_targets, timeout=args.timeout)
                if status is None:
                    raise RuntimeError("未收到下一段目标回包")
                if status["fault_name"] != "NONE":
                    raise RuntimeError(f"板端拒绝下一段目标: {status['fault_name']}")
                if args.visual:
                    print()
                print_status(f"切换第 {stage_index + 1}/{len(target_sequence)} 段", status)
                id3_start = status["actual_id3"]
                id3_target = active_targets[2]
                reached_samples = 0
        if args.visual:
            print()
            print_status("保持结束", status)
        if stage_index < len(target_sequence) - 1:
            raise RuntimeError("保持时间结束，但分段轨迹尚未完成")
    finally:
        if armed and driver.serial_comm.is_connected():
            status = driver.disable_current_position_control(timeout=args.timeout)
            if status is not None:
                print_status("关闭确认", status)
        driver.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="0x06/0x22 ID3 电流模式位置控制测试")
    parser.add_argument("--port", default="COM11")
    parser.add_argument("--timeout", type=float, default=1.0)
    parser.add_argument("--hold-time", type=float, default=30.0)
    target_group = parser.add_mutually_exclusive_group()
    target_group.add_argument("--targets", type=int, nargs=6, metavar=("ID1", "ID2", "ID3", "ID4", "ID5", "ID6"))
    target_group.add_argument("--id3-offset", type=int, help="相对当前锁存姿态，仅修改 ID3 目标的 tick 偏移")
    parser.add_argument("--visual", action="store_true", help="终端实时显示 ID3 位置进度条")
    parser.add_argument("--reach-tolerance", type=int, default=3, help="判定 ID3 到位的允许误差 tick，默认 3")
    parser.add_argument(
        "--post-reach-max-error",
        type=int,
        default=30,
        help="已到位后允许再次偏离的最大误差 tick，超过后自动关闭，默认 30",
    )
    parser.add_argument("--id3-step", type=int, default=0, help="将 ID3 相对目标拆为若干小段；0 表示不分段")
    parser.add_argument("--stage-tolerance", type=int, default=6, help="分段切换的 ID3 最大误差 tick，默认 6")
    parser.add_argument("--stage-max-current", type=int, default=450, help="分段切换前允许的 ID3 最大电流绝对值，默认 450")
    parser.add_argument("--allow-large-offset", action="store_true", help="允许超过 50 tick 的危险 ID3 相对测试")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    if args.hold_time <= 0:
        parser.error("--hold-time 必须大于 0")
    if args.targets is not None and any(value < 0 or value > 4095 for value in args.targets):
        parser.error("--targets 的六个位置必须在 0~4095")
    if args.reach_tolerance < 0:
        parser.error("--reach-tolerance 不能为负数")
    if args.post_reach_max_error <= args.reach_tolerance:
        parser.error("--post-reach-max-error 必须大于 --reach-tolerance")
    if args.stage_tolerance < 0:
        parser.error("--stage-tolerance 不能为负数")
    if args.stage_max_current < 0:
        parser.error("--stage-max-current 不能为负数")
    if args.id3_step < 0:
        parser.error("--id3-step 不能为负数")
    if args.id3_step > 50:
        parser.error("--id3-step 在当前安全阶段不能超过 50")
    if args.id3_step and (args.id3_offset is None or args.id3_offset == 0):
        parser.error("--id3-step 需要配合非零的 --id3-offset")
    main(args)
