"""
机械臂仿真器

提供与真实机械臂API兼容的仿真接口。
"""

import numpy as np
from typing import List, Optional, Dict, Any, Callable
import time
import threading

from .mujoco_manager import MuJoCoManager
from ..utils.logger import logger


class RobotSimulator:
    """机械臂仿真器 - 提供与真实机械臂兼容的接口"""
    
    def __init__(self, model_path: str = None, enable_viewer: bool = True):
        """
        初始化机械臂仿真器
        
        Args:
            model_path: MuJoCo模型文件路径
            enable_viewer: 是否启用可视化
        """
        self.mujoco_manager = MuJoCoManager(model_path, enable_viewer)
        
        # 仿真状态
        self.is_connected = False
        self.is_moving = False
        self.is_online_control = False
        
        # 运动参数
        self.max_joint_velocity = 2.5  # rad/s
        self.max_joint_acceleration = 8.0  # rad/s²
        self.default_speed_factor = 1.0
        
        # 关节限位
        self.joint_limits = [
            (-3.14, 3.14),  # 关节1
            (-1.57, 1.57),  # 关节2
            (-3.14, 3.14),  # 关节3
            (-3.14, 3.14),  # 关节4
            (-1.57, 1.57),  # 关节5
            (-3.14, 3.14),  # 关节6
        ]
        
        # 夹爪限位
        self.gripper_limits = (0.0, 1.57)  # 0-90度
        
        # 回调函数
        self.progress_callback: Optional[Callable] = None
        self.completion_callback: Optional[Callable] = None
        self.error_callback: Optional[Callable] = None
        
        # 运动控制
        self._motion_thread: Optional[threading.Thread] = None
        self._stop_motion = threading.Event()
        
        logger.info("初始化机械臂仿真器")
    
    def connect(self) -> bool:
        """
        连接仿真环境
        
        Returns:
            bool: 是否连接成功
        """
        try:
            # 加载模型
            if not self.mujoco_manager.load_model():
                logger.error("加载MuJoCo模型失败")
                return False
            
            # 启动仿真
            if not self.mujoco_manager.start_simulation():
                logger.error("启动MuJoCo仿真失败")
                return False
            
            # 启动可视化
            if not self.mujoco_manager.start_viewer():
                logger.warning("启动可视化窗口失败，继续运行")
            
            self.is_connected = True
            logger.info("仿真环境连接成功")
            return True
            
        except Exception as e:
            logger.error(f"连接仿真环境失败: {e}")
            return False
    
    def disconnect(self) -> bool:
        """
        断开仿真环境
        
        Returns:
            bool: 是否断开成功
        """
        try:
            # 停止运动
            self.stop_motion()
            
            # 关闭仿真
            self.mujoco_manager.stop_simulation()
            self.mujoco_manager.close()
            
            self.is_connected = False
            logger.info("仿真环境已断开")
            return True
            
        except Exception as e:
            logger.error(f"断开仿真环境失败: {e}")
            return False
    
    def get_joint_angles(self, joint_format: str = 'rad') -> Optional[List[float]]:
        """
        获取当前关节角度
        
        Args:
            joint_format: 角度格式 ('rad' 或 'deg')
            
        Returns:
            List[float]: 关节角度列表
        """
        if not self.is_connected:
            logger.error("仿真环境未连接")
            return None
        
        joint_angles = self.mujoco_manager.get_joint_angles()
        if joint_angles is None:
            return None
        
        if joint_format == 'deg':
            # 转换为度
            joint_angles = [np.degrees(angle) for angle in joint_angles]
        
        return joint_angles
    
    def get_gripper_angle(self, joint_format: str = 'rad') -> Optional[float]:
        """
        获取当前夹爪角度
        
        Args:
            joint_format: 角度格式 ('rad' 或 'deg')
            
        Returns:
            float: 夹爪角度
        """
        if not self.is_connected:
            logger.error("仿真环境未连接")
            return None
        
        gripper_angle = self.mujoco_manager.get_gripper_angle()
        if gripper_angle is None:
            return None
        
        if joint_format == 'deg':
            gripper_angle = np.degrees(gripper_angle)
        
        return gripper_angle
    
    def get_end_effector_pose(self) -> Optional[List[float]]:
        """
        获取末端执行器位姿
        
        Returns:
            List[float]: [x, y, z, qx, qy, qz, qw]
        """
        if not self.is_connected:
            logger.error("仿真环境未连接")
            return None
        
        return self.mujoco_manager.get_end_effector_pose()
    
    def set_joint_angles(self, joint_angles: List[float], joint_format: str = 'rad') -> bool:
        """
        设置关节角度
        
        Args:
            joint_angles: 关节角度列表
            joint_format: 角度格式 ('rad' 或 'deg')
            
        Returns:
            bool: 是否设置成功
        """
        if not self.is_connected:
            logger.error("仿真环境未连接")
            return False
        
        if len(joint_angles) != 6:
            logger.error(f"关节角度数量错误: {len(joint_angles)}, 期望6个")
            return False
        
        # 转换角度格式
        if joint_format == 'deg':
            joint_angles = [np.radians(angle) for angle in joint_angles]
        
        # 检查关节限位
        for i, angle in enumerate(joint_angles):
            min_limit, max_limit = self.joint_limits[i]
            if not (min_limit <= angle <= max_limit):
                logger.error(f"关节{i+1}角度超出限位: {angle:.3f} not in [{min_limit:.3f}, {max_limit:.3f}]")
                return False
        
        return self.mujoco_manager.set_joint_angles(joint_angles)
    
    def set_gripper_angle(self, angle: float, joint_format: str = 'rad') -> bool:
        """
        设置夹爪角度
        
        Args:
            angle: 夹爪角度
            joint_format: 角度格式 ('rad' 或 'deg')
            
        Returns:
            bool: 是否设置成功
        """
        if not self.is_connected:
            logger.error("仿真环境未连接")
            return False
        
        # 转换角度格式
        if joint_format == 'deg':
            angle = np.radians(angle)
        
        # 检查夹爪限位
        min_limit, max_limit = self.gripper_limits
        if not (min_limit <= angle <= max_limit):
            logger.error(f"夹爪角度超出限位: {angle:.3f} not in [{min_limit:.3f}, {max_limit:.3f}]")
            return False
        
        return self.mujoco_manager.set_gripper_angle(angle)
    
    def move_joint(self, target_joints: List[float], 
                   joint_format: str = 'rad',
                   speed_factor: float = 1.0,
                   interpolation_type: str = 'cubic') -> bool:
        """
        关节空间运动
        
        Args:
            target_joints: 目标关节角度
            joint_format: 角度格式
            speed_factor: 速度因子
            interpolation_type: 插值类型
            
        Returns:
            bool: 是否执行成功
        """
        if not self.is_connected:
            logger.error("仿真环境未连接")
            return False
        
        # 获取当前关节角度
        current_joints = self.get_joint_angles(joint_format)
        if current_joints is None:
            return False
        
        # 生成轨迹
        trajectory = self._generate_trajectory(
            current_joints, target_joints, 
            speed_factor, interpolation_type
        )
        
        if not trajectory:
            return False
        
        # 执行轨迹
        return self._execute_trajectory(trajectory, joint_format)
    
    def move_gripper(self, target_angle: float,
                     joint_format: str = 'rad',
                     speed_factor: float = 1.0) -> bool:
        """
        夹爪运动
        
        Args:
            target_angle: 目标夹爪角度
            joint_format: 角度格式
            speed_factor: 速度因子
            
        Returns:
            bool: 是否执行成功
        """
        if not self.is_connected:
            logger.error("仿真环境未连接")
            return False
        
        # 获取当前夹爪角度
        current_angle = self.get_gripper_angle(joint_format)
        if current_angle is None:
            return False
        
        # 生成夹爪轨迹
        gripper_trajectory = self._generate_gripper_trajectory(
            current_angle, target_angle, speed_factor
        )
        
        if not gripper_trajectory:
            return False
        
        # 执行夹爪轨迹
        return self._execute_gripper_trajectory(gripper_trajectory, joint_format)
    
    def _generate_trajectory(self, start_joints: List[float], 
                           target_joints: List[float],
                           speed_factor: float,
                           interpolation_type: str) -> List[List[float]]:
        """生成关节轨迹"""
        try:
            # 计算运动距离
            distances = [abs(target - start) for start, target in zip(start_joints, target_joints)]
            max_distance = max(distances)
            
            if max_distance < 0.001:  # 距离太小，直接返回目标
                return [target_joints]
            
            # 计算运动时间
            max_velocity = self.max_joint_velocity * speed_factor
            max_acceleration = self.max_joint_acceleration * speed_factor
            
            # 梯形速度剖面时间计算
            t_accel = max_velocity / max_acceleration
            t_decel = max_velocity / max_acceleration
            t_const = max(0, (max_distance - max_velocity * t_accel) / max_velocity)
            
            total_time = t_accel + t_const + t_decel
            dt = 0.01  # 10ms时间步长
            steps = max(1, int(total_time / dt))
            
            # 生成轨迹点
            trajectory = []
            for i in range(steps + 1):
                t = i * dt
                ratio = self._calculate_velocity_profile_ratio(t, t_accel, t_const, t_decel)
                
                point = []
                for start, target in zip(start_joints, target_joints):
                    angle = start + (target - start) * ratio
                    point.append(angle)
                
                trajectory.append(point)
            
            return trajectory
            
        except Exception as e:
            logger.error(f"生成轨迹失败: {e}")
            return []
    
    def _generate_gripper_trajectory(self, start_angle: float, 
                                   target_angle: float,
                                   speed_factor: float) -> List[float]:
        """生成夹爪轨迹"""
        try:
            distance = abs(target_angle - start_angle)
            if distance < 0.001:
                return [target_angle]
            
            max_velocity = 1.0 * speed_factor  # 夹爪最大速度
            max_acceleration = 5.0 * speed_factor  # 夹爪最大加速度
            
            t_accel = max_velocity / max_acceleration
            t_decel = max_velocity / max_acceleration
            t_const = max(0, (distance - max_velocity * t_accel) / max_velocity)
            
            total_time = t_accel + t_const + t_decel
            dt = 0.01
            steps = max(1, int(total_time / dt))
            
            trajectory = []
            for i in range(steps + 1):
                t = i * dt
                ratio = self._calculate_velocity_profile_ratio(t, t_accel, t_const, t_decel)
                angle = start_angle + (target_angle - start_angle) * ratio
                trajectory.append(angle)
            
            return trajectory
            
        except Exception as e:
            logger.error(f"生成夹爪轨迹失败: {e}")
            return []
    
    def _calculate_velocity_profile_ratio(self, t: float, t_accel: float, 
                                        t_const: float, t_decel: float) -> float:
        """计算梯形速度剖面的位置比例"""
        if t <= t_accel:
            # 加速阶段
            return 0.5 * (t / t_accel) ** 2
        elif t <= t_accel + t_const:
            # 匀速阶段
            return 0.5 + (t - t_accel) / t_const * 0.5
        else:
            # 减速阶段
            t_remaining = t_accel + t_const + t_decel - t
            return 1.0 - 0.5 * (t_remaining / t_decel) ** 2
    
    def _execute_trajectory(self, trajectory: List[List[float]], 
                          joint_format: str) -> bool:
        """执行关节轨迹"""
        try:
            self.is_moving = True
            self._stop_motion.clear()
            
            total_points = len(trajectory)
            
            for i, joint_point in enumerate(trajectory):
                if self._stop_motion.is_set():
                    logger.info("收到停止信号，终止运动")
                    break
                
                # 设置关节角度
                if not self.set_joint_angles(joint_point, joint_format):
                    logger.error(f"执行第{i+1}个轨迹点失败")
                    return False
                
                # 调用进度回调
                if self.progress_callback:
                    try:
                        self.progress_callback(i + 1, total_points, joint_point)
                    except Exception as e:
                        logger.error(f"进度回调执行失败: {e}")
                
                # 仿真时间步长
                time.sleep(0.01)
            
            self.is_moving = False
            
            # 调用完成回调
            if self.completion_callback:
                try:
                    self.completion_callback()
                except Exception as e:
                    logger.error(f"完成回调执行失败: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"执行轨迹失败: {e}")
            self.is_moving = False
            return False
    
    def _execute_gripper_trajectory(self, trajectory: List[float], 
                                  joint_format: str) -> bool:
        """执行夹爪轨迹"""
        try:
            self.is_moving = True
            self._stop_motion.clear()
            
            total_points = len(trajectory)
            
            for i, angle in enumerate(trajectory):
                if self._stop_motion.is_set():
                    logger.info("收到停止信号，终止夹爪运动")
                    break
                
                # 设置夹爪角度
                if not self.set_gripper_angle(angle, joint_format):
                    logger.error(f"执行第{i+1}个夹爪轨迹点失败")
                    return False
                
                # 调用进度回调
                if self.progress_callback:
                    try:
                        self.progress_callback(i + 1, total_points, [angle])
                    except Exception as e:
                        logger.error(f"进度回调执行失败: {e}")
                
                # 仿真时间步长
                time.sleep(0.01)
            
            self.is_moving = False
            
            # 调用完成回调
            if self.completion_callback:
                try:
                    self.completion_callback()
                except Exception as e:
                    logger.error(f"完成回调执行失败: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"执行夹爪轨迹失败: {e}")
            self.is_moving = False
            return False
    
    def stop_motion(self):
        """停止运动"""
        self._stop_motion.set()
        self.is_moving = False
        logger.info("运动已停止")
    
    def is_robot_moving(self) -> bool:
        """检查机械臂是否在运动"""
        return self.is_moving
    
    def set_joint_limits(self, joint_limits: List[tuple]):
        """设置关节限位"""
        if len(joint_limits) != 6:
            logger.error("关节限位数量错误")
            return False
        
        self.joint_limits = joint_limits
        logger.info("关节限位已设置")
        return True
    
    def set_gripper_limits(self, gripper_limits: tuple):
        """设置夹爪限位"""
        self.gripper_limits = gripper_limits
        logger.info("夹爪限位已设置")
        return True
    
    def set_motion_parameters(self, max_velocity: float = None, 
                            max_acceleration: float = None):
        """设置运动参数"""
        if max_velocity is not None:
            self.max_joint_velocity = max_velocity
        if max_acceleration is not None:
            self.max_joint_acceleration = max_acceleration
        logger.info("运动参数已设置")
    
    def set_callbacks(self, progress_callback: Callable = None,
                     completion_callback: Callable = None,
                     error_callback: Callable = None):
        """设置回调函数"""
        self.progress_callback = progress_callback
        self.completion_callback = completion_callback
        self.error_callback = error_callback
        logger.info("回调函数已设置")
    
    def reset_simulation(self):
        """重置仿真"""
        if self.is_connected:
            self.mujoco_manager.reset_simulation()
            logger.info("仿真已重置")
    
    def __del__(self):
        """析构函数"""
        try:
            self.disconnect()
        except Exception as e:
            logger.error(f"机械臂仿真器析构异常: {e}")