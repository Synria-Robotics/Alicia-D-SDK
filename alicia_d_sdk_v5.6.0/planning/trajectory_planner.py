"""
TrajectoryPlanner - 轨迹规划器

职责：
- 提供统一的轨迹规划接口
- 协调不同类型的规划器
- 处理规划参数和配置
- 提供规划结果验证
"""

from typing import List, Optional, Dict, Any, Union, Tuple
from abc import ABC, abstractmethod
import numpy as np

from .joint_space_planner import JointSpacePlanner
from .cartesian_space_planner import CartesianSpacePlanner
from ..kinematics import RobotModel, IKController
from ..utils.logger import logger


class TrajectoryPlanner:
    """轨迹规划器 - 提供统一的轨迹规划接口"""
    
    def __init__(self, 
                 robot_model: RobotModel,
                 ik_controller: IKController):
        """
        初始化轨迹规划器
        
        Args:
            robot_model: 机器人模型
            ik_controller: IK控制器
        """
        self.robot_model = robot_model
        self.ik_controller = ik_controller
        
        # 创建子规划器
        self.joint_planner = JointSpacePlanner()
        self.cartesian_planner = CartesianSpacePlanner()
        
        # 规划参数
        self.default_steps = 200
        self.min_steps = 10
        self.max_steps = 1000
        self.default_delay = 0.02
        
        logger.info("初始化轨迹规划器")
    
    # ==================== 关节空间规划 ====================
    
    def plan_joint_trajectory(self,
                             start_angles: List[float],
                             target_angles: List[float],
                             steps: Optional[int] = None,
                             speed_factor: float = 1.0,
                             interpolation_type: str = "cubic") -> List[List[float]]:
        """
        规划关节空间轨迹
        
        Args:
            start_angles: 起始关节角度
            target_angles: 目标关节角度
            steps: 插值步数，None则自动计算
            speed_factor: 速度因子
            interpolation_type: 插值类型 ("linear", "cubic", "quintic")
            
        Returns:
            List[List[float]]: 关节轨迹
        """
        if len(start_angles) != 6 or len(target_angles) != 6:
            logger.error("关节角度数量错误")
            return []
        
        if steps is None:
            steps = self._calculate_steps(start_angles, target_angles, speed_factor)
        
        steps = max(self.min_steps, min(steps, self.max_steps))
        
        logger.info(f"规划关节轨迹: {steps}步, 插值类型: {interpolation_type}")
        
        return self.joint_planner.plan(
            start_angles=start_angles,
            target_angles=target_angles,
            steps=steps,
            interpolation_type=interpolation_type
        )
    
    def plan_joint_waypoints(self,
                            waypoints: List[List[float]],
                            steps_per_segment: Optional[int] = None,
                            speed_factor: float = 1.0,
                            interpolation_type: str = "cubic") -> List[List[float]]:
        """
        规划关节空间多点轨迹
        
        Args:
            waypoints: 关节角度路径点列表
            steps_per_segment: 每段插值步数
            speed_factor: 速度因子
            interpolation_type: 插值类型
            
        Returns:
            List[List[float]]: 完整关节轨迹
        """
        if not waypoints or len(waypoints) < 2:
            logger.error("路径点数量不足")
            return []
        
        for i, wp in enumerate(waypoints):
            if len(wp) != 6:
                logger.error(f"第{i+1}个路径点关节数量错误")
                return []
        
        full_trajectory = []
        
        for i in range(len(waypoints) - 1):
            start_angles = waypoints[i]
            target_angles = waypoints[i + 1]
            
            # 计算每段步数
            if steps_per_segment is None:
                segment_steps = self._calculate_steps(start_angles, target_angles, speed_factor)
            else:
                segment_steps = steps_per_segment
            
            # 规划当前段
            segment_trajectory = self.plan_joint_trajectory(
                start_angles=start_angles,
                target_angles=target_angles,
                steps=segment_steps,
                speed_factor=speed_factor,
                interpolation_type=interpolation_type
            )
            
            if not segment_trajectory:
                logger.error(f"第{i+1}段轨迹规划失败")
                return []
            
            # 添加到完整轨迹（跳过重复的中间点）
            if i == 0:
                full_trajectory.extend(segment_trajectory)
            else:
                full_trajectory.extend(segment_trajectory[1:])
        
        logger.info(f"规划关节多点轨迹完成: {len(full_trajectory)}个点")
        return full_trajectory
    
    # ==================== 笛卡尔空间规划 ====================
    
    def plan_cartesian_trajectory(self,
                                 start_angles: List[float],
                                 waypoints: List[List[float]],
                                 steps_per_segment: Optional[int] = None,
                                 speed_factor: float = 1.0,
                                 interpolation_type: str = "linear") -> Tuple[List[List[float]], List[List[float]]]:
        """
        规划笛卡尔空间轨迹
        
        Args:
            start_angles: 起始关节角度
            waypoints: 位姿路径点列表 [x, y, z, qx, qy, qz, qw]
            steps_per_segment: 每段插值步数
            speed_factor: 速度因子
            interpolation_type: 插值类型 ("linear", "cubic")
            
        Returns:
            Tuple[List[List[float]], List[List[float]]]: (关节轨迹, 位姿轨迹)
        """
        if len(start_angles) != 6:
            logger.error("起始关节角度数量错误")
            return [], []
        
        if not waypoints:
            logger.error("位姿路径点为空")
            return [], []
        
        for i, wp in enumerate(waypoints):
            if len(wp) != 7:
                logger.error(f"第{i+1}个位姿路径点维度错误")
                return [], []
        
        # 计算起始位姿
        start_pos, start_quat = self.robot_model.forward_kinematics(start_angles)
        start_pose = np.concatenate([start_pos, start_quat]).tolist()
        
        # 规划位姿轨迹
        all_waypoints = [start_pose] + waypoints
        pose_trajectory = self.cartesian_planner.plan_waypoints(
            waypoints=all_waypoints,
            steps_per_segment=steps_per_segment,
            speed_factor=speed_factor,
            interpolation_type=interpolation_type
        )
        
        if not pose_trajectory:
            logger.error("位姿轨迹规划失败")
            return [], []
        
        # 转换为关节轨迹
        joint_trajectory = self._convert_pose_to_joint_trajectory(pose_trajectory, start_angles)
        
        if not joint_trajectory:
            logger.error("位姿轨迹转换为关节轨迹失败")
            return [], []
        
        logger.info(f"规划笛卡尔轨迹完成: {len(joint_trajectory)}个点")
        return joint_trajectory, pose_trajectory
    
    def plan_cartesian_single(self,
                             start_angles: List[float],
                             target_pose: List[float],
                             steps: Optional[int] = None,
                             speed_factor: float = 1.0,
                             interpolation_type: str = "linear") -> Tuple[List[List[float]], List[List[float]]]:
        """
        规划单个笛卡尔目标轨迹
        
        Args:
            start_angles: 起始关节角度
            target_pose: 目标位姿 [x, y, z, qx, qy, qz, qw]
            steps: 插值步数
            speed_factor: 速度因子
            interpolation_type: 插值类型
            
        Returns:
            Tuple[List[List[float]], List[List[float]]]: (关节轨迹, 位姿轨迹)
        """
        return self.plan_cartesian_trajectory(
            start_angles=start_angles,
            waypoints=[target_pose],
            steps_per_segment=steps,
            speed_factor=speed_factor,
            interpolation_type=interpolation_type
        )
    
    # ==================== 夹爪轨迹规划 ====================
    
    def plan_gripper_trajectory(self,
                               start_angle: float,
                               target_angle: float,
                               steps: Optional[int] = None,
                               speed_factor: float = 1.0,
                               interpolation_type: str = "linear") -> List[float]:
        """
        规划夹爪轨迹
        
        Args:
            start_angle: 起始夹爪角度
            target_angle: 目标夹爪角度
            steps: 插值步数
            speed_factor: 速度因子
            interpolation_type: 插值类型
            
        Returns:
            List[float]: 夹爪轨迹
        """
        if steps is None:
            angle_diff = abs(target_angle - start_angle)
            steps = max(self.min_steps, int(angle_diff * 50 * speed_factor))
        
        steps = max(self.min_steps, min(steps, self.max_steps))
        
        if interpolation_type == "linear":
            return self._linear_interpolation(start_angle, target_angle, steps)
        elif interpolation_type == "cubic":
            return self._cubic_interpolation(start_angle, target_angle, steps)
        else:
            logger.warning(f"不支持的夹爪插值类型: {interpolation_type}，使用线性插值")
            return self._linear_interpolation(start_angle, target_angle, steps)
    
    # ==================== 配置接口 ====================
    
    def set_default_steps(self, steps: int):
        """设置默认插值步数"""
        self.default_steps = max(self.min_steps, min(steps, self.max_steps))
        logger.info(f"设置默认插值步数: {self.default_steps}")
    
    def set_step_limits(self, min_steps: int, max_steps: int):
        """设置插值步数限制"""
        self.min_steps = max(1, min_steps)
        self.max_steps = max(self.min_steps, max_steps)
        logger.info(f"设置插值步数限制: {self.min_steps} - {self.max_steps}")
    
    def set_default_delay(self, delay: float):
        """设置默认执行延迟"""
        self.default_delay = max(0.001, delay)
        logger.info(f"设置默认执行延迟: {self.default_delay:.3f}s")
    
    # ==================== 内部方法 ====================
    
    def _calculate_steps(self, start_angles: List[float], target_angles: List[float], speed_factor: float) -> int:
        """计算插值步数"""
        # 计算关节角度变化量
        angle_changes = [abs(t - s) for s, t in zip(start_angles, target_angles)]
        max_change = max(angle_changes)
        
        # 基于最大角度变化计算步数
        base_steps = int(max_change * 100 * speed_factor)
        steps = max(self.min_steps, min(base_steps, self.max_steps))
        
        return steps
    
    def _convert_pose_to_joint_trajectory(self, pose_trajectory: List[List[float]], start_angles: List[float]) -> List[List[float]]:
        """将位姿轨迹转换为关节轨迹"""
        joint_trajectory = []
        current_angles = start_angles.copy()
        
        for pose in pose_trajectory:
            # 使用IK求解关节角度
            joint_angles = self.ik_controller.solve_ik(
                pose_traj=[pose],
                initial_angles=current_angles,
                output_format='as_list'
            )
            
            if not joint_angles:
                logger.error("IK求解失败")
                return []
            
            joint_trajectory.append(joint_angles[0])
            current_angles = joint_angles[0]  # 使用当前解作为下次的初始值
        
        return joint_trajectory
    
    def _linear_interpolation(self, start: float, target: float, steps: int) -> List[float]:
        """线性插值"""
        if steps <= 1:
            return [target]
        
        return [start + (target - start) * i / (steps - 1) for i in range(steps)]
    
    def _cubic_interpolation(self, start: float, target: float, steps: int) -> List[float]:
        """三次插值"""
        if steps <= 1:
            return [target]
        
        def ease_in_out_cubic(t: float) -> float:
            return 4 * t**3 if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2
        
        return [start + (target - start) * ease_in_out_cubic(i / (steps - 1)) for i in range(steps)]
    
    # ==================== 验证方法 ====================
    
    def validate_joint_trajectory(self, trajectory: List[List[float]], joint_limits: Optional[List[tuple]] = None) -> bool:
        """验证关节轨迹"""
        if not trajectory:
            logger.error("轨迹为空")
            return False
        
        for i, point in enumerate(trajectory):
            if len(point) != 6:
                logger.error(f"第{i+1}个轨迹点关节数量错误")
                return False
            
            # 检查关节限位
            if joint_limits:
                for j, angle in enumerate(point):
                    if j < len(joint_limits):
                        min_limit, max_limit = joint_limits[j]
                        if not (min_limit <= angle <= max_limit):
                            logger.error(f"第{i+1}个轨迹点第{j+1}个关节超出限位")
                            return False
        
        return True
    
    def validate_pose_trajectory(self, trajectory: List[List[float]], cartesian_limits: Optional[Dict[str, tuple]] = None) -> bool:
        """验证位姿轨迹"""
        if not trajectory:
            logger.error("轨迹为空")
            return False
        
        for i, pose in enumerate(trajectory):
            if len(pose) != 7:
                logger.error(f"第{i+1}个轨迹点位姿维度错误")
                return False
            
            # 检查笛卡尔限位
            if cartesian_limits:
                x, y, z = pose[:3]
                if 'x' in cartesian_limits:
                    min_x, max_x = cartesian_limits['x']
                    if not (min_x <= x <= max_x):
                        logger.error(f"第{i+1}个轨迹点X坐标超出限位")
                        return False
                # 类似检查Y和Z坐标
        
        return True