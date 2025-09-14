"""
StateManager - 状态管理器

职责：
- 状态数据管理
- 状态监控和记录
- 状态查询接口
- 状态变化通知
"""

import time
import threading
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass
from datetime import datetime
import numpy as np

from ..hardware import ServoDriver, JointState
from ..kinematics import RobotModel
from ..utils.logger import logger


@dataclass
class RobotState:
    """机器人状态数据类"""
    timestamp: float
    joint_angles: List[float]
    gripper_angle: float
    pose: List[float]  # [x, y, z, qx, qy, qz, qw]
    is_moving: bool
    is_online_control: bool
    emergency_stop: bool


class StateManager:
    """状态管理器 - 负责状态数据管理"""
    
    def __init__(self, 
                 servo_driver: ServoDriver,
                 robot_model: RobotModel):
        """
        初始化状态管理器
        
        Args:
            servo_driver: 舵机驱动
            robot_model: 机器人模型
        """
        self.servo_driver = servo_driver
        self.robot_model = robot_model
        
        # 状态缓存
        self._current_state: Optional[RobotState] = None
        self._state_history: List[RobotState] = []
        self._max_history_size = 1000
        
        # 状态监控
        self._monitoring_active = False
        self._monitoring_thread = None
        self._monitoring_interval = 0.1  # 100ms
        
        # 状态变化回调
        self._state_change_callbacks: List[Callable] = []
        self._lock = threading.Lock()
        
        logger.info("初始化状态管理器")
    
    # ==================== 状态查询接口 ====================
    
    def get_current_state(self) -> Optional[RobotState]:
        """获取当前状态"""
        with self._lock:
            return self._current_state
    
    def get_joint_angles(self) -> Optional[List[float]]:
        """获取当前关节角度"""
        state = self.get_current_state()
        return state.joint_angles if state else None
    
    def get_pose(self) -> Optional[List[float]]:
        """获取当前位姿"""
        state = self.get_current_state()
        return state.pose if state else None
    
    def get_gripper_angle(self) -> Optional[float]:
        """获取当前夹爪角度"""
        state = self.get_current_state()
        return state.gripper_angle if state else None
    
    def is_moving(self) -> bool:
        """是否正在运动"""
        state = self.get_current_state()
        return state.is_moving if state else False
    
    def is_online_control_active(self) -> bool:
        """在线控制是否激活"""
        state = self.get_current_state()
        return state.is_online_control if state else False
    
    def is_emergency_stop(self) -> bool:
        """是否紧急停止"""
        state = self.get_current_state()
        return state.emergency_stop if state else False
    
    # ==================== 状态历史接口 ====================
    
    def get_state_history(self, max_count: Optional[int] = None) -> List[RobotState]:
        """获取状态历史"""
        with self._lock:
            if max_count is None:
                return self._state_history.copy()
            else:
                return self._state_history[-max_count:].copy()
    
    def clear_state_history(self):
        """清除状态历史"""
        with self._lock:
            self._state_history.clear()
        logger.info("状态历史已清除")
    
    def get_state_at_time(self, timestamp: float, tolerance: float = 0.1) -> Optional[RobotState]:
        """获取指定时间点的状态"""
        with self._lock:
            for state in reversed(self._state_history):
                if abs(state.timestamp - timestamp) <= tolerance:
                    return state
        return None
    
    # ==================== 状态监控接口 ====================
    
    def start_monitoring(self, interval: float = 0.1) -> bool:
        """
        启动状态监控
        
        Args:
            interval: 监控间隔（秒）
            
        Returns:
            bool: 是否成功启动
        """
        if self._monitoring_active:
            logger.warning("状态监控已经在运行")
            return False
        
        self._monitoring_interval = max(0.01, interval)  # 最小10ms
        self._monitoring_active = True
        
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self._monitoring_thread.start()
        
        logger.info(f"启动状态监控，间隔: {self._monitoring_interval:.3f}s")
        return True
    
    def stop_monitoring(self) -> bool:
        """
        停止状态监控
        
        Returns:
            bool: 是否成功停止
        """
        if not self._monitoring_active:
            logger.warning("状态监控未运行")
            return False
        
        self._monitoring_active = False
        
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=2.0)
        
        self._monitoring_thread = None
        logger.info("状态监控已停止")
        return True
    
    def is_monitoring_active(self) -> bool:
        """状态监控是否激活"""
        return self._monitoring_active
    
    # ==================== 状态更新接口 ====================
    
    def update_state(self, 
                    is_moving: bool = False,
                    is_online_control: bool = False,
                    emergency_stop: bool = False):
        """
        更新状态信息
        
        Args:
            is_moving: 是否正在运动
            is_online_control: 是否在线控制
            emergency_stop: 是否紧急停止
        """
        try:
            # 获取硬件状态
            joint_state = self.servo_driver.get_joint_state()
            if not joint_state:
                return
            
            # 计算位姿
            pos, quat = self.robot_model.forward_kinematics(joint_state.angles)
            pose = np.concatenate([pos, quat]).tolist()
            
            # 创建新状态
            new_state = RobotState(
                timestamp=time.time(),
                joint_angles=joint_state.angles.copy(),
                gripper_angle=joint_state.gripper,
                pose=pose,
                is_moving=is_moving,
                is_online_control=is_online_control,
                emergency_stop=emergency_stop
            )
            
            # 更新状态
            with self._lock:
                old_state = self._current_state
                self._current_state = new_state
                
                # 添加到历史
                self._state_history.append(new_state)
                
                # 限制历史大小
                if len(self._state_history) > self._max_history_size:
                    self._state_history.pop(0)
            
            # 触发状态变化回调
            if old_state is None or self._has_state_changed(old_state, new_state):
                self._trigger_state_change_callbacks(old_state, new_state)
            
        except Exception as e:
            logger.error(f"更新状态失败: {e}")
    
    # ==================== 回调接口 ====================
    
    def add_state_change_callback(self, callback: Callable[[RobotState, RobotState], None]):
        """
        添加状态变化回调
        
        Args:
            callback: 回调函数，参数为(old_state, new_state)
        """
        with self._lock:
            self._state_change_callbacks.append(callback)
    
    def remove_state_change_callback(self, callback: Callable[[RobotState, RobotState], None]):
        """
        移除状态变化回调
        
        Args:
            callback: 要移除的回调函数
        """
        with self._lock:
            if callback in self._state_change_callbacks:
                self._state_change_callbacks.remove(callback)
    
    def clear_state_change_callbacks(self):
        """清除所有状态变化回调"""
        with self._lock:
            self._state_change_callbacks.clear()
    
    # ==================== 配置接口 ====================
    
    def set_max_history_size(self, size: int):
        """设置最大历史记录数量"""
        self._max_history_size = max(100, size)
        logger.info(f"设置最大历史记录数量: {self._max_history_size}")
    
    def set_monitoring_interval(self, interval: float):
        """设置监控间隔"""
        self._monitoring_interval = max(0.01, interval)
        logger.info(f"设置监控间隔: {self._monitoring_interval:.3f}s")
    
    # ==================== 内部方法 ====================
    
    def _monitoring_loop(self):
        """状态监控循环"""
        logger.info("状态监控循环开始")
        
        while self._monitoring_active:
            try:
                # 更新状态（这里需要从外部获取运动状态信息）
                self.update_state()
                time.sleep(self._monitoring_interval)
            except Exception as e:
                logger.error(f"状态监控循环异常: {e}")
                time.sleep(self._monitoring_interval)
        
        logger.info("状态监控循环结束")
    
    def _has_state_changed(self, old_state: RobotState, new_state: RobotState) -> bool:
        """检查状态是否发生变化"""
        if old_state is None:
            return True
        
        # 检查关节角度变化
        joint_threshold = 1e-6
        for old_angle, new_angle in zip(old_state.joint_angles, new_state.joint_angles):
            if abs(old_angle - new_angle) > joint_threshold:
                return True
        
        # 检查夹爪角度变化
        if abs(old_state.gripper_angle - new_state.gripper_angle) > joint_threshold:
            return True
        
        # 检查运动状态变化
        if old_state.is_moving != new_state.is_moving:
            return True
        
        # 检查在线控制状态变化
        if old_state.is_online_control != new_state.is_online_control:
            return True
        
        # 检查紧急停止状态变化
        if old_state.emergency_stop != new_state.emergency_stop:
            return True
        
        return False
    
    def _trigger_state_change_callbacks(self, old_state: Optional[RobotState], new_state: RobotState):
        """触发状态变化回调"""
        with self._lock:
            callbacks = self._state_change_callbacks.copy()
        
        for callback in callbacks:
            try:
                callback(old_state, new_state)
            except Exception as e:
                logger.error(f"状态变化回调执行失败: {e}")
    
    # ==================== 工具方法 ====================
    
    def get_state_statistics(self) -> Dict[str, Any]:
        """获取状态统计信息"""
        with self._lock:
            if not self._state_history:
                return {"total_states": 0}
            
            total_states = len(self._state_history)
            time_span = self._state_history[-1].timestamp - self._state_history[0].timestamp
            
            # 计算关节角度范围
            joint_ranges = []
            for i in range(6):
                angles = [state.joint_angles[i] for state in self._state_history]
                joint_ranges.append({
                    "min": min(angles),
                    "max": max(angles),
                    "range": max(angles) - min(angles)
                })
            
            return {
                "total_states": total_states,
                "time_span": time_span,
                "joint_ranges": joint_ranges,
                "monitoring_active": self._monitoring_active,
                "max_history_size": self._max_history_size
            }
    
    def export_state_history(self, filename: str) -> bool:
        """导出状态历史到文件"""
        try:
            import json
            
            with self._lock:
                history_data = []
                for state in self._state_history:
                    history_data.append({
                        "timestamp": state.timestamp,
                        "joint_angles": state.joint_angles,
                        "gripper_angle": state.gripper_angle,
                        "pose": state.pose,
                        "is_moving": state.is_moving,
                        "is_online_control": state.is_online_control,
                        "emergency_stop": state.emergency_stop
                    })
            
            with open(filename, 'w') as f:
                json.dump(history_data, f, indent=2)
            
            logger.info(f"状态历史已导出到: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"导出状态历史失败: {e}")
            return False
    
    def __del__(self):
        """析构函数"""
        try:
            if self._monitoring_active:
                self.stop_monitoring()
        except Exception as e:
            logger.error(f"状态管理器析构异常: {e}")