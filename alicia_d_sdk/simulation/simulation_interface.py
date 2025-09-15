"""
仿真接口适配器

提供与真实机械臂API完全兼容的仿真接口。
"""

from typing import List, Optional, Dict, Any, Callable
import time
import threading

from .robot_simulator import RobotSimulator
from ..utils.logger import logger


class SimulationInterface:
    """仿真接口适配器 - 提供与真实机械臂API兼容的接口"""
    
    def __init__(self, model_path: str = None, enable_viewer: bool = True, end_effector_body_name: str = None):
        """
        初始化仿真接口
        
        Args:
            model_path: MuJoCo模型文件路径
            enable_viewer: 是否启用可视化
        """
        self.simulator = RobotSimulator(model_path, enable_viewer, end_effector_body_name=end_effector_body_name)
        
        # 状态管理
        self.is_connected = False
        self.is_moving = False
        self.is_online_control = False
        self.emergency_stop = False
        
        # 配置参数
        self.joint_limits = [
            (-3.14, 3.14),  # 关节1
            (-1.57, 1.57),  # 关节2
            (-3.14, 3.14),  # 关节3
            (-3.14, 3.14),  # 关节4
            (-1.57, 1.57),  # 关节5
            (-3.14, 3.14),  # 关节6
        ]
        
        self.gripper_limits = (0.0, 1.57)
        
        # 运动参数
        self.max_joint_velocity = 2.5
        self.max_joint_acceleration = 8.0
        self.default_speed_factor = 1.0
        
        # 回调函数
        self.progress_callback: Optional[Callable] = None
        self.completion_callback: Optional[Callable] = None
        self.error_callback: Optional[Callable] = None
        
        logger.info("初始化仿真接口适配器")
    
    def connect(self) -> bool:
        """
        连接仿真环境
        
        Returns:
            bool: 是否连接成功
        """
        try:
            success = self.simulator.connect()
            if success:
                self.is_connected = True
                logger.info("仿真接口连接成功")
            else:
                logger.error("仿真接口连接失败")
            return success
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
            success = self.simulator.disconnect()
            if success:
                self.is_connected = False
                self.is_moving = False
                self.is_online_control = False
                logger.info("仿真接口已断开")
            return success
        except Exception as e:
            logger.error(f"断开仿真环境失败: {e}")
            return False
    
    # ==================== 状态查询接口 ====================
    
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
        
        return self.simulator.get_joint_angles(joint_format)
    
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
        
        return self.simulator.get_gripper_angle(joint_format)
    
    def get_end_effector_pose(self) -> Optional[List[float]]:
        """
        获取末端执行器位姿
        
        Returns:
            List[float]: [x, y, z, qx, qy, qz, qw]
        """
        if not self.is_connected:
            logger.error("仿真环境未连接")
            return None
        
        return self.simulator.get_end_effector_pose()
    
    def is_moving(self) -> bool:
        """检查机械臂是否在运动"""
        return self.is_moving
    
    def is_online_control_active(self) -> bool:
        """检查在线控制是否激活"""
        return self.is_online_control
    
    def is_emergency_stop(self) -> bool:
        """检查是否紧急停止"""
        return self.emergency_stop
    
    # ==================== 运动控制接口 ====================
    
    def moveJ(self, target_joints: List[float], 
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
        
        if self.emergency_stop:
            logger.error("紧急停止状态，无法运动")
            return False
        
        # 检查关节限位
        if not self._check_joint_limits(target_joints, joint_format):
            return False
        
        logger.info(f"执行关节运动: {target_joints}")
        
        # 设置回调函数
        self.simulator.set_callbacks(
            progress_callback=self._progress_callback,
            completion_callback=self._completion_callback,
            error_callback=self._error_callback
        )
        
        # 执行运动
        success = self.simulator.move_joint(
            target_joints, joint_format, speed_factor, interpolation_type
        )
        
        return success
    
    def moveGripper(self, target_angle: float,
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
        
        if self.emergency_stop:
            logger.error("紧急停止状态，无法运动")
            return False
        
        # 检查夹爪限位
        if not self._check_gripper_limits(target_angle, joint_format):
            return False
        
        logger.info(f"执行夹爪运动: {target_angle}")
        
        # 设置回调函数
        self.simulator.set_callbacks(
            progress_callback=self._progress_callback,
            completion_callback=self._completion_callback,
            error_callback=self._error_callback
        )
        
        # 执行运动
        success = self.simulator.move_gripper(
            target_angle, joint_format, speed_factor
        )
        
        return success
    
    def moveJ_waypoints(self, waypoints: List[List[float]],
                       joint_format: str = 'rad',
                       speed_factor: float = 1.0,
                       interpolation_type: str = 'cubic') -> bool:
        """
        多点关节轨迹运动
        
        Args:
            waypoints: 轨迹点列表
            joint_format: 角度格式
            speed_factor: 速度因子
            interpolation_type: 插值类型
            
        Returns:
            bool: 是否执行成功
        """
        if not self.is_connected:
            logger.error("仿真环境未连接")
            return False
        
        if self.emergency_stop:
            logger.error("紧急停止状态，无法运动")
            return False
        
        if not waypoints:
            logger.error("轨迹点列表为空")
            return False
        
        logger.info(f"执行多点轨迹运动: {len(waypoints)}个点")
        
        # 设置回调函数
        self.simulator.set_callbacks(
            progress_callback=self._progress_callback,
            completion_callback=self._completion_callback,
            error_callback=self._error_callback
        )
        
        # 逐点执行轨迹
        for i, waypoint in enumerate(waypoints):
            if not self._check_joint_limits(waypoint, joint_format):
                logger.error(f"第{i+1}个轨迹点超出限位")
                return False
            
            success = self.simulator.move_joint(
                waypoint, joint_format, speed_factor, interpolation_type
            )
            
            if not success:
                logger.error(f"执行第{i+1}个轨迹点失败")
                return False
        
        return True
    
    def stop_motion(self):
        """停止运动"""
        if self.is_moving:
            self.simulator.stop_motion()
            self.is_moving = False
            logger.info("运动已停止")
    
    def emergency_stop_robot(self):
        """紧急停止机械臂"""
        self.emergency_stop = True
        self.stop_motion()
        logger.warning("紧急停止已激活")
    
    def clear_emergency_stop(self):
        """清除紧急停止"""
        self.emergency_stop = False
        logger.info("紧急停止已清除")
    
    # ==================== 在线控制接口 ====================
    
    def start_online_control(self, command_rate_hz: float = 200.0) -> bool:
        """
        启动在线控制
        
        Args:
            command_rate_hz: 控制频率
            
        Returns:
            bool: 是否启动成功
        """
        if not self.is_connected:
            logger.error("仿真环境未连接")
            return False
        
        if self.emergency_stop:
            logger.error("紧急停止状态，无法启动在线控制")
            return False
        
        self.is_online_control = True
        logger.info(f"在线控制已启动，频率: {command_rate_hz}Hz")
        return True
    
    def stop_online_control(self) -> bool:
        """
        停止在线控制
        
        Returns:
            bool: 是否停止成功
        """
        self.is_online_control = False
        logger.info("在线控制已停止")
        return True
    
    def set_joint_target(self, target_joints: List[float], 
                        joint_format: str = 'rad') -> bool:
        """
        设置在线控制目标
        
        Args:
            target_joints: 目标关节角度
            joint_format: 角度格式
            
        Returns:
            bool: 是否设置成功
        """
        if not self.is_online_control:
            logger.error("在线控制未激活")
            return False
        
        if not self._check_joint_limits(target_joints, joint_format):
            return False
        
        # 直接设置关节角度（在线控制模式）
        return self.simulator.set_joint_angles(target_joints, joint_format)
    
    def set_gripper_target(self, target_angle: float,
                          joint_format: str = 'rad') -> bool:
        """
        设置夹爪目标
        
        Args:
            target_angle: 目标夹爪角度
            joint_format: 角度格式
            
        Returns:
            bool: 是否设置成功
        """
        if not self.is_online_control:
            logger.error("在线控制未激活")
            return False
        
        if not self._check_gripper_limits(target_angle, joint_format):
            return False
        
        # 直接设置夹爪角度
        return self.simulator.set_gripper_angle(target_angle, joint_format)
    
    # ==================== 配置接口 ====================
    
    def set_joint_limits(self, joint_limits: List[tuple]) -> bool:
        """
        设置关节限位
        
        Args:
            joint_limits: 关节限位列表
            
        Returns:
            bool: 是否设置成功
        """
        if len(joint_limits) != 6:
            logger.error("关节限位数量错误")
            return False
        
        self.joint_limits = joint_limits
        self.simulator.set_joint_limits(joint_limits)
        logger.info("关节限位已设置")
        return True
    
    def set_gripper_limits(self, gripper_limits: tuple) -> bool:
        """
        设置夹爪限位
        
        Args:
            gripper_limits: 夹爪限位
            
        Returns:
            bool: 是否设置成功
        """
        self.gripper_limits = gripper_limits
        self.simulator.set_gripper_limits(gripper_limits)
        logger.info("夹爪限位已设置")
        return True
    
    def set_motion_parameters(self, max_velocity: float = None,
                            max_acceleration: float = None) -> bool:
        """
        设置运动参数
        
        Args:
            max_velocity: 最大关节速度
            max_acceleration: 最大关节加速度
            
        Returns:
            bool: 是否设置成功
        """
        if max_velocity is not None:
            self.max_joint_velocity = max_velocity
        if max_acceleration is not None:
            self.max_joint_acceleration = max_acceleration
        
        self.simulator.set_motion_parameters(max_velocity, max_acceleration)
        logger.info("运动参数已设置")
        return True
    
    def set_callbacks(self, progress_callback: Callable = None,
                     completion_callback: Callable = None,
                     error_callback: Callable = None):
        """
        设置回调函数
        
        Args:
            progress_callback: 进度回调
            completion_callback: 完成回调
            error_callback: 错误回调
        """
        self.progress_callback = progress_callback
        self.completion_callback = completion_callback
        self.error_callback = error_callback
        logger.info("回调函数已设置")
    
    def reset_simulation(self):
        """重置仿真"""
        if self.is_connected:
            self.simulator.reset_simulation()
            logger.info("仿真已重置")
    
    # ==================== 内部方法 ====================
    
    def _check_joint_limits(self, joint_angles: List[float], 
                           joint_format: str) -> bool:
        """检查关节限位"""
        if len(joint_angles) != 6:
            logger.error("关节角度数量错误")
            return False
        
        # 转换角度格式
        if joint_format == 'deg':
            joint_angles = [self._deg_to_rad(angle) for angle in joint_angles]
        
        # 检查限位
        for i, angle in enumerate(joint_angles):
            min_limit, max_limit = self.joint_limits[i]
            if not (min_limit <= angle <= max_limit):
                logger.error(f"关节{i+1}角度超出限位: {angle:.3f} not in [{min_limit:.3f}, {max_limit:.3f}]")
                return False
        
        return True
    
    def _check_gripper_limits(self, angle: float, joint_format: str) -> bool:
        """检查夹爪限位"""
        # 转换角度格式
        if joint_format == 'deg':
            angle = self._deg_to_rad(angle)
        
        min_limit, max_limit = self.gripper_limits
        if not (min_limit <= angle <= max_limit):
            logger.error(f"夹爪角度超出限位: {angle:.3f} not in [{min_limit:.3f}, {max_limit:.3f}]")
            return False
        
        return True
    
    def _deg_to_rad(self, angle_deg: float) -> float:
        """度转弧度"""
        import math
        return math.radians(angle_deg)
    
    def _progress_callback(self, current: int, total: int, joint_point: List[float]):
        """进度回调"""
        self.is_moving = True
        if self.progress_callback:
            try:
                self.progress_callback(current, total, joint_point)
            except Exception as e:
                logger.error(f"进度回调执行失败: {e}")
    
    def _completion_callback(self):
        """完成回调"""
        self.is_moving = False
        if self.completion_callback:
            try:
                self.completion_callback()
            except Exception as e:
                logger.error(f"完成回调执行失败: {e}")
    
    def _error_callback(self, error_message: str):
        """错误回调"""
        self.is_moving = False
        if self.error_callback:
            try:
                self.error_callback(error_message)
            except Exception as e:
                logger.error(f"错误回调执行失败: {e}")
    
    def __del__(self):
        """析构函数"""
        try:
            self.disconnect()
        except Exception as e:
            logger.error(f"仿真接口适配器析构异常: {e}")