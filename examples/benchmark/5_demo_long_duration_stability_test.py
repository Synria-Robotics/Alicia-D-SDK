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
Demo: 03_demo_read_state 长时间稳定性测试 (含舵机自检)

功能说明：
- 封装 03_demo_read_state.py 的 print_state 功能
- 增加舵机自检功能 (self_check)，检查每个舵机是否正常
- 长时间持续读取机械臂状态
- 捕获任何错误、异常、通信故障、舵机异常
- 支持断言验证：如果有任何错误则测试失败

self_check 返回的 bits 数组说明：
- bits[0-5]: 6个关节舵机状态 (True=正常)
- bits[6-9]: 4个夹爪舵机状态 (True=正常)
- 全部为 True 表示所有舵机正常

使用方法：
# 默认1小时测试，FPS=3
python 5_demo_long_duration_stability_test.py --duration 1

# 快速测试5分钟
python 5_demo_long_duration_stability_test.py --duration 0.08

# 高频率测试
python 5_demo_long_duration_stability_test.py --duration 1 --fps 200

# 启用断言模式（测试失败时报错）
python 5_demo_long_duration_stability_test.py --duration 1 --assert_pass
"""

import argparse
import json
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass

import numpy as np
import alicia_d_sdk
from alicia_d_sdk.utils import precise_sleep


# 舵机名称映射 (索引 -> 名称)
SERVO_NAMES = {
    0: "关节1舵机",
    1: "关节2舵机", 
    2: "关节3舵机",
    3: "关节4舵机",
    4: "关节5舵机",
    5: "关节6舵机",
    6: "夹爪舵机1",
    7: "夹爪舵机2",
    8: "夹爪舵机3",
    9: "夹爪舵机4",
}


@dataclass
class ErrorRecord:
    """错误记录"""
    timestamp: float      # 距离开始的秒数
    error_type: str       # 错误类型
    message: str          # 错误信息
    details: Dict = None  # 详细信息


class ReadStateStabilityTest:
    """
    03_demo_read_state 稳定性测试 (含舵机自检)
    
    模拟 print_state(continuous=True) 的行为，并增加舵机自检
    """
    
    def __init__(
        self,
        robot,
        duration_hours: float = 1.0,
        fps: float = 3.0,
        output_format: str = "deg",
        self_check_interval: float = 5.0,
        log_dir: Optional[Path] = None,
    ):
        """
        初始化测试
        
        :param robot: 机器人实例
        :param duration_hours: 测试时长（小时）
        :param fps: 读取频率（帧/秒）
        :param output_format: 输出格式 'deg' 或 'rad'
        :param self_check_interval: 舵机自检间隔（秒）
        :param log_dir: 日志目录
        """
        self.robot = robot
        self.duration_hours = duration_hours
        self.duration_seconds = duration_hours * 3600
        self.fps = fps
        self.interval = 1.0 / fps
        self.output_format = output_format
        self.self_check_interval = self_check_interval
        
        # 机械臂类型检测
        # - follower (操作臂): 10个舵机 (6关节 + 4夹爪)
        # - leader (示教臂): 6个舵机 (仅6关节，无夹爪)
        self.robot_type: str = None
        self.servo_count: int = 10  # 默认检查全部10个，后续根据类型调整
        
        # 统计
        self.total_reads = 0
        self.successful_reads = 0
        self.failed_reads = 0
        self.self_check_count = 0
        self.servo_errors = 0
        self.errors: List[ErrorRecord] = []
        
        # 时间
        self.start_time: float = 0
        self.last_self_check_time: float = 0
        
        # 日志路径
        if log_dir is None:
            script_dir = Path(__file__).resolve().parent
            now = datetime.now()
            date_str = now.strftime("%Y%m%d")
            log_dir = script_dir / "demo_log" / date_str
        
        log_dir.mkdir(parents=True, exist_ok=True)
        time_str = datetime.now().strftime("%H%M%S")
        self.report_path = log_dir / f"{time_str}_read_state_stability_report.json"

    def _log_error(self, error_type: str, message: str, details: Dict = None):
        """记录错误"""
        elapsed = time.time() - self.start_time
        error = ErrorRecord(
            timestamp=elapsed,
            error_type=error_type,
            message=message,
            details=details
        )
        self.errors.append(error)
        self.failed_reads += 1
        print(f"\n[{elapsed:.1f}s] ❌ {error_type}: {message}")
        if details:
            print(f"    详情: {details}")

    def _detect_robot_type(self):
        """
        检测机械臂类型 (示教臂/操作臂)
        
        - follower (操作臂): 序列号以 ADF 开头，有10个舵机
        - leader (示教臂): 序列号以 ADL 开头，只有6个关节舵机
        """
        try:
            version = self.robot.get_robot_state("version")
            if version:
                serial_number = version.get("serial_number", "")
                if serial_number.startswith("ADF"):
                    self.robot_type = "follower"
                    self.servo_count = 10  # 操作臂: 6关节 + 4夹爪
                elif serial_number.startswith("ADL"):
                    self.robot_type = "leader"
                    self.servo_count = 6   # 示教臂: 仅6关节
                else:
                    self.robot_type = "unknown"
                    self.servo_count = 6   # 未知类型默认只检查6个关节
                
                print(f"🤖 检测到机械臂类型: {self.robot_type} (序列号: {serial_number})")
                print(f"🔍 将检查 {self.servo_count} 个舵机")
        except Exception as e:
            print(f"⚠️  无法检测机械臂类型: {e}，默认检查6个舵机")
            self.servo_count = 6

    def _check_servos(self) -> bool:
        """
        执行舵机自检
        
        根据机械臂类型检查对应数量的舵机：
        - 操作臂 (follower): 检查10个舵机 (bits[0-9])
        - 示教臂 (leader): 只检查6个关节舵机 (bits[0-5])
        
        :return: True 如果所有舵机正常，False 否则
        """
        now = time.time()
        if now - self.last_self_check_time < self.self_check_interval:
            return True
        
        self.last_self_check_time = now
        self.self_check_count += 1
        
        try:
            self_check = self.robot.get_robot_state("self_check", timeout=2.0)
            
            if self_check is None:
                self._log_error(
                    "SELF_CHECK_FAILED",
                    "无法获取舵机自检数据 (返回 None)"
                )
                return False
            
            bits = self_check.get("bits", [])
            raw_mask = self_check.get("raw_mask", 0)
            
            # 根据机械臂类型，只检查对应数量的舵机
            all_ok = True
            failed_servos = []
            
            for i in range(min(self.servo_count, len(bits))):
                is_ok = bits[i]
                servo_name = SERVO_NAMES.get(i, f"舵机{i}")
                if not is_ok:
                    all_ok = False
                    failed_servos.append(servo_name)
            
            if not all_ok:
                self.servo_errors += 1
                self._log_error(
                    "SERVO_ERROR",
                    f"舵机自检异常: {failed_servos}",
                    {
                        "robot_type": self.robot_type,
                        "servo_count": self.servo_count,
                        "raw_mask": f"0x{raw_mask:04X}",
                        "bits": bits[:self.servo_count],
                        "failed_servos": failed_servos,
                    }
                )
                return False
            
            # 每隔一段时间打印自检成功信息
            if self.self_check_count % 12 == 1:  # 约每分钟一次（假设5秒间隔）
                elapsed = time.time() - self.start_time
                print(f"[{elapsed:.0f}s] ✅ 舵机自检通过 ({self.robot_type}, 检查{self.servo_count}个舵机)")
            
            return True
            
        except Exception as e:
            self._log_error(
                "SELF_CHECK_EXCEPTION",
                str(e),
                {"traceback": traceback.format_exc()[:500]}
            )
            return False

    def _read_state_once(self) -> bool:
        """
        模拟 03 demo 的 _print_once 函数，读取并打印一次状态
        
        :return: True 如果成功，False 如果失败
        """
        try:
            # 1. 获取关节和夹爪状态 (与 03 demo 一致)
            state = self.robot.get_robot_state("joint_gripper")
            if state is None:
                self._log_error("STATE_READ_FAILED", "get_robot_state('joint_gripper') 返回 None")
                return False
            
            joints = state.angles
            gripper = state.gripper
            status = state.run_status_text
            
            # 检查关节角度是否全为 0（异常数据）
            # 如果所有关节角度都接近 0（阈值 0.01 弧度 ≈ 0.57°），视为异常
            if all(abs(angle) < 0.01 for angle in joints):
                self._log_error(
                    "ALL_JOINTS_ZERO",
                    "关节角度全部为 0，可能是通信或数据解析错误",
                    {"joints_rad": list(joints), "gripper": gripper}
                )
                return False
            
            # 2. 获取温度 (与 03 demo 一致)
            temperature = self.robot.get_robot_state("temperature", timeout=5.0)
            
            # 3. 获取速度 (与 03 demo 一致)
            velocity = self.robot.get_robot_state("velocity")
            
            # 4. 舵机自检 (增强功能，03 demo 只调用不处理)
            self._check_servos()
            
            # 5. 格式化输出
            if self.output_format == 'deg':
                joint_out = np.round(np.array(joints) * 180.0 / np.pi, 2)
                unit = "°"
            else:
                joint_out = np.round(joints, 3)
                unit = "rad"
            
            # 每10秒打印一次详细信息
            if self.total_reads % int(self.fps * 10) == 0:
                print(f"\n关节角度（{unit}): {joint_out.tolist()}, 夹爪: {gripper}")
                if status != "idle":
                    print(f"按键状态：{status}")
                if temperature is not None:
                    print(f"舵机温度（°C): {np.round(temperature, 1).tolist()}")
                if velocity is not None:
                    print(f"舵机速度(deg/s): {np.round(velocity, 1).tolist()}")
            
            self.successful_reads += 1
            return True
            
        except Exception as e:
            self._log_error("EXCEPTION", str(e), {"traceback": traceback.format_exc()[:500]})
            return False

    def run(self) -> bool:
        """
        运行测试
        
        :return: True 如果测试通过（无错误），False 否则
        """
        print(f"\n{'='*60}")
        print(f"🚀 开始 03_demo_read_state 稳定性测试 (含舵机自检)")
        print(f"{'='*60}")
        print(f"⏱️  测试时长: {self.duration_hours} 小时 ({self.duration_seconds:.0f} 秒)")
        print(f"📡 读取频率: {self.fps} FPS (间隔 {self.interval*1000:.1f}ms)")
        print(f"🔍 自检间隔: {self.self_check_interval} 秒")
        print(f"📐 输出格式: {self.output_format}")
        print(f"{'='*60}")
        print(f"💡 这个测试模拟 03_demo_read_state.py 的持续运行")
        print(f"💡 增加了舵机自检功能，检测每个舵机是否正常")
        print(f"💡 如果有任何错误会被捕获并记录")
        print(f"{'='*60}\n")
        
        # 检测机械臂类型
        self._detect_robot_type()
        
        self.start_time = time.time()
        self.last_self_check_time = 0
        end_time = self.start_time + self.duration_seconds
        last_progress_time = 0
        
        # 与 03 demo 一致的 spin_threshold 设置
        spin_threshold = 0.002 if self.interval <= 0.010 else 0.010
        
        try:
            while time.time() < end_time:
                loop_start = time.perf_counter()
                elapsed = time.time() - self.start_time
                
                self.total_reads += 1
                
                # 执行一次状态读取（模拟 03 demo 的 _print_once）
                self._read_state_once()
                
                # 打印进度（每30秒一次）
                if int(elapsed) - last_progress_time >= 30:
                    last_progress_time = int(elapsed)
                    percent = (elapsed / self.duration_seconds) * 100
                    remaining = (self.duration_seconds - elapsed) / 60
                    success_rate = (self.successful_reads / self.total_reads * 100) if self.total_reads > 0 else 0
                    print(f"\n📊 进度: {percent:.1f}% | 剩余: {remaining:.1f}分钟")
                    print(f"   读取: {self.total_reads} | 成功: {self.successful_reads} | 失败: {self.failed_reads}")
                    print(f"   成功率: {success_rate:.2f}% | 舵机自检: {self.self_check_count} | 舵机异常: {self.servo_errors}")
                
                # 精确等待（与 03 demo 一致）
                dt = time.perf_counter() - loop_start
                precise_sleep(self.interval - dt, spin_threshold=spin_threshold)
                
        except KeyboardInterrupt:
            print("\n\n⚠️  用户中断测试 (Ctrl+C)")
        except Exception as e:
            self._log_error("FATAL_ERROR", str(e), {"traceback": traceback.format_exc()})
        
        # 生成报告
        self._generate_report()
        
        # 返回测试是否通过
        return len(self.errors) == 0

    def _generate_report(self):
        """生成测试报告"""
        elapsed = time.time() - self.start_time
        success_rate = (self.successful_reads / self.total_reads * 100) if self.total_reads > 0 else 0
        
        report = {
            "test_info": {
                "test_type": "03_demo_read_state 稳定性测试 (含舵机自检)",
                "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
                "end_time": datetime.now().isoformat(),
                "planned_duration_hours": self.duration_hours,
                "actual_duration_seconds": elapsed,
                "fps": self.fps,
                "self_check_interval": self.self_check_interval,
            },
            "statistics": {
                "total_reads": self.total_reads,
                "successful_reads": self.successful_reads,
                "failed_reads": self.failed_reads,
                "success_rate_percent": success_rate,
                "self_check_count": self.self_check_count,
                "servo_errors": self.servo_errors,
                "total_errors": len(self.errors),
            },
            "errors": [
                {
                    "timestamp_seconds": e.timestamp,
                    "type": e.error_type,
                    "message": e.message,
                    "details": e.details,
                }
                for e in self.errors[:50]
            ],
            "test_result": {
                "passed": len(self.errors) == 0,
                "verdict": "PASS ✅" if len(self.errors) == 0 else "FAIL ❌",
            }
        }
        
        # 保存报告
        with open(self.report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        # 打印摘要
        print(f"\n{'='*60}")
        print(f"📋 测试报告")
        print(f"{'='*60}")
        print(f"⏱️  运行时间: {elapsed/60:.1f} 分钟 ({elapsed:.0f} 秒)")
        print(f"📊 总读取次数: {self.total_reads}")
        print(f"✅ 成功读取: {self.successful_reads}")
        print(f"❌ 失败读取: {self.failed_reads}")
        print(f"📈 成功率: {success_rate:.2f}%")
        print(f"🔍 舵机自检次数: {self.self_check_count}")
        print(f"⚠️  舵机异常次数: {self.servo_errors}")
        print(f"💥 总错误数量: {len(self.errors)}")
        print(f"\n📁 报告文件: {self.report_path}")
        print(f"{'='*60}")
        
        if len(self.errors) == 0:
            print(f"🎉 测试结果: PASS ✅")
            print(f"   状态读取正常，所有舵机自检通过")
        else:
            print(f"💔 测试结果: FAIL ❌ (发生 {len(self.errors)} 个错误)")
            print(f"\n最近的错误:")
            for e in self.errors[-5:]:
                print(f"  [{e.timestamp:.1f}s] {e.error_type}: {e.message}")
        print(f"{'='*60}\n")


def main(args):
    """主函数"""
    
    # 创建机器人实例
    robot = alicia_d_sdk.create_robot(
        port=args.port,
        gripper_type=args.gripper_type
    )
    
    try:
        # 创建测试实例
        test = ReadStateStabilityTest(
            robot=robot,
            duration_hours=args.duration,
            fps=args.fps,
            output_format=args.format,
            self_check_interval=args.self_check_interval,
        )
        
        # 运行测试
        passed = test.run()
        
        # 断言：如果启用了断言模式，测试失败时抛出异常
        if args.assert_pass:
            assert passed, f"稳定性测试失败！共 {len(test.errors)} 个错误，其中舵机异常 {test.servo_errors} 次"
        
        return passed
        
    except AssertionError as e:
        print(f"\n💥 断言失败: {e}")
        raise
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        traceback.print_exc()
        return False
    finally:
        robot.disconnect()
        print("👋 机器人已断开连接")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="03_demo_read_state 长时间稳定性测试 (含舵机自检)",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # 串口设置
    parser.add_argument('--port', type=str, default="", 
                        help="串口端口 (例如: COM3)")
    parser.add_argument('--gripper_type', type=str, default="50mm",
                        help="夹爪类型 (默认: 50mm)")
    
    # 显示设置
    parser.add_argument('--format', type=str, default='deg', choices=['rad', 'deg'],
                        help="角度显示格式")
    parser.add_argument('--fps', type=float, default=3.0,
                        help="读取频率 FPS (默认: 3.0)")
    
    # 测试设置
    parser.add_argument('--duration', type=float, default=1.0,
                        help="测试时长，单位：小时 (默认: 1.0)")
    parser.add_argument('--self_check_interval', type=float, default=5.0,
                        help="舵机自检间隔，单位：秒 (默认: 5.0)")
    
    # 断言设置
    parser.add_argument('--assert_pass', action='store_true',
                        help="启用断言模式：如果有任何错误则抛出 AssertionError")
    
    args = parser.parse_args()
    
    success = main(args)
    exit(0 if success else 1)
