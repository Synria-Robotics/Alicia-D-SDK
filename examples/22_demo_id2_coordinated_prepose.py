"""0x06/0x22：先由 ID3 降低 ID2 力臂，再执行 ID2 小行程测试。"""

import argparse
import time

from alicia_d_sdk.hardware.servo_driver import ServoDriver


class EncoderPositionTracker:
    """将 12 位环形编码器值展开为相对锁存姿态的连续 tick 位移。"""

    def __init__(self) -> None:
        self._previous_raw: int | None = None
        self._continuous: int = 0
        self._origin: int = 0

    def update(self, raw_position: int) -> tuple[int, int]:
        raw_position &= 0x0FFF
        if self._previous_raw is None:
            self._previous_raw = raw_position
            self._continuous = raw_position
            self._origin = raw_position
        else:
            delta = (raw_position - self._previous_raw + 2048) % 4096 - 2048
            self._continuous += delta
            self._previous_raw = raw_position
        return self._continuous, self._continuous - self._origin


def print_status(prefix: str, status: dict, args: argparse.Namespace | None = None) -> None:
    """打印协同预备阶段最需要关注的 ID2/ID3 状态。"""
    id2_motion = ""
    if args is not None:
        id2_actual_continuous, id2_actual_delta = args.id2_actual_tracker.update(
            status["actual_id2"]
        )
        id2_target_continuous, id2_target_delta = args.id2_target_tracker.update(
            status["targets"][1]
        )
        id2_motion = (
            f" | ID2_CONT actual={id2_actual_continuous} (d={id2_actual_delta:+d}) "
            f"target={id2_target_continuous} (d={id2_target_delta:+d})"
        )
    message = (
        f"{prefix}: state={status['state_name']} fault={status['fault_name']} | "
        f"ID2 actual={status['actual_id2']} target={status['targets'][1]} "
        f"err={status['error_id2_ticks']:+d} I={status['current_id2']:+d} "
        f"G={status['gravity_current_id2']:+d} PD={status['pd_current_id2']:+d} "
        f"BIAS={status['bias_current_id2']:+d} | "
        f"ID3 actual={status['actual_id3']} target={status['targets'][2]} "
        f"err={status['error_id3_ticks']:+d} I={status['current_id3']:+d} "
        f"G={status['gravity_current_id3']:+d} "
        f"PD={status['pd_current_id3']:+d} "
        f"BIAS={status['bias_current_id3']:+d}"
    )
    message += id2_motion
    if status.get("id3_reference") is not None:
        flags = status.get("id3_control_flags", 0)
        message += (
            f" | ID3_REF={status['id3_reference']} "
            f"CTRL_ERR={status['id3_control_error_ticks']:+d} "
            f"V={status['id3_filtered_velocity_ticks_per_second']:+d}tick/s "
            f"INT={status['id3_integral_current']:+d} "
            f"BREAK={status['id3_breakaway_current']:+d} "
            f"STALL={status.get('id3_stall_cycles', 0)} "
            f"CTRL={int(bool(flags & 0x01))} "
            f"FINAL={int(bool(flags & 0x02))} "
            f"STUCK={int(bool(flags & 0x04))} "
            f"INT_BLOCK={int(bool(flags & 0x08))}"
        )
    print(message)


def wait_for_id3_prepose(
    driver: ServoDriver, args: argparse.Namespace, stage_index: int, stage_count: int
) -> dict:
    """等待单个 ID3 预备小段到位；故障或超时由调用方安全关闭 0x22。"""
    deadline = time.monotonic() + args.prepose_timeout
    while time.monotonic() < deadline:
        time.sleep(args.poll_period)
        if args.debug_terms:
            status = driver.get_current_position_control_debug(timeout=args.timeout)
        else:
            status = driver.get_current_position_control_status(timeout=args.timeout)
        if status is None:
            raise RuntimeError("等待 ID3 预备姿态期间未收到 0x22 状态回包")
        print_status(f"ID3 预备第 {stage_index}/{stage_count} 段", status, args)
        if status["state_name"] == "FAULT":
            raise RuntimeError(
                f"ID3 预备第 {stage_index}/{stage_count} 段进入故障: "
                f"{status['fault_name']}"
            )
        if abs(status["error_id3_ticks"]) <= args.id3_tolerance:
            return status
    raise RuntimeError(
        f"ID3 预备第 {stage_index}/{stage_count} 段未在规定时间内到位，"
        "已停止后续 ID2 动作"
    )


