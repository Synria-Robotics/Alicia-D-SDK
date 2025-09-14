"""
MotionController - 运动控制器

职责：
- 运动控制和协调
- 实时控制管理
- 安全检查和限位
- 状态监控和反馈
"""

import time
import threading
from typing import List, Optional, Dict, Any, Callable
import numpy as np

from ..execution import HardwareExecutor
from ..hardware import ServoDriver, JointState
from ..kinematics import RobotModel, IKController
from ..utils.logger import logger


class MotionController:
    """运动控制器 - 负责运动控制和协调"""
    
    def __init__(self, 
                 servo_driver: ServoDriver,
                 robot_model: RobotModel,
                 ik_controller: IKController,
                 hardware_executor: HardwareExecutor):
        """
        初始化运动控制器
        
        Args:
            servo_driver: 舵机驱动
            robot_model: 机器人模型
            ik_controller: IK控制器
            hardware_executor: 硬件执行器
        """
        self.servo_driver = servo_driver
        self.robot_model = robot_model
        self.ik_controller = ik_controller
        self.hardware_executor = hardware_executor
        
        # 控制参数
        self.max_joint_velocity = 2.5  # rad/s
        self.max_joint_acceleration = 8.0  # rad/s²
        self.max_gripper_velocity = 1.5  # rad/s
        self.max_gripper_acceleration = 10.0  # rad/s²
        
        # 安全参数
        self.joint_limits = None  # 关节限位
        self.cartesian_limits = None  # 笛卡尔限位
        self.emergency_stop = False
        
        # 在线控制
        self._online_control_active = False
        self._online_thread = None
        self._online_target = None
        self._online_lock = threading.Lock()
        
        logger.info("初始化运动控制器")
    
    # ==================== 轨迹控制接口 ====================
    
    def execute_joint_trajectory(self, 
                                joint_trajectory: List[List[float]],
                                gripper_trajectory: Optional[List[float]] = None,
                                delay: Optional[float] = None,
                                progress_callback: Optional[Callable] = None,
                                completion_callback: Optional[Callable] = None,
                                error_callback: Optional[Callable] = None) -> bool:
        """
        执行关节轨迹
        
        Args:
            joint_trajectory: 关节轨迹
            gripper_trajectory: 夹爪轨迹，可选
            delay: 执行延迟
            progress_callback: 进度回调
            completion_callback: 完成回调
            error_callback: 错误回调
            
        Returns:
            bool: 是否成功开始执行
        """
        if self.emergency_stop:
            logger.warning("紧急停止状态，无法执行轨迹")
            return False
        
        # 安全检查
        if not self._validate_joint_trajectory(joint_trajectory):
            return False
        
        # 停止在线控制
        if self._online_control_active:
            self.stop_online_control()
        
        # 执行轨迹
        return self.hardware_executor.execute_trajectory(
            joint_trajectory=joint_trajectory,
            gripper_trajectory=gripper_trajectory,
            delay=delay,
            progress_callback=progress_callback,
            completion_callback=completion_callback,
            error_callback=error_callback
        )
    
    def execute_cartesian_trajectory(self, 
                                    pose_trajectory: List[List[float]],
                                    gripper_trajectory: Optional[List[float]] = None,
                                    delay: Optional[float] = None,
                                    progress_callback: Optional[Callable] = None,
                                    completion_callback: Optional[Callable] = None,
                                    error_callback: Optional[Callable] = None) -> bool:
        """
        执行笛卡尔轨迹
        
        Args:
            pose_trajectory: 位姿轨迹
            gripper_trajectory: 夹爪轨迹，可选
            delay: 执行延迟
            progress_callback: 进度回调
            completion_callback: 完成回调
            error_callback: 错误回调
            
        Returns:
            bool: 是否成功开始执行
        """
        if self.emergency_stop:
            logger.warning("紧急停止状态，无法执行轨迹")
            return False
        
        # 安全检查
        if not self._validate_pose_trajectory(pose_trajectory):
            return False
        
        # 转换为关节轨迹
        joint_trajectory = self._convert_pose_to_joint_trajectory(pose_trajectory)
        if not joint_trajectory:
            logger.error("笛卡尔轨迹转换为关节轨迹失败")
            return False
        
        # 执行关节轨迹
        return self.execute_joint_trajectory(
            joint_trajectory=joint_trajectory,
            gripper_trajectory=gripper_trajectory,
            delay=delay,
            progress_callback=progress_callback,
            completion_callback=completion_callback,
            error_callback=error_callback
        )
    
    # ==================== 实时控制接口 ====================
    
    def start_online_control(self, 
                            command_rate_hz: float = 200.0,
                            max_joint_velocity: Optional[float] = None,
                            max_joint_acceleration: Optional[float] = None,
                            max_gripper_velocity: Optional[float] = None,
                            max_gripper_acceleration: Optional[float] = None) -> bool:
        """
        启动在线实时控制
        
        Args:
            command_rate_hz: 控制频率
            max_joint_velocity: 最大关节速度
            max_joint_acceleration: 最大关节加速度
            max_gripper_velocity: 最大夹爪速度
            max_gripper_acceleration: 最大夹爪加速度
            
        Returns:
            bool: 是否成功启动
        """
        if self.emergency_stop:
            logger.warning("紧急停止状态，无法启动在线控制")
            return False
        
        if self._online_control_active:
            logger.warning("在线控制已经在运行")
            return False
        
        # 更新控制参数
        if max_joint_velocity is not None:
            self.max_joint_velocity = max_joint_velocity
        if max_joint_acceleration is not None:
            self.max_joint_acceleration = max_joint_acceleration
        if max_gripper_velocity is not None:
            self.max_gripper_velocity = max_gripper_velocity
        if max_gripper_acceleration is not None:
            self.max_gripper_acceleration = max_gripper_acceleration
        
        # 启动在线控制线程
        self._online_control_active = True
        self._online_thread = threading.Thread(
            target=self._online_control_loop,
            args=(command_rate_hz,),
            daemon=True
        )
        self._online_thread.start()
        
        logger.info(f"启动在线控制，频率: {command_rate_hz}Hz")
        return True
    
    def stop_online_control(self) -> bool:
        """
        停止在线实时控制
        
        Returns:
            bool: 是否成功停止
        """
        if not self._online_control_active:
            logger.warning("在线控制未运行")
            return False
        
        self._online_control_active = False
        
        if self._online_thread and self._online_thread.is_alive():
            self._online_thread.join(timeout=2.0)
        
        self._online_thread = None
        logger.info("在线控制已停止")
        return True
    
    def set_online_target(self, 
                         joint_angles: Optional[List[float]] = None,
                         gripper_angle: Optional[float] = None) -> bool:
        """
        设置在线控制目标
        
        Args:
            joint_angles: 关节角度目标
            gripper_angle: 夹爪角度目标
            
        Returns:
            bool: 是否成功设置
        """
        if not self._online_control_active:
            logger.warning("在线控制未运行")
            return False
        
        with self._online_lock:
            if joint_angles is not None:
                if len(joint_angles) != 6:
                    logger.error("关节角度数量错误")
                    return False
                self._online_target = {
                    'joints': joint_angles.copy(),
                    'gripper': gripper_angle
                }
            elif gripper_angle is not None:
                if self._online_target is None:
                    self._online_target = {'joints': None, 'gripper': gripper_angle}
                else:
                    self._online_target['gripper'] = gripper_angle
        
        return True
    
    # ==================== 状态查询接口 ====================
    
    def is_executing(self) -> bool:
        """是否正在执行轨迹"""
        return self.hardware_executor.is_executing()
    
    def is_online_control_active(self) -> bool:
        """在线控制是否激活"""
        return self._online_control_active
    
    def get_current_joint_angles(self) -> Optional[List[float]]:
        """获取当前关节角度"""
        return self.servo_driver.get_joint_angles()
    
    def get_current_pose(self) -> Optional[List[float]]:
        """获取当前位姿"""
        joint_angles = self.get_current_joint_angles()
        if not joint_angles:
            return None
        
        pos, quat = self.robot_model.forward_kinematics(joint_angles)
        return np.concatenate([pos, quat]).tolist()
    
    def get_current_gripper_angle(self) -> Optional[float]:
        """获取当前夹爪角度"""
        state = self.servo_driver.get_joint_state()
        return state.gripper if state else None
    
    # ==================== 安全控制接口 ====================
    
    def emergency_stop(self) -> bool:
        """
        紧急停止
        
        Returns:
            bool: 是否成功停止
        """
        self.emergency_stop = True
        
        # 停止轨迹执行
        if self.is_executing():
            self.hardware_executor.stop_execution()
        
        # 停止在线控制
        if self._online_control_active:
            self.stop_online_control()
        
        logger.warning("紧急停止已激活")
        return True
    
    def clear_emergency_stop(self) -> bool:
        """
        清除紧急停止状态
        
        Returns:
            bool: 是否成功清除
        """
        self.emergency_stop = False
        logger.info("紧急停止状态已清除")
        return True
    
    def set_joint_limits(self, joint_limits: List[tuple]):
        """设置关节限位"""
        self.joint_limits = joint_limits
        logger.info("关节限位已设置")
    
    def set_cartesian_limits(self, cartesian_limits: Dict[str, tuple]):
        """设置笛卡尔限位"""
        self.cartesian_limits = cartesian_limits
        logger.info("笛卡尔限位已设置")
    
    # ==================== 内部方法 ====================
    
    def _validate_joint_trajectory(self, joint_trajectory: List[List[float]]) -> bool:
        """验证关节轨迹"""
        if not joint_trajectory:
            logger.error("关节轨迹为空")
            return False
        
        for i, point in enumerate(joint_trajectory):
            if len(point) != 6:
                logger.error(f"第{i+1}个轨迹点关节数量错误")
                return False
            
            # 检查关节限位
            if self.joint_limits:
                for j, angle in enumerate(point):
                    if j < len(self.joint_limits):
                        min_limit, max_limit = self.joint_limits[j]
                        if not (min_limit <= angle <= max_limit):
                            logger.error(f"第{i+1}个轨迹点第{j+1}个关节超出限位")
                            return False
        
        return True
    
    def _validate_pose_trajectory(self, pose_trajectory: List[List[float]]) -> bool:
        """验证位姿轨迹"""
        if not pose_trajectory:
            logger.error("位姿轨迹为空")
            return False
        
        for i, pose in enumerate(pose_trajectory):
            if len(pose) != 7:
                logger.error(f"第{i+1}个轨迹点位姿维度错误")
                return False
            
            # 检查笛卡尔限位
            if self.cartesian_limits:
                x, y, z = pose[:3]
                if 'x' in self.cartesian_limits:
                    min_x, max_x = self.cartesian_limits['x']
                    if not (min_x <= x <= max_x):
                        logger.error(f"第{i+1}个轨迹点X坐标超出限位")
                        return False
                # 类似检查Y和Z坐标
        
        return True
    
    def _convert_pose_to_joint_trajectory(self, pose_trajectory: List[List[float]]) -> List[List[float]]:
        """将位姿轨迹转换为关节轨迹"""
        joint_trajectory = []
        current_joints = self.get_current_joint_angles()
        
        if not current_joints:
            logger.error("无法获取当前关节角度")
            return []
        
        for pose in pose_trajectory:
            # 使用IK求解关节角度
            joint_angles = self.ik_controller.solve_ik(
                pose_traj=[pose],
                initial_angles=current_joints,
                output_format='as_list'
            )
            
            if not joint_angles:
                logger.error("IK求解失败")
                return []
            
            joint_trajectory.append(joint_angles[0])
            current_joints = joint_angles[0]  # 使用当前解作为下次的初始值
        
        return joint_trajectory
    
    def _online_control_loop(self, command_rate_hz: float):
        """在线控制循环"""
        dt = 1.0 / command_rate_hz
        last_time = time.perf_counter()
        
        # 当前命令状态
        cmd_joints = [0.0] * 6
        cmd_gripper = 0.0
        cmd_joint_vel = [0.0] * 6
        cmd_gripper_vel = 0.0
        
        # 初始化当前状态
        current_state = self.get_current_joint_angles()
        if current_state:
            cmd_joints = current_state.copy()
        
        current_gripper = self.get_current_gripper_angle()
        if current_gripper is not None:
            cmd_gripper = current_gripper
        
        logger.info("在线控制循环开始")
        
        while self._online_control_active and not self.emergency_stop:
            start_time = time.perf_counter()
            
            # 获取目标
            with self._online_lock:
                target = self._online_target
            
            # 更新关节命令
            if target and target.get('joints'):
                target_joints = target['joints']
                for i in range(6):
                    error = target_joints[i] - cmd_joints[i]
                    sign = 1.0 if error >= 0.0 else -1.0
                    
                    # 计算速度限制
                    brake_dist = (cmd_joint_vel[i] ** 2) / (2.0 * max(1e-6, self.max_joint_acceleration))
                    dist = abs(error)
                    
                    if brake_dist >= dist:
                        # 减速阶段
                        cmd_joint_vel[i] -= sign * self.max_joint_acceleration * dt * (1.0 if (cmd_joint_vel[i] * sign) > 0.0 else -1.0)
                    else:
                        # 加速阶段
                        cmd_joint_vel[i] += sign * self.max_joint_acceleration * dt
                    
                    # 限制速度
                    cmd_joint_vel[i] = max(-self.max_joint_velocity, min(self.max_joint_velocity, cmd_joint_vel[i]))
                    
                    # 更新位置
                    new_pos = cmd_joints[i] + cmd_joint_vel[i] * dt
                    
                    # 检查是否到达目标
                    if (target_joints[i] - cmd_joints[i]) * (target_joints[i] - new_pos) <= 0.0:
                        new_pos = target_joints[i]
                        cmd_joint_vel[i] = 0.0
                    
                    cmd_joints[i] = new_pos
            
            # 更新夹爪命令
            if target and target.get('gripper') is not None:
                target_gripper = target['gripper']
                error = target_gripper - cmd_gripper
                sign = 1.0 if error >= 0.0 else -1.0
                
                brake_dist = (cmd_gripper_vel ** 2) / (2.0 * max(1e-6, self.max_gripper_acceleration))
                dist = abs(error)
                
                if brake_dist >= dist:
                    cmd_gripper_vel -= sign * self.max_gripper_acceleration * dt * (1.0 if (cmd_gripper_vel * sign) > 0.0 else -1.0)
                else:
                    cmd_gripper_vel += sign * self.max_gripper_acceleration * dt
                
                cmd_gripper_vel = max(-self.max_gripper_velocity, min(self.max_gripper_velocity, cmd_gripper_vel))
                
                new_gripper = cmd_gripper + cmd_gripper_vel * dt
                
                if (target_gripper - cmd_gripper) * (target_gripper - new_gripper) <= 0.0:
                    new_gripper = target_gripper
                    cmd_gripper_vel = 0.0
                
                cmd_gripper = new_gripper
            
            # 发送命令
            try:
                self.servo_driver.set_joint_angles(cmd_joints)
                if target and target.get('gripper') is not None:
                    self.servo_driver.set_gripper(cmd_gripper)
            except Exception as e:
                logger.error(f"发送在线控制命令失败: {e}")
                break
            
            # 控制循环频率
            elapsed = time.perf_counter() - start_time
            sleep_time = dt - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        logger.info("在线控制循环结束")
    
    def __del__(self):
        """析构函数"""
        try:
            if self._online_control_active:
                self.stop_online_control()
        except Exception as e:
            logger.error(f"运动控制器析构异常: {e}")