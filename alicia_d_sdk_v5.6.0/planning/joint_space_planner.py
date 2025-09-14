"""
JointSpacePlanner - 关节空间规划器

职责：
- 关节空间轨迹规划
- 多种插值算法实现
- 关节限位检查
- 速度规划
"""

from typing import List, Optional
import numpy as np

from ..utils.logger import logger


class JointSpacePlanner:
    """关节空间规划器 - 负责关节空间轨迹规划"""
    
    def __init__(self):
        """初始化关节空间规划器"""
        logger.info("初始化关节空间规划器")
    
    def plan(self,
             start_angles: List[float],
             target_angles: List[float],
             steps: int,
             interpolation_type: str = "cubic") -> List[List[float]]:
        """
        规划关节空间轨迹
        
        Args:
            start_angles: 起始关节角度
            target_angles: 目标关节角度
            steps: 插值步数
            interpolation_type: 插值类型 ("linear", "cubic", "quintic")
            
        Returns:
            List[List[float]]: 关节轨迹
        """
        if len(start_angles) != 6 or len(target_angles) != 6:
            logger.error("关节角度数量错误")
            return []
        
        if steps < 1:
            logger.error("插值步数必须大于0")
            return []
        
        logger.info(f"规划关节轨迹: {steps}步, 插值类型: {interpolation_type}")
        
        if interpolation_type == "linear":
            return self._linear_interpolation(start_angles, target_angles, steps)
        elif interpolation_type == "cubic":
            return self._cubic_interpolation(start_angles, target_angles, steps)
        elif interpolation_type == "quintic":
            return self._quintic_interpolation(start_angles, target_angles, steps)
        else:
            logger.warning(f"不支持的插值类型: {interpolation_type}，使用三次插值")
            return self._cubic_interpolation(start_angles, target_angles, steps)
    
    def _linear_interpolation(self, start_angles: List[float], target_angles: List[float], steps: int) -> List[List[float]]:
        """线性插值"""
        trajectory = []
        
        for i in range(steps):
            ratio = i / (steps - 1) if steps > 1 else 1.0
            interpolated = [
                start + (target - start) * ratio
                for start, target in zip(start_angles, target_angles)
            ]
            trajectory.append(interpolated)
        
        return trajectory
    
    def _cubic_interpolation(self, start_angles: List[float], target_angles: List[float], steps: int) -> List[List[float]]:
        """三次插值（缓动函数）"""
        trajectory = []
        
        for i in range(steps):
            t = i / (steps - 1) if steps > 1 else 1.0
            ratio = self._ease_in_out_cubic(t)
            interpolated = [
                start + (target - start) * ratio
                for start, target in zip(start_angles, target_angles)
            ]
            trajectory.append(interpolated)
        
        return trajectory
    
    def _quintic_interpolation(self, start_angles: List[float], target_angles: List[float], steps: int) -> List[List[float]]:
        """五次插值（更平滑的缓动函数）"""
        trajectory = []
        
        for i in range(steps):
            t = i / (steps - 1) if steps > 1 else 1.0
            ratio = self._ease_in_out_quintic(t)
            interpolated = [
                start + (target - start) * ratio
                for start, target in zip(start_angles, target_angles)
            ]
            trajectory.append(interpolated)
        
        return trajectory
    
    @staticmethod
    def _ease_in_out_cubic(t: float) -> float:
        """三次缓动函数"""
        return 4 * t**3 if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2
    
    @staticmethod
    def _ease_in_out_quintic(t: float) -> float:
        """五次缓动函数"""
        return 16 * t**5 if t < 0.5 else 1 - pow(-2 * t + 2, 5) / 2
    
    def plan_with_velocity_profile(self,
                                  start_angles: List[float],
                                  target_angles: List[float],
                                  max_velocity: float = 2.5,
                                  max_acceleration: float = 8.0,
                                  time_step: float = 0.01) -> List[List[float]]:
        """
        带速度剖面的轨迹规划
        
        Args:
            start_angles: 起始关节角度
            target_angles: 目标关节角度
            max_velocity: 最大速度 (rad/s)
            max_acceleration: 最大加速度 (rad/s²)
            time_step: 时间步长 (s)
            
        Returns:
            List[List[float]]: 关节轨迹
        """
        if len(start_angles) != 6 or len(target_angles) != 6:
            logger.error("关节角度数量错误")
            return []
        
        # 计算每个关节的运动时间
        joint_times = []
        for start, target in zip(start_angles, target_angles):
            angle_diff = abs(target - start)
            
            # 计算加速和减速时间
            t_accel = max_velocity / max_acceleration
            t_decel = max_velocity / max_acceleration
            
            # 计算匀速时间
            t_const = max(0, (angle_diff - max_velocity * t_accel) / max_velocity)
            
            # 总时间
            total_time = t_accel + t_const + t_decel
            joint_times.append(total_time)
        
        # 使用最长的关节时间
        total_time = max(joint_times)
        steps = int(total_time / time_step) + 1
        
        logger.info(f"速度剖面规划: 总时间{total_time:.3f}s, {steps}步")
        
        trajectory = []
        for i in range(steps):
            t = i * time_step
            interpolated = []
            
            for j, (start, target) in enumerate(zip(start_angles, target_angles)):
                angle_diff = target - start
                joint_time = joint_times[j]
                
                if t >= joint_time:
                    # 已到达目标
                    interpolated.append(target)
                else:
                    # 计算当前时刻的角度
                    if t <= t_accel:
                        # 加速阶段
                        ratio = 0.5 * (t / t_accel) ** 2
                    elif t <= joint_time - t_decel:
                        # 匀速阶段
                        t_const = joint_time - t_accel - t_decel
                        ratio = 0.5 + (t - t_accel) / t_const * 0.5
                    else:
                        # 减速阶段
                        t_remaining = joint_time - t
                        ratio = 1.0 - 0.5 * (t_remaining / t_decel) ** 2
                    
                    angle = start + angle_diff * ratio
                    interpolated.append(angle)
            
            trajectory.append(interpolated)
        
        return trajectory
    
    def check_joint_limits(self, trajectory: List[List[float]], joint_limits: List[tuple]) -> bool:
        """
        检查关节轨迹是否在限位内
        
        Args:
            trajectory: 关节轨迹
            joint_limits: 关节限位 [(min1, max1), (min2, max2), ...]
            
        Returns:
            bool: 是否在限位内
        """
        if len(joint_limits) != 6:
            logger.error("关节限位数量错误")
            return False
        
        for i, point in enumerate(trajectory):
            if len(point) != 6:
                logger.error(f"第{i+1}个轨迹点关节数量错误")
                return False
            
            for j, angle in enumerate(point):
                if j < len(joint_limits):
                    min_limit, max_limit = joint_limits[j]
                    if not (min_limit <= angle <= max_limit):
                        logger.error(f"第{i+1}个轨迹点第{j+1}个关节超出限位: {angle:.3f} not in [{min_limit:.3f}, {max_limit:.3f}]")
                        return False
        
        return True
    
    def clip_to_joint_limits(self, trajectory: List[List[float]], joint_limits: List[tuple]) -> List[List[float]]:
        """
        将关节轨迹裁剪到限位内
        
        Args:
            trajectory: 关节轨迹
            joint_limits: 关节限位
            
        Returns:
            List[List[float]]: 裁剪后的轨迹
        """
        if len(joint_limits) != 6:
            logger.error("关节限位数量错误")
            return trajectory
        
        clipped_trajectory = []
        violations = []
        
        for i, point in enumerate(trajectory):
            if len(point) != 6:
                logger.error(f"第{i+1}个轨迹点关节数量错误")
                continue
            
            clipped_point = []
            for j, angle in enumerate(point):
                if j < len(joint_limits):
                    min_limit, max_limit = joint_limits[j]
                    clipped_angle = max(min_limit, min(angle, max_limit))
                    clipped_point.append(clipped_angle)
                    
                    if clipped_angle != angle:
                        violations.append((i, j, angle, clipped_angle))
                else:
                    clipped_point.append(angle)
            
            clipped_trajectory.append(clipped_point)
        
        if violations:
            logger.warning(f"轨迹中有{len(violations)}个关节角度被裁剪到限位内")
            for i, j, original, clipped in violations[:5]:  # 只显示前5个
                logger.warning(f"点{i+1}关节{j+1}: {original:.3f} -> {clipped:.3f}")
        
        return clipped_trajectory