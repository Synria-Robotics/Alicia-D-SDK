"""
ServoDriver - 舵机驱动层

职责：
- 提供统一的硬件接口
- 管理串口通信
- 处理数据解析
- 提供状态查询接口
"""

import math
import time
import threading
from typing import List, Optional, Dict, Tuple
import numpy as np

from .serial_comm import SerialComm
from .data_parser import DataParser, JointState
from ..utils.logger import logger


class ServoDriver:
    """舵机驱动层 - 提供统一的硬件接口"""
    
    # 常量定义
    RAD_TO_DEG = 180.0 / math.pi
    DEG_TO_RAD = math.pi / 180.0
    
    # 帧常量
    FRAME_HEADER = 0xAA
    FRAME_FOOTER = 0xFF
    FRAME_MINIMAL_SIZE = 5
    ARM_DATA_SIZE = 18
    GRIPPER_FRAME_SIZE = 8
    
    # 指令ID
    CMD_GRIPPER = 0x02
    CMD_ZERO_POS = 0x03
    CMD_JOINT = 0x04
    CMD_MULTI_ARM = 0x06
    CMD_TORQUE = 0x13
    
    def __init__(self, port: str = "", baudrate: int = 1000000, debug_mode: bool = False):
        """
        初始化舵机驱动
        
        Args:
            port: 串口名称，留空则自动搜索
            baudrate: 波特率
            debug_mode: 是否启用调试模式
        """
        self.debug_mode = debug_mode
        self._lock = threading.Lock()
        
        # 创建串口通信模块和数据解析器
        self.serial_comm = SerialComm(lock=self._lock, port=port, baudrate=baudrate, debug_mode=debug_mode)
        self.data_parser = DataParser(lock=self._lock, debug_mode=debug_mode)
        
        # 舵机配置
        self.servo_count = 9
        self.joint_count = 6
        
        # 舵机映射表
        self.joint_to_servo_map = [
            (0, 1.0),    # 关节1 -> 舵机1 (正向)
            (0, 1.0),    # 关节1 -> 舵机2 (正向重复)
            (1, 1.0),    # 关节2 -> 舵机3 (正向)
            (1, -1.0),   # 关节2 -> 舵机4 (反向)
            (2, 1.0),    # 关节3 -> 舵机5 (正向)
            (2, -1.0),   # 关节3 -> 舵机6 (反向)
            (3, 1.0),    # 关节4 -> 舵机7 (正向)
            (4, 1.0),    # 关节5 -> 舵机8 (正向)
            (5, 1.0),    # 关节6 -> 舵机9 (正向)
        ]
        
        # 状态更新线程
        self._update_thread = None
        self.thread_update_interval = 0.005
        self._stop_thread = threading.Event()
        self._thread_running = False
        
        logger.info("初始化舵机驱动模块")
        logger.info(f"调试模式: {'启用' if debug_mode else '禁用'}")

    def connect(self) -> bool:
        """连接到机械臂"""
        result = self.serial_comm.connect()
        if result:
            self.start_update_thread()
            self.wait_for_valid_state()
        return result
    
    def disconnect(self):
        """断开与机械臂的连接"""
        self.stop_update_thread()
        self.serial_comm.disconnect()
    
    def start_update_thread(self):
        """启动状态更新线程"""
        if self._update_thread is not None and self._thread_running:
            logger.info("状态更新线程已经在运行")
            return
        
        self._stop_thread.clear()
        self._thread_running = True
        
        self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self._update_thread.start()
        logger.info("状态更新线程已启动")
    
    def stop_update_thread(self):
        """停止状态更新线程"""
        if self._update_thread is None or not self._thread_running:
            return
        
        self._stop_thread.set()
        self._thread_running = False
        
        if self._update_thread.is_alive():
            self._update_thread.join(timeout=2.0)
        
        self._update_thread = None
        logger.info("状态更新线程已停止")
    
    def _update_loop(self):
        """状态更新线程主循环"""
        logger.info("状态更新线程开始运行")
        
        while not self._stop_thread.is_set():
            time.sleep(self.thread_update_interval)
            try:
                with self._lock:
                    frame = self.serial_comm.read_frame()
                if frame == 9999999:
                    logger.error("检测到严重的串口通信异常，机械臂可能已断开连接")
                    break
                if frame:
                    self.data_parser.parse_frame(frame)
            except Exception as e:
                logger.error(f"状态更新线程异常: {str(e)}")
                break
        self._thread_running = False
        logger.info("状态更新线程已结束运行")
    
    def wait_for_valid_state(self, timeout: float = 1.5) -> bool:
        """等待机械臂状态变为有效"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            js = self.get_joint_state()
            if js and max(abs(a) for a in js.angles) > 1e-3:
                return True
            time.sleep(0.05)
        logger.warning("未收到有效关节状态")
        return False
    
    # ==================== 状态查询接口 ====================
    
    def get_joint_angles(self) -> Optional[List[float]]:
        """读取关节角度（弧度）"""
        return self.data_parser.get_joint_state().angles
    
    def get_joint_state(self) -> JointState:
        """读取完整的机械臂状态"""
        return self.data_parser.get_joint_state()
    
    def get_gripper_data(self) -> Tuple[float, bool, bool]:
        """读取夹爪数据"""
        state = self.data_parser.get_joint_state()
        return state.gripper, state.button1, state.button2
    
    # ==================== 命令发送接口 ====================
    
    def set_joint_angles(self, joint_angles: List[float]) -> bool:
        """设置关节角度（弧度）"""
        if len(joint_angles) != self.joint_count:
            logger.error(f"关节数量错误: 需要{self.joint_count}个, 提供了{len(joint_angles)}个")
            return False
        
        frame = self._build_joint_frame(joint_angles)
        
        for i in range(2):
            result = self.serial_comm.send_data(frame)
        
        return result
    
    def set_gripper(self, angle_rad: float) -> bool:
        """设置夹爪角度（弧度）"""
        frame = self._build_gripper_frame(angle_rad)
        
        for i in range(2):
            result = self.serial_comm.send_data(frame)
        
        return result
    
    def set_zero_position(self) -> bool:
        """设置当前位置为零点"""
        frame = self._build_command_frame(self.CMD_ZERO_POS, [0x00])
        return self.serial_comm.send_data(frame)
    
    def enable_torque(self) -> bool:
        """使能力矩控制"""
        frame = self._build_command_frame(self.CMD_TORQUE, [0x01])
        result = self.serial_comm.send_data(frame)
        time.sleep(0.5)
        return result
    
    def disable_torque(self) -> bool:
        """禁用力矩控制"""
        frame = self._build_command_frame(self.CMD_TORQUE, [0x00])
        result = self.serial_comm.send_data(frame)
        time.sleep(0.5)
        return result
    
    # ==================== 内部方法 ====================
    
    def _build_joint_frame(self, joint_angles: List[float]) -> List[int]:
        """构建关节控制帧"""
        frame_size = self.FRAME_MINIMAL_SIZE + self.ARM_DATA_SIZE
        frame = [0] * frame_size
        frame[0] = self.FRAME_HEADER
        frame[1] = self.CMD_JOINT
        frame[2] = self.ARM_DATA_SIZE
        frame[-1] = self.FRAME_FOOTER
        
        for servo_idx, (joint_idx, direction) in enumerate(self.joint_to_servo_map):
            servo_angle_rad = joint_angles[joint_idx] * direction
            hardware_value = self._rad_to_hardware_value(servo_angle_rad)
            
            frame[3 + servo_idx*2] = hardware_value & 0xFF
            frame[3 + servo_idx*2 + 1] = (hardware_value >> 8) & 0xFF
        
        frame[-2] = self._calculate_checksum(frame)
        
        if self.debug_mode:
            angle_deg = [round(angle * self.RAD_TO_DEG, 2) for angle in joint_angles]
            logger.debug(f"发送关节角度(度): {angle_deg}")
        
        return frame
    
    def _build_gripper_frame(self, angle_rad: float) -> List[int]:
        """构建夹爪控制帧"""
        frame = [0] * self.GRIPPER_FRAME_SIZE
        frame[0] = self.FRAME_HEADER
        frame[1] = self.CMD_GRIPPER
        frame[2] = 3
        frame[3] = 1
        frame[-1] = self.FRAME_FOOTER
        
        gripper_value = self._rad_to_hardware_value_grip(angle_rad)
        frame[4] = gripper_value & 0xFF
        frame[5] = (gripper_value >> 8) & 0xFF
        frame[6] = self._calculate_checksum(frame)
        
        if self.debug_mode:
            angle_deg = round(angle_rad * self.RAD_TO_DEG, 2)
            logger.debug(f"发送夹爪角度: {angle_deg}度")
        
        return frame
    
    def _build_command_frame(self, cmd_id: int, data: List[int]) -> List[int]:
        """构建命令帧"""
        frame_size = len(data) + 5
        frame = [0] * frame_size
        frame[0] = self.FRAME_HEADER
        frame[1] = cmd_id
        frame[2] = len(data)
        
        for i, d in enumerate(data):
            frame[3 + i] = d
        
        frame[-1] = self.FRAME_FOOTER
        frame[-2] = self._calculate_checksum(frame)
        
        return frame
    
    def _rad_to_hardware_value(self, angle_rad: float) -> int:
        """将弧度转换为硬件值(0-4095)"""
        angle_deg = angle_rad * self.RAD_TO_DEG
        
        if angle_deg < -180.0 or angle_deg > 180.0:
            logger.warning(f"角度值超出范围: {angle_deg:.2f}度，会被截断")
            angle_deg = max(-180.0, min(180.0, angle_deg))
        
        value = int((angle_deg + 180.0) / 360.0 * 4096)
        return max(0, min(4095, value))
    
    def _rad_to_hardware_value_grip(self, angle_rad: float) -> int:
        """将弧度转换为夹爪舵机值(2048-2900)"""
        angle_deg = angle_rad * self.RAD_TO_DEG
        
        if angle_deg < 0:
            logger.warning(f"夹爪角度值超出范围: {angle_deg:.2f}度，会被截断")
            angle_deg = 0
        elif angle_deg > 100.0:
            logger.warning(f"夹爪角度值超出范围: {angle_deg:.2f}度，会被截断")
            angle_deg = 100.0

        servo_value_limit = 3290
        ratio = (servo_value_limit - 2048) / 100
        value = int(2048 + (angle_deg * ratio))
        
        return max(2048, min(servo_value_limit, value))
    
    def _calculate_checksum(self, frame: List[int]) -> int:
        """计算校验和"""
        checksum = 0
        for i in range(3, len(frame) - 2):
            checksum += frame[i]
        return checksum % 2
    
    def __del__(self):
        """析构函数"""
        try:
            self.stop_update_thread()
            self.disconnect()
        except Exception as e:
            if hasattr(logger, 'error'):
                logger.error(f"析构函数中出现异常: {str(e)}")