def wait_for_arm_settle(driver: ServoDriver, args: argparse.Namespace) -> dict:
    """开启 0x22 后只保持锁存姿态，给启动瞬态留出消退时间。"""
    deadline = time.monotonic() + args.arm_settle_time
    status: dict | None = None
    while time.monotonic() < deadline:
        time.sleep(min(args.poll_period, max(0.0, deadline - time.monotonic())))
        if args.debug_terms:
            status = driver.get_current_position_control_debug(timeout=args.timeout)
        else:
            status = driver.get_current_position_control_status(timeout=args.timeout)
        if status is None:
            raise RuntimeError("启动稳定等待期间未收到 0x22 状态回包")
        print_status("启动稳定中（尚未下发 ID3 行程）", status, args)
        if status["state_name"] == "FAULT":
            raise RuntimeError(f"启动稳定期间板端进入故障状态: {status['fault_name']}")
    if status is None:
        raise RuntimeError("启动稳定等待没有获得板端状态")
    return status


def main(args: argparse.Namespace) -> None:
    driver = ServoDriver(port=args.port, debug_mode=args.debug)
    enabled = False
    args.id2_actual_tracker = EncoderPositionTracker()
    args.id2_target_tracker = EncoderPositionTracker()

    try:
        if not driver.connect():
            raise RuntimeError("串口连接失败")

        # 预览是纯读操作：先让用户看到模型建议，再决定是否给机械臂上电流。
        preview = driver.preview_current_position_id3_prepose(timeout=args.timeout)
        if preview is None:
            raise RuntimeError("未收到 ID3 预备姿态预览回包，请确认已刷入最新固件")
        if preview["fault_name"] != "NONE":
            raise RuntimeError(f"板端无法预览预备姿态: {preview['fault_name']}")

        prepose_target = preview["id3_prepose_target"]
        prepose_offset = preview["id3_prepose_offset_ticks"]
        predicted_gravity = preview["predicted_id2_gravity_current"]
        if prepose_target is None or prepose_offset is None or predicted_gravity is None:
            raise RuntimeError("预备姿态回包缺少候选数据")
        if prepose_offset == 0:
            raise RuntimeError("模型未找到可降低 ID2 重力负载的 ID3 预备姿态，本次不移动")
        model_prepose_offset = prepose_offset
        if args.id3_prepose_offset is not None:
            # 逐段扩大工作空间时，必须以本次锁存姿态为基准，不能再次自动走向模型的完整最优点。
            prepose_offset = args.id3_prepose_offset
            print(
                f"模型完整预备建议为 {model_prepose_offset:+d} tick；"
                f"本次按指定相对行程执行 {prepose_offset:+d} tick。"
            )
        elif abs(prepose_offset) > args.max_prepose_travel:
            # 完整模型最优点可能位于未验证的大行程区域。先走到已验证上限，
            # 后续仍以实时读到的 G_ID2 作为是否执行 ID2 的最终判断。
            prepose_offset = (
                args.max_prepose_travel if prepose_offset > 0 else -args.max_prepose_travel
            )
            print(
                "模型最优预备行程为 "
                f"{model_prepose_offset:+d} tick，超过当前安全验证上限；"
                f"本次只执行 {prepose_offset:+d} tick 的中间预备姿态。"
            )

        print(
            "板端只读预览完成："
            f"ID3 本次预备偏移 {prepose_offset:+d} tick；"
            f"完整模型最优点预测 ID2 重力电流 {predicted_gravity:+d}。"
        )
        print("当前仍是 OFF，不会输出电流。确认后才会开启 0x22；请先托住机械臂。")
        if input("确认开启 0x22 并进入 ID3 预备流程请输入 YES，其他输入取消: ").strip() != "YES":
            print("已取消，未执行 ID3 预备动作。")
            return

        status = driver.enable_current_position_control(timeout=args.timeout)
        if status is None:
            raise RuntimeError("未收到 0x22 开启回包，请确认已刷入协同预备姿态固件")
        enabled = True
        print_status("锁存当前姿态", status, args)

        if args.arm_settle_time > 0:
            print(
                f"已开启 0x22，先保持当前姿态 {args.arm_settle_time:.1f} 秒。"
                "这段时间不会下发 ID3 行程；请等待抖动消退。"
            )
            status = wait_for_arm_settle(driver, args)

        prepose_target = (status["targets"][2] + prepose_offset) % 4096
        print(
            f"启动稳定结束。本次 ID3 将从 {status['targets'][2]} 走到 {prepose_target}"
            f"（{prepose_offset:+d} tick）。"
        )
        if input("确认机械臂已稳定，现在开始 ID3 预备行程请输入 YES，其他输入取消: ").strip() != "YES":
            print("已取消，已安全关闭 0x22，未执行 ID3 预备行程。")
            return

        # 高负载姿态下不允许 ID3 一次走完数百 tick：分成小段，每段到位后再继续。
        stage_start = status["targets"][2]
        remaining = prepose_offset
        stage_count = (abs(remaining) + args.prepose_step - 1) // args.prepose_step
        for stage_index in range(1, stage_count + 1):
            step = min(abs(remaining), args.prepose_step)
            step = step if remaining > 0 else -step
            stage_target = (stage_start + step) % 4096

            targets = list(status["targets"])
            targets[2] = stage_target
            status = driver.set_current_position_targets(targets, timeout=args.timeout)
            if status is None:
                raise RuntimeError(
                    f"ID3 预备第 {stage_index}/{stage_count} 段未收到回包"
                )
            if status["fault_name"] != "NONE":
                raise RuntimeError(
                    f"板端拒绝 ID3 预备第 {stage_index}/{stage_count} 段: "
                    f"{status['fault_name']}"
                )
            print_status(f"ID3 预备第 {stage_index}/{stage_count} 段目标已写入", status, args)

            status = wait_for_id3_prepose(driver, args, stage_index, stage_count)
            stage_start = stage_target
            remaining -= step
        print_status("ID3 预备完成", status, args)
        if abs(status["gravity_current_id2"]) > args.max_id2_gravity_current:
            print(
                "ID3 预备后 ID2 重力电流仍为 "
                f"{status['gravity_current_id2']:+d}，超过安全阈值 "
                f"+/-{args.max_id2_gravity_current}；已安全结束，未下发 ID2 目标。"
            )
            return

        start_id2 = status["targets"][1]
        # 协议位置为单圈 0~4095；跨越边界时按单圈环绕，板端会保留连续运动方向。
        target_id2 = (start_id2 + args.id2_offset) % 4096
        print(
            f"ID2 当前重力电流 {status['gravity_current_id2']:+d}，在允许余量内。\n"
            f"下一步将执行 ID2 {start_id2} -> {target_id2}（{args.id2_offset:+d} tick）。"
        )
        if input("确认执行 ID2 行程请输入 YES，其他输入取消: ").strip() != "YES":
            print("已取消，ID2 目标未下发。")
            return

        targets = list(status["targets"])
        targets[1] = target_id2
        status = driver.set_current_position_targets(targets, timeout=args.timeout)
        if status is None:
            raise RuntimeError("ID2 目标未收到回包")
        if status["fault_name"] != "NONE":
            raise RuntimeError(f"板端拒绝 ID2 目标: {status['fault_name']}")
        print_status("ID2 目标已写入", status, args)

        deadline = time.monotonic() + args.hold_time
        while time.monotonic() < deadline:
            time.sleep(args.poll_period)
            if args.debug_terms:
                status = driver.get_current_position_control_debug(timeout=args.timeout)
            else:
                status = driver.get_current_position_control_status(timeout=args.timeout)
            if status is None:
                raise RuntimeError("ID2 行程期间未收到 0x22 状态回包")
            print_status("协同控制中", status, args)
            if status["state_name"] == "FAULT":
                raise RuntimeError(f"板端进入故障状态: {status['fault_name']}")
            if abs(status["error_id2_ticks"]) > args.max_error:
                raise RuntimeError(
                    f"ID2 误差扩大到 {status['error_id2_ticks']:+d} tick，已停止测试"
                )
    finally:
        if enabled and driver.serial_comm.is_connected():
            status = driver.disable_current_position_control(timeout=args.timeout)
            if status is not None:
                print_status("关闭确认", status, args)
        driver.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ID3 预备姿态 + ID2 小行程协同测试")
    parser.add_argument("--port", default="COM11")
    parser.add_argument("--timeout", type=float, default=1.0)
    parser.add_argument("--id2-offset", type=int, required=True, help="ID2 相对锁存目标的偏移，范围 -100 到 +100 tick")
    parser.add_argument("--prepose-timeout", type=float, default=30.0, help="等待 ID3 预备到位的最长时间")
    parser.add_argument(
        "--prepose-step",
        type=int,
        default=25,
        help="ID3 预备每小段的最大行程 tick，默认 25",
    )
    parser.add_argument(
        "--max-prepose-travel",
        type=int,
        default=150,
        help="允许自动执行的 ID3 预备总行程上限 tick，默认 150",
    )
    parser.add_argument(
        "--id3-prepose-offset",
        type=int,
        default=None,
        help="相对本次锁存姿态指定 ID3 预备行程；用于每次仅扩展一小段工作空间",
    )
    parser.add_argument("--id3-tolerance", type=int, default=8, help="ID3 预备到位允许误差")
    parser.add_argument("--max-id2-gravity-current", type=int, default=600, help="允许执行 ID2 前的 |G_ID2| 上限")
    parser.add_argument("--hold-time", type=float, default=20.0)
    parser.add_argument(
        "--arm-settle-time",
        type=float,
        default=5.0,
        help="开启 0x22 后、下发 ID3 行程前的稳定等待时间，默认 5 秒；设为 0 可跳过",
    )
    parser.add_argument("--poll-period", type=float, default=0.2)
    parser.add_argument("--max-error", type=int, default=160)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument(
        "--debug-terms",
        action="store_true",
        help="读取 0x22/0x05 只读诊断项，打印 ID3 参考、速度、积分和破静摩擦分量",
    )
    args = parser.parse_args()

    if args.id2_offset == 0 or abs(args.id2_offset) > 100:
        parser.error("--id2-offset 必须在 -100 到 +100 tick，且不能为 0")
    if (
        args.prepose_timeout <= 0
        or args.hold_time <= 0
        or args.poll_period <= 0
        or args.arm_settle_time < 0
    ):
        parser.error("时间参数必须为正数")
    if args.prepose_step < 5 or args.prepose_step > 50:
        parser.error("--prepose-step 必须在 5 到 50 tick")
    if args.max_prepose_travel < 10 or args.max_prepose_travel > 400:
        parser.error("--max-prepose-travel 必须在 10 到 400 tick")
    if args.id3_prepose_offset is not None and (
        args.id3_prepose_offset == 0 or abs(args.id3_prepose_offset) > 400
    ):
        parser.error("--id3-prepose-offset 必须在 -400 到 +400 tick，且不能为 0")
    if args.id3_tolerance < 1 or args.max_id2_gravity_current < 1:
        parser.error("误差和电流阈值必须为正数")
    if args.max_error <= abs(args.id2_offset):
        parser.error("--max-error 必须大于 |--id2-offset|")

    main(args)
