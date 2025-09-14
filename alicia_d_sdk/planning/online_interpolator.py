"""
OnlineInterpolator - 在线插值器

职责：
- 在线实时插值
- 梯形速度剖面
- 实时目标更新
- 平滑控制
"""

import time
import threading
from typing import List, Optional, Callable
import numpy as np

from ..hardware import ServoDriver
from ..utils.logger import logger


class OnlineInterpolator:
    """在线插值器 - 提供实时插值功能"""
    
    def __init__(self,
                 servo_driver: ServoDriver,
                 command_rate_hz: float = 200.0,
                 max_joint_velocity: float = 2.5,
                 max_joint_acceleration: float = 8.0,
                 max_gripper_velocity: float = 1.5,
                 max_gripper_acceleration: float = 10.0):
        """
        初始化在线插值器
        
        Args:
            servo_driver: 舵机驱动
            command_rate_hz: 控制频率
            max_joint_velocity: 最大关节速度 (rad/s)
            max_joint_acceleration: 最大关节加速度 (rad/s²)
            max_gripper_velocity: 最大夹爪速度 (rad/s)
            max_gripper_acceleration: 最大夹爪加速度 (rad/s²)
        """
        self.servo_driver = servo_driver
        
        # 控制参数
        self.command_rate_hz = max(1.0, command_rate_hz)
        self.max_joint_velocity = max_joint_velocity
        self.max_joint_acceleration = max_joint_acceleration
        self.max_gripper_velocity = max_gripper_velocity
        self.max_gripper_acceleration = max_gripper_acceleration
        
        # 线程控制
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # 插值状态
        self._cmd_joints = [0.0] * 6
        self._cmd_gripper = 0.0
        self._cmd_joint_vel = [0.0] * 6
        self._cmd_gripper_vel = 0.0
        
        # 目标状态
        self._target_joints = [0.0] * 6
        self._target_gripper = 0.0
        self._has_joint_target = False
        self._has_gripper_target = False
        
        # 回调函数
        self._target_reached_callback: Optional[Callable] = None
        
        # 初始化当前状态
        self._sync_to_current_state()
        
        logger.info("初始化在线插值器")
    
    def start(self) -> bool:
        """
        启动在线插值
        
        Returns:
            bool: 是否成功启动
        """
        if self._running:
            logger.warning("在线插值器已经在运行")
            return False
        
        # 同步到当前状态
        self._sync_to_current_state()
        
        self._running = True
        self._thread = threading.Thread(target=self._interpolation_loop, daemon=True)
        self._thread.start()
        
        logger.info(f"启动在线插值器，频率: {self.command_rate_hz}Hz")
        return True
    
    def stop(self) -> bool:
        """
        停止在线插值
        
        Returns:
            bool: 是否成功停止
        """
        if not self._running:
            logger.warning("在线插值器未运行")
            return False
        
        self._running = False
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        
        self._thread = None
        logger.info("在线插值器已停止")
        return True
    
    def set_joint_target(self, joint_angles: List[float]) -> bool:
        """
        设置关节目标
        
        Args:
            joint_angles: 关节角度目标 (6个关节)
            
        Returns:
            bool: 是否成功设置
        """
        if len(joint_angles) != 6:
            logger.error("关节角度数量错误")
            return False
        
        with self._lock:
            self._target_joints = joint_angles.copy()
            self._has_joint_target = True
        
        return True
    
    def set_gripper_target(self, gripper_angle: float) -> bool:
        """
        设置夹爪目标
        
        Args:
            gripper_angle: 夹爪角度目标
            
        Returns:
            bool: 是否成功设置
        """
        with self._lock:
            self._target_gripper = gripper_angle
            self._has_gripper_target = True
        
        return True
    
    def clear_joint_target(self):
        """清除关节目标"""
        with self._lock:
            self._has_joint_target = False
    
    def clear_gripper_target(self):
        """清除夹爪目标"""
        with self._lock:
            self._has_gripper_target = False
    
    def clear_all_targets(self):
        """清除所有目标"""
        with self._lock:
            self._has_joint_target = False
            self._has_gripper_target = False
    
    def update_parameters(self,
                         command_rate_hz: Optional[float] = None,
                         max_joint_velocity: Optional[float] = None,
                         max_joint_acceleration: Optional[float] = None,
                         max_gripper_velocity: Optional[float] = None,
                         max_gripper_acceleration: Optional[float] = None):
        """
        更新控制参数
        
        Args:
            command_rate_hz: 控制频率
            max_joint_velocity: 最大关节速度
            max_joint_acceleration: 最大关节加速度
            max_gripper_velocity: 最大夹爪速度
            max_gripper_acceleration: 最大夹爪加速度
        """
        with self._lock:
            if command_rate_hz is not None:
                self.command_rate_hz = max(1.0, command_rate_hz)
            if max_joint_velocity is not None:
                self.max_joint_velocity = max_joint_velocity
            if max_joint_acceleration is not None:
                self.max_joint_acceleration = max_joint_acceleration
            if max_gripper_velocity is not None:
                self.max_gripper_velocity = max_gripper_velocity
            if max_gripper_acceleration is not None:
                self.max_gripper_acceleration = max_gripper_acceleration
        
        logger.info("在线插值器参数已更新")
    
    def set_target_reached_callback(self, callback: Optional[Callable]):
        """
        设置目标到达回调
        
        Args:
            callback: 回调函数，当目标到达时调用
        """
        self._target_reached_callback = callback
    
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running
    
    def has_joint_target(self) -> bool:
        """是否有关节目标"""
        with self._lock:
            return self._has_joint_target
    
    def has_gripper_target(self) -> bool:
        """是否有夹爪目标"""
        with self._lock:
            return self._has_gripper_target
    
    def get_current_joint_angles(self) -> List[float]:
        """获取当前关节角度"""
        with self._lock:
            return self._cmd_joints.copy()
    
    def get_current_gripper_angle(self) -> float:
        """获取当前夹爪角度"""
        with self._lock:
            return self._cmd_gripper
    
    def get_target_joint_angles(self) -> Optional[List[float]]:
        """获取目标关节角度"""
        with self._lock:
            return self._target_joints.copy() if self._has_joint_target else None
    
    def get_target_gripper_angle(self) -> Optional[float]:
        """获取目标夹爪角度"""
        with self._lock:
            return self._target_gripper if self._has_gripper_target else None
    
    def is_target_reached(self, tolerance: float = 0.01) -> bool:
        """
        检查是否到达目标
        
        Args:
            tolerance: 容差
            
        Returns:
            bool: 是否到达目标
        """
        with self._lock:
            # 检查关节目标
            if self._has_joint_target:
                for i in range(6):
                    if abs(self._cmd_joints[i] - self._target_joints[i]) > tolerance:
                        return False
            
            # 检查夹爪目标
            if self._has_gripper_target:
                if abs(self._cmd_gripper - self._target_gripper) > tolerance:
                    return False
        
        return True
    
    def _sync_to_current_state(self):
        """同步到当前状态"""
        try:
            current_joints = self.servo_driver.get_joint_angles()
            if current_joints and len(current_joints) == 6:
                with self._lock:
                    self._cmd_joints = current_joints.copy()
                    self._target_joints = current_joints.copy()
            
            current_gripper = self.servo_driver.get_gripper_data()[0]
            if current_gripper is not None:
                with self._lock:
                    self._cmd_gripper = current_gripper
                    self._target_gripper = current_gripper
        except Exception as e:
            logger.error(f"同步当前状态失败: {e}")
    
    def _interpolation_loop(self):
        """插值循环"""
        dt = 1.0 / self.command_rate_hz
        last_time = time.perf_counter()
        
        logger.info("在线插值循环开始")
        
        while self._running:
            start_time = time.perf_counter()
            
            # 更新关节命令
            with self._lock:
                if self._has_joint_target:
                    self._update_joint_commands(dt)
                
                if self._has_gripper_target:
                    self._update_gripper_commands(dt)
                
                cmd_joints = self._cmd_joints.copy()
                cmd_gripper = self._cmd_gripper
                has_joint_target = self._has_joint_target
                has_gripper_target = self._has_gripper_target
            
            # 发送命令
            try:
                self.servo_driver.set_joint_angles(cmd_joints)
                if has_gripper_target:
                    self.servo_driver.set_gripper(cmd_gripper)
            except Exception as e:
                logger.error(f"发送插值命令失败: {e}")
                break
            
            # 检查目标到达
            if self._check_target_reached():
                self._handle_target_reached()
            
            # 控制循环频率
            elapsed = time.perf_counter() - start_time
            sleep_time = dt - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        logger.info("在线插值循环结束")
    
    def _update_joint_commands(self, dt: float):
        """更新关节命令"""
        for i in range(6):
            pos = self._cmd_joints[i]
            vel = self._cmd_joint_vel[i]
            target = self._target_joints[i]
            error = target - pos
            sign = 1.0 if error >= 0.0 else -1.0
            
            # 计算制动距离
            brake_dist = (vel * vel) / (2.0 * max(1e-6, self.max_joint_acceleration))
            dist = abs(error)
            
            # 决定加速/减速
            if brake_dist >= dist:
                # 减速阶段
                vel -= sign * self.max_joint_acceleration * dt * (1.0 if (vel * sign) > 0.0 else -1.0)
            else:
                # 加速阶段
                vel += sign * self.max_joint_acceleration * dt
            
            # 限制速度
            vel = max(-self.max_joint_velocity, min(self.max_joint_velocity, vel))
            
            # 更新位置
            new_pos = pos + vel * dt
            
            # 检查是否到达目标
            if (target - pos) * (target - new_pos) <= 0.0:
                new_pos = target
                vel = 0.0
            
            self._cmd_joints[i] = new_pos
            self._cmd_joint_vel[i] = vel
    
    def _update_gripper_commands(self, dt: float):
        """更新夹爪命令"""
        pos = self._cmd_gripper
        vel = self._cmd_gripper_vel
        target = self._target_gripper
        error = target - pos
        sign = 1.0 if error >= 0.0 else -1.0
        
        # 计算制动距离
        brake_dist = (vel * vel) / (2.0 * max(1e-6, self.max_gripper_acceleration))
        dist = abs(error)
        
        # 决定加速/减速
        if brake_dist >= dist:
            # 减速阶段
            vel -= sign * self.max_gripper_acceleration * dt * (1.0 if (vel * sign) > 0.0 else -1.0)
        else:
            # 加速阶段
            vel += sign * self.max_gripper_acceleration * dt
        
        # 限制速度
        vel = max(-self.max_gripper_velocity, min(self.max_gripper_velocity, vel))
        
        # 更新位置
        new_pos = pos + vel * dt
        
        # 检查是否到达目标
        if (target - pos) * (target - new_pos) <= 0.0:
            new_pos = target
            vel = 0.0
        
        self._cmd_gripper = new_pos
        self._cmd_gripper_vel = vel
    
    def _check_target_reached(self) -> bool:
        """检查是否到达目标"""
        tolerance = 0.01
        
        # 检查关节目标
        if self._has_joint_target:
            for i in range(6):
                if abs(self._cmd_joints[i] - self._target_joints[i]) > tolerance:
                    return False
        
        # 检查夹爪目标
        if self._has_gripper_target:
            if abs(self._cmd_gripper - self._target_gripper) > tolerance:
                return False
        
        return True
    
    def _handle_target_reached(self):
        """处理目标到达"""
        # 清除目标标志
        self._has_joint_target = False
        self._has_gripper_target = False
        
        # 调用回调函数
        if self._target_reached_callback:
            try:
                self._target_reached_callback()
            except Exception as e:
                logger.error(f"目标到达回调执行失败: {e}")
    
    def __del__(self):
        """析构函数"""
        try:
            if self._running:
                self.stop()
        except Exception as e:
            logger.error(f"在线插值器析构异常: {e}")