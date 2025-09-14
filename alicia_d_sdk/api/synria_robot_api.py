"""
SynriaRobotAPI - 用户层API

职责：
- 提供简洁统一的用户接口
- 高级运动命令封装
- 状态查询接口
- 系统控制功能
- 参数验证和错误处理
"""

import time
from typing import List, Optional, Dict, Any, Callable, Union
import numpy as np

from ..hardware import ServoDriver
from ..execution import HardwareExecutor
from ..control import MotionController, StateManager
from ..planning import TrajectoryPlanner, OnlineInterpolator
from ..kinematics import RobotModel, IKController
from ..utils.logger import logger


class SynriaRobotAPI:
    """Synria机械臂API - 提供统一的用户接口"""
    
    def __init__(self,
                 servo_driver: ServoDriver,
                 robot_model: RobotModel,
                 ik_controller: IKController):
        """
        初始化Synria机械臂API
        
        Args:
            servo_driver: 舵机驱动
            robot_model: 机器人模型
            ik_controller: IK控制器
        """
        # 核心组件
        self.servo_driver = servo_driver
        self.robot_model = robot_model
        self.ik_controller = ik_controller
        
        # 创建各层组件
        self.hardware_executor = HardwareExecutor(servo_driver)
        self.motion_controller = MotionController(
            servo_driver=servo_driver,
            robot_model=robot_model,
            ik_controller=ik_controller,
            hardware_executor=self.hardware_executor
        )
        self.state_manager = StateManager(
            servo_driver=servo_driver,
            robot_model=robot_model
        )
        self.trajectory_planner = TrajectoryPlanner(
            robot_model=robot_model,
            ik_controller=ik_controller
        )
        self.online_interpolator = OnlineInterpolator(servo_driver)
        
        # 默认参数
        self.home_angles = [0.0] * 6
        self.home_pose = [0.3086, -0.0025, 0.0890, 0.0029, 0.9310, -0.0028, 0.3649]
        
        # 安全参数
        self.joint_limits = [
            (-3.14, 3.14),  # 关节1
            (-1.57, 1.57),  # 关节2
            (-3.14, 3.14),  # 关节3
            (-3.14, 3.14),  # 关节4
            (-1.57, 1.57),  # 关节5
            (-3.14, 3.14),  # 关节6
        ]
        
        logger.info("初始化Synria机械臂API")
    
    # ==================== 连接管理 ====================
    
    def connect(self) -> bool:
        """连接到机械臂"""
        result = self.servo_driver.connect()
        if result:
            self.state_manager.start_monitoring()
        return result
    
    def disconnect(self):
        """断开与机械臂的连接"""
        self.stop_all_motion()
        self.state_manager.stop_monitoring()
        self.servo_driver.disconnect()
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.servo_driver.serial_comm.is_connected()
    
    # ==================== 关节空间运动 ====================
    
    def moveJ(self,
              target_joints: List[float],
              joint_format: str = 'rad',
              speed_factor: float = 1.0,
              interpolation_type: str = "cubic",
              progress_callback: Optional[Callable] = None,
              completion_callback: Optional[Callable] = None,
              error_callback: Optional[Callable] = None) -> bool:
        """
        关节空间运动
        
        Args:
            target_joints: 目标关节角度
            joint_format: 角度单位 ('rad' 或 'deg')
            speed_factor: 速度因子
            interpolation_type: 插值类型
            progress_callback: 进度回调
            completion_callback: 完成回调
            error_callback: 错误回调
            
        Returns:
            bool: 是否成功开始运动
        """
        if not self.is_connected():
            logger.error("机械臂未连接")
            return False
        
        # 参数验证和转换
        if joint_format.lower() == 'deg':
            target_joints = [angle * np.pi / 180.0 for angle in target_joints]
        elif joint_format.lower() != 'rad':
            logger.error("不支持的关节格式，应为 'rad' 或 'deg'")
            return False
        
        if len(target_joints) != 6:
            logger.error("关节角度数量错误，需要6个关节")
            return False
        
        # 检查关节限位
        target_joints = self._check_and_clip_joint_limits(target_joints)
        
        # 获取当前关节角度
        current_joints = self.get_joints()
        if not current_joints:
            logger.error("无法获取当前关节角度")
            return False
        
        # 规划轨迹
        joint_trajectory = self.trajectory_planner.plan_joint_trajectory(
            start_angles=current_joints,
            target_angles=target_joints,
            speed_factor=speed_factor,
            interpolation_type=interpolation_type
        )
        
        if not joint_trajectory:
            logger.error("关节轨迹规划失败")
            return False
        
        # 执行轨迹
        logger.info(f"开始关节空间运动: {len(joint_trajectory)}个点")
        return self.motion_controller.execute_joint_trajectory(
            joint_trajectory=joint_trajectory,
            progress_callback=progress_callback,
            completion_callback=completion_callback,
            error_callback=error_callback
        )
    
    def moveJ_waypoints(self,
                       waypoints: List[List[float]],
                       joint_format: str = 'rad',
                       speed_factor: float = 1.0,
                       interpolation_type: str = "cubic",
                       progress_callback: Optional[Callable] = None,
                       completion_callback: Optional[Callable] = None,
                       error_callback: Optional[Callable] = None) -> bool:
        """
        关节空间多点运动
        
        Args:
            waypoints: 关节角度路径点列表
            joint_format: 角度单位
            speed_factor: 速度因子
            interpolation_type: 插值类型
            progress_callback: 进度回调
            completion_callback: 完成回调
            error_callback: 错误回调
            
        Returns:
            bool: 是否成功开始运动
        """
        if not self.is_connected():
            logger.error("机械臂未连接")
            return False
        
        # 参数验证和转换
        if joint_format.lower() == 'deg':
            waypoints = [[angle * np.pi / 180.0 for angle in wp] for wp in waypoints]
        elif joint_format.lower() != 'rad':
            logger.error("不支持的关节格式，应为 'rad' 或 'deg'")
            return False
        
        for i, wp in enumerate(waypoints):
            if len(wp) != 6:
                logger.error(f"第{i+1}个路径点关节数量错误")
                return False
        
        # 检查关节限位
        waypoints = [self._check_and_clip_joint_limits(wp) for wp in waypoints]
        
        # 规划轨迹
        joint_trajectory = self.trajectory_planner.plan_joint_waypoints(
            waypoints=waypoints,
            speed_factor=speed_factor,
            interpolation_type=interpolation_type
        )
        
        if not joint_trajectory:
            logger.error("关节多点轨迹规划失败")
            return False
        
        # 执行轨迹
        logger.info(f"开始关节空间多点运动: {len(joint_trajectory)}个点")
        return self.motion_controller.execute_joint_trajectory(
            joint_trajectory=joint_trajectory,
            progress_callback=progress_callback,
            completion_callback=completion_callback,
            error_callback=error_callback
        )
    
    # ==================== 笛卡尔空间运动 ====================
    
    def moveCartesian(self,
                     waypoints: Union[List[List[float]], List[float]],
                     speed_factor: float = 1.0,
                     interpolation_type: str = "linear",
                     progress_callback: Optional[Callable] = None,
                     completion_callback: Optional[Callable] = None,
                     error_callback: Optional[Callable] = None) -> bool:
        """
        笛卡尔空间运动
        
        Args:
            waypoints: 位姿路径点 [x, y, z, qx, qy, qz, qw]
            speed_factor: 速度因子
            interpolation_type: 插值类型
            progress_callback: 进度回调
            completion_callback: 完成回调
            error_callback: 错误回调
            
        Returns:
            bool: 是否成功开始运动
        """
        if not self.is_connected():
            logger.error("机械臂未连接")
            return False
        
        # 参数处理
        if isinstance(waypoints[0], (int, float)) and len(waypoints) == 7:
            waypoints = [waypoints]
        
        for i, wp in enumerate(waypoints):
            if len(wp) != 7:
                logger.error(f"第{i+1}个路径点位姿维度错误")
                return False
        
        # 获取当前关节角度
        current_joints = self.get_joints()
        if not current_joints:
            logger.error("无法获取当前关节角度")
            return False
        
        # 规划轨迹
        joint_trajectory, pose_trajectory = self.trajectory_planner.plan_cartesian_trajectory(
            start_angles=current_joints,
            waypoints=waypoints,
            speed_factor=speed_factor,
            interpolation_type=interpolation_type
        )
        
        if not joint_trajectory:
            logger.error("笛卡尔轨迹规划失败")
            return False
        
        # 执行轨迹
        logger.info(f"开始笛卡尔空间运动: {len(joint_trajectory)}个点")
        return self.motion_controller.execute_joint_trajectory(
            joint_trajectory=joint_trajectory,
            progress_callback=progress_callback,
            completion_callback=completion_callback,
            error_callback=error_callback
        )
    
    def movePose(self,
                target_pose: List[float],
                speed_factor: float = 1.0,
                interpolation_type: str = "linear",
                progress_callback: Optional[Callable] = None,
                completion_callback: Optional[Callable] = None,
                error_callback: Optional[Callable] = None) -> bool:
        """
        移动到指定位姿
        
        Args:
            target_pose: 目标位姿 [x, y, z, qx, qy, qz, qw]
            speed_factor: 速度因子
            interpolation_type: 插值类型
            progress_callback: 进度回调
            completion_callback: 完成回调
            error_callback: 错误回调
            
        Returns:
            bool: 是否成功开始运动
        """
        return self.moveCartesian(
            waypoints=[target_pose],
            speed_factor=speed_factor,
            interpolation_type=interpolation_type,
            progress_callback=progress_callback,
            completion_callback=completion_callback,
            error_callback=error_callback
        )
    
    # ==================== 在线控制 ====================
    
    def start_online_control(self,
                            command_rate_hz: float = 200.0,
                            max_joint_velocity: Optional[float] = None,
                            max_joint_acceleration: Optional[float] = None) -> bool:
        """
        启动在线控制
        
        Args:
            command_rate_hz: 控制频率
            max_joint_velocity: 最大关节速度
            max_joint_acceleration: 最大关节加速度
            
        Returns:
            bool: 是否成功启动
        """
        if not self.is_connected():
            logger.error("机械臂未连接")
            return False
        
        return self.motion_controller.start_online_control(
            command_rate_hz=command_rate_hz,
            max_joint_velocity=max_joint_velocity,
            max_joint_acceleration=max_joint_acceleration
        )
    
    def stop_online_control(self) -> bool:
        """停止在线控制"""
        return self.motion_controller.stop_online_control()
    
    def set_joint_target(self, joint_angles: List[float]) -> bool:
        """设置关节目标"""
        if len(joint_angles) != 6:
            logger.error("关节角度数量错误")
            return False
        
        # 检查关节限位
        joint_angles = self._check_and_clip_joint_limits(joint_angles)
        
        return self.motion_controller.set_online_target(joint_angles=joint_angles)
    
    def set_pose_target(self, pose: List[float]) -> bool:
        """设置位姿目标"""
        if len(pose) != 7:
            logger.error("位姿维度错误")
            return False
        
        # 转换为关节角度
        current_joints = self.get_joints()
        if not current_joints:
            logger.error("无法获取当前关节角度")
            return False
        
        joint_angles = self.ik_controller.solve_ik(
            pose_traj=[pose],
            initial_angles=current_joints,
            output_format='as_list'
        )
        
        if not joint_angles:
            logger.error("IK求解失败")
            return False
        
        return self.set_joint_target(joint_angles[0])
    
    # ==================== 夹爪控制 ====================
    
    def gripper_control(self,
                       command: Optional[str] = None,
                       angle_deg: Optional[float] = None,
                       wait_for_completion: bool = True,
                       timeout: float = 5.0,
                       tolerance: float = 1.0) -> bool:
        """
        夹爪控制
        
        Args:
            command: 命令 ("open" 或 "close")
            angle_deg: 角度 (0-100度)
            wait_for_completion: 是否等待完成
            timeout: 超时时间
            tolerance: 容差
            
        Returns:
            bool: 是否成功
        """
        if command is not None and angle_deg is not None:
            logger.error("command 与 angle_deg 参数不可同时指定")
            return False
        
        if command is not None:
            if command == "open":
                angle_deg = 0.0
            elif command == "close":
                angle_deg = 100.0
            else:
                logger.error("command 参数必须是 'open' 或 'close'")
                return False
        
        if angle_deg is None:
            logger.error("必须提供 command 或 angle_deg 参数")
            return False
        
        # 转换为弧度
        angle_rad = angle_deg * np.pi / 180.0
        
        # 发送夹爪命令
        success = self.servo_driver.set_gripper(angle_rad)
        if not success:
            logger.error("夹爪命令发送失败")
            return False
        
        if wait_for_completion:
            start_time = time.time()
            while time.time() - start_time < timeout:
                current_gripper = self.get_gripper()
                if current_gripper is not None:
                    current_deg = current_gripper * 180.0 / np.pi
                    if abs(current_deg - angle_deg) <= tolerance:
                        logger.info(f"夹爪已到达目标角度: {angle_deg:.1f}°")
                        return True
                time.sleep(0.1)
            
            logger.warning("夹爪运动等待超时")
            return False
        
        return True
    
    # ==================== 状态查询 ====================
    
    def get_joints(self) -> Optional[List[float]]:
        """获取当前关节角度（弧度）"""
        return self.state_manager.get_joint_angles()
    
    def get_pose(self) -> Optional[List[float]]:
        """获取当前位姿 [x, y, z, qx, qy, qz, qw]"""
        return self.state_manager.get_pose()
    
    def get_gripper(self) -> Optional[float]:
        """获取当前夹爪角度（弧度）"""
        return self.state_manager.get_gripper_angle()
    
    def is_moving(self) -> bool:
        """是否正在运动"""
        return self.state_manager.is_moving()
    
    def is_online_control_active(self) -> bool:
        """在线控制是否激活"""
        return self.state_manager.is_online_control_active()
    
    def is_emergency_stop(self) -> bool:
        """是否紧急停止"""
        return self.state_manager.is_emergency_stop()
    
    # ==================== 系统控制 ====================
    
    def moveHome(self) -> bool:
        """移动到初始位置"""
        logger.info("移动到初始位置")
        return self.moveJ(target_joints=self.home_angles)
    
    def torque_control(self, command: str) -> bool:
        """
        扭矩控制
        
        Args:
            command: "on" 或 "off"
            
        Returns:
            bool: 是否成功
        """
        if command == "on":
            logger.info("开启扭矩")
            return self.servo_driver.enable_torque()
        elif command == "off":
            logger.info("关闭扭矩")
            return self.servo_driver.disable_torque()
        else:
            logger.error("command 参数必须是 'on' 或 'off'")
            return False
    
    def zero_calibration(self) -> bool:
        """归零校准"""
        logger.info("开始归零校准")
        
        # 关闭扭矩
        if not self.torque_control('off'):
            logger.error("扭矩关闭失败")
            return False
        
        input("请手动拖动机械臂到零点位置，然后按回车继续...")
        
        # 重新开启扭矩
        if not self.torque_control('on'):
            logger.error("扭矩开启失败")
            return False
        
        # 执行零点校准
        result = self.servo_driver.set_zero_position()
        if result:
            logger.info("归零校准成功")
        else:
            logger.error("归零校准失败")
        
        return result
    
    def emergency_stop(self) -> bool:
        """紧急停止"""
        logger.warning("执行紧急停止")
        return self.motion_controller.emergency_stop()
    
    def clear_emergency_stop(self) -> bool:
        """清除紧急停止状态"""
        logger.info("清除紧急停止状态")
        return self.motion_controller.clear_emergency_stop()
    
    def stop_all_motion(self) -> bool:
        """停止所有运动"""
        logger.info("停止所有运动")
        
        # 停止轨迹执行
        if self.motion_controller.is_executing():
            self.hardware_executor.stop_execution()
        
        # 停止在线控制
        if self.motion_controller.is_online_control_active():
            self.motion_controller.stop_online_control()
        
        return True
    
    # ==================== 配置接口 ====================
    
    def set_home_position(self, joint_angles: List[float]):
        """设置初始位置"""
        if len(joint_angles) != 6:
            logger.error("关节角度数量错误")
            return
        
        self.home_angles = joint_angles.copy()
        logger.info("初始位置已设置")
    
    def set_joint_limits(self, joint_limits: List[tuple]):
        """设置关节限位"""
        if len(joint_limits) != 6:
            logger.error("关节限位数量错误")
            return
        
        self.joint_limits = joint_limits
        self.motion_controller.set_joint_limits(joint_limits)
        logger.info("关节限位已设置")
    
    def set_cartesian_limits(self, cartesian_limits: Dict[str, tuple]):
        """设置笛卡尔限位"""
        self.motion_controller.set_cartesian_limits(cartesian_limits)
        logger.info("笛卡尔限位已设置")
    
    # ==================== 内部方法 ====================
    
    def _check_and_clip_joint_limits(self, joint_angles: List[float]) -> List[float]:
        """检查并裁剪关节限位"""
        clipped_angles = []
        violations = []
        
        for i, angle in enumerate(joint_angles):
            if i < len(self.joint_limits):
                min_limit, max_limit = self.joint_limits[i]
                clipped_angle = max(min_limit, min(angle, max_limit))
                clipped_angles.append(clipped_angle)
                
                if clipped_angle != angle:
                    violations.append((i, angle, clipped_angle))
            else:
                clipped_angles.append(angle)
        
        if violations:
            logger.warning(f"有{len(violations)}个关节角度被裁剪到限位内")
            for joint_idx, original, clipped in violations:
                logger.warning(f"关节{joint_idx+1}: {original:.3f} -> {clipped:.3f}")
        
        return clipped_angles
    
    def print_state(self, continuous: bool = False, output_format: str = "deg"):
        """打印当前状态"""
        def _print_once():
            joints = self.get_joints()
            pose = self.get_pose()
            gripper = self.get_gripper()
            
            if joints is None:
                logger.warning("无法获取关节状态")
                return
            
            if output_format == 'deg':
                joint_deg = [angle * 180.0 / np.pi for angle in joints]
                gripper_deg = gripper * 180.0 / np.pi if gripper else 0.0
                unit = "°"
            else:
                joint_deg = joints
                gripper_deg = gripper if gripper else 0.0
                unit = "rad"
            
            logger.info(f"关节角度 ({unit}): {[round(a, 2) for a in joint_deg]}")
            if pose:
                logger.info(f"位姿: {[round(p, 3) for p in pose[:3]]} {[round(q, 3) for q in pose[3:]]}")
            logger.info(f"夹爪角度 ({unit}): {round(gripper_deg, 2)}")
        
        if continuous:
            logger.info("开始连续状态打印，按 Ctrl+C 停止")
            try:
                while True:
                    _print_once()
                    time.sleep(0.5)
            except KeyboardInterrupt:
                logger.info("停止连续状态打印")
        else:
            _print_once()
    
    def __del__(self):
        """析构函数"""
        try:
            self.stop_all_motion()
            self.disconnect()
        except Exception as e:
            logger.error(f"SynriaRobotAPI析构异常: {e}")