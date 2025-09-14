"""
CartesianSpacePlanner - 笛卡尔空间规划器

职责：
- 笛卡尔空间轨迹规划
- 位置和姿态插值
- 路径点处理
- 轨迹平滑
"""

from typing import List, Optional, Tuple
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp

from ..utils.logger import logger


class CartesianSpacePlanner:
    """笛卡尔空间规划器 - 负责笛卡尔空间轨迹规划"""
    
    def __init__(self):
        """初始化笛卡尔空间规划器"""
        logger.info("初始化笛卡尔空间规划器")
    
    def plan_waypoints(self,
                      waypoints: List[List[float]],
                      steps_per_segment: Optional[int] = None,
                      speed_factor: float = 1.0,
                      interpolation_type: str = "linear") -> List[List[float]]:
        """
        规划多点笛卡尔轨迹
        
        Args:
            waypoints: 位姿路径点列表 [x, y, z, qx, qy, qz, qw]
            steps_per_segment: 每段插值步数
            speed_factor: 速度因子
            interpolation_type: 插值类型 ("linear", "cubic")
            
        Returns:
            List[List[float]]: 位姿轨迹
        """
        if not waypoints or len(waypoints) < 2:
            logger.error("路径点数量不足")
            return []
        
        for i, wp in enumerate(waypoints):
            if len(wp) != 7:
                logger.error(f"第{i+1}个路径点位姿维度错误")
                return []
        
        logger.info(f"规划笛卡尔多点轨迹: {len(waypoints)}个路径点")
        
        full_trajectory = []
        
        for i in range(len(waypoints) - 1):
            start_pose = waypoints[i]
            target_pose = waypoints[i + 1]
            
            # 计算当前段步数
            if steps_per_segment is None:
                segment_steps = self._estimate_steps_between_poses(start_pose, target_pose, speed_factor)
            else:
                segment_steps = steps_per_segment
            
            # 规划当前段
            segment_trajectory = self.plan_single_segment(
                start_pose=start_pose,
                target_pose=target_pose,
                steps=segment_steps,
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
        
        logger.info(f"笛卡尔多点轨迹规划完成: {len(full_trajectory)}个点")
        return full_trajectory
    
    def plan_single_segment(self,
                           start_pose: List[float],
                           target_pose: List[float],
                           steps: int,
                           interpolation_type: str = "linear") -> List[List[float]]:
        """
        规划单段笛卡尔轨迹
        
        Args:
            start_pose: 起始位姿 [x, y, z, qx, qy, qz, qw]
            target_pose: 目标位姿 [x, y, z, qx, qy, qz, qw]
            steps: 插值步数
            interpolation_type: 插值类型
            
        Returns:
            List[List[float]]: 位姿轨迹
        """
        if len(start_pose) != 7 or len(target_pose) != 7:
            logger.error("位姿维度错误")
            return []
        
        if steps < 1:
            logger.error("插值步数必须大于0")
            return []
        
        if interpolation_type == "linear":
            return self._linear_pose_interpolation(start_pose, target_pose, steps)
        elif interpolation_type == "cubic":
            return self._cubic_pose_interpolation(start_pose, target_pose, steps)
        else:
            logger.warning(f"不支持的插值类型: {interpolation_type}，使用线性插值")
            return self._linear_pose_interpolation(start_pose, target_pose, steps)
    
    def _linear_pose_interpolation(self, start_pose: List[float], target_pose: List[float], steps: int) -> List[List[float]]:
        """线性位姿插值"""
        start_pos = np.array(start_pose[:3])
        start_quat = np.array(start_pose[3:])
        target_pos = np.array(target_pose[:3])
        target_quat = np.array(target_pose[3:])
        
        # 确保四元数在同一个半球
        if np.dot(start_quat, target_quat) < 0.0:
            target_quat = -target_quat
        
        trajectory = []
        
        for i in range(steps):
            t = i / (steps - 1) if steps > 1 else 1.0
            
            # 位置线性插值
            pos = (1 - t) * start_pos + t * target_pos
            
            # 姿态球面线性插值
            key_rots = R.from_quat([start_quat, target_quat])
            slerp = Slerp([0, 1], key_rots)
            quat = slerp([t])[0].as_quat()
            
            pose = np.concatenate([pos, quat]).tolist()
            trajectory.append(pose)
        
        return trajectory
    
    def _cubic_pose_interpolation(self, start_pose: List[float], target_pose: List[float], steps: int) -> List[List[float]]:
        """三次位姿插值"""
        start_pos = np.array(start_pose[:3])
        start_quat = np.array(start_pose[3:])
        target_pos = np.array(target_pose[:3])
        target_quat = np.array(target_pose[3:])
        
        # 确保四元数在同一个半球
        if np.dot(start_quat, target_quat) < 0.0:
            target_quat = -target_quat
        
        trajectory = []
        
        for i in range(steps):
            t = i / (steps - 1) if steps > 1 else 1.0
            ratio = self._ease_in_out_cubic(t)
            
            # 位置三次插值
            pos = (1 - ratio) * start_pos + ratio * target_pos
            
            # 姿态球面线性插值
            key_rots = R.from_quat([start_quat, target_quat])
            slerp = Slerp([0, 1], key_rots)
            quat = slerp([ratio])[0].as_quat()
            
            pose = np.concatenate([pos, quat]).tolist()
            trajectory.append(pose)
        
        return trajectory
    
    def _estimate_steps_between_poses(self, 
                                     pose1: List[float], 
                                     pose2: List[float], 
                                     speed_factor: float = 1.0) -> int:
        """
        根据两个位姿之间的差异估算所需的插值步数
        
        Args:
            pose1: 起始位姿
            pose2: 目标位姿
            speed_factor: 速度因子
            
        Returns:
            int: 估算的步数
        """
        pos1 = np.array(pose1[:3])
        quat1 = np.array(pose1[3:])
        pos2 = np.array(pose2[:3])
        quat2 = np.array(pose2[3:])
        
        # 位置差（欧几里得距离）
        pos_diff = np.linalg.norm(pos1 - pos2)
        
        # 姿态差（旋转角度）
        q1 = R.from_quat(quat1)
        q2 = R.from_quat(quat2)
        angle_diff = q1.inv() * q2
        ori_diff_deg = np.degrees(angle_diff.magnitude())
        
        # 插值步数比例
        step_pos = pos_diff * 100  # 每 1m 差异对应 100 步
        step_ori = ori_diff_deg    # 每 1 度对应 1 步
        
        base_steps = 50
        steps = int((base_steps + step_pos + step_ori) * speed_factor)
        
        return max(5, min(steps, 200))  # 限制步数在范围内
    
    @staticmethod
    def _ease_in_out_cubic(t: float) -> float:
        """三次缓动函数"""
        return 4 * t**3 if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2
    
    def plan_circular_arc(self,
                         center: List[float],
                         radius: float,
                         start_angle: float,
                         end_angle: float,
                         normal_vector: List[float] = [0, 0, 1],
                         steps: int = 50) -> List[List[float]]:
        """
        规划圆形弧轨迹
        
        Args:
            center: 圆心位置 [x, y, z]
            radius: 半径
            start_angle: 起始角度 (弧度)
            end_angle: 结束角度 (弧度)
            normal_vector: 法向量 [x, y, z]
            steps: 插值步数
            
        Returns:
            List[List[float]]: 位姿轨迹（只有位置，姿态为默认）
        """
        if len(center) != 3:
            logger.error("圆心位置维度错误")
            return []
        
        if len(normal_vector) != 3:
            logger.error("法向量维度错误")
            return []
        
        center = np.array(center)
        normal = np.array(normal_vector)
        normal = normal / np.linalg.norm(normal)  # 归一化
        
        # 创建两个正交向量
        if abs(normal[2]) < 0.9:
            v1 = np.cross(normal, [0, 0, 1])
        else:
            v1 = np.cross(normal, [1, 0, 0])
        v1 = v1 / np.linalg.norm(v1)
        v2 = np.cross(normal, v1)
        
        trajectory = []
        
        for i in range(steps):
            t = i / (steps - 1) if steps > 1 else 1.0
            angle = start_angle + (end_angle - start_angle) * t
            
            # 计算圆弧上的点
            point = center + radius * (v1 * np.cos(angle) + v2 * np.sin(angle))
            
            # 默认姿态（可以根据需要调整）
            quat = [0, 0, 0, 1]  # 单位四元数
            
            pose = np.concatenate([point, quat]).tolist()
            trajectory.append(pose)
        
        logger.info(f"圆形弧轨迹规划完成: {steps}个点")
        return trajectory
    
    def plan_straight_line(self,
                          start_pose: List[float],
                          end_pose: List[float],
                          steps: int) -> List[List[float]]:
        """
        规划直线轨迹
        
        Args:
            start_pose: 起始位姿
            end_pose: 结束位姿
            steps: 插值步数
            
        Returns:
            List[List[float]]: 位姿轨迹
        """
        return self.plan_single_segment(start_pose, end_pose, steps, "linear")
    
    def smooth_trajectory(self, 
                         trajectory: List[List[float]], 
                         window_size: int = 5) -> List[List[float]]:
        """
        平滑轨迹（移动平均）
        
        Args:
            trajectory: 原始轨迹
            window_size: 窗口大小
            
        Returns:
            List[List[float]]: 平滑后的轨迹
        """
        if len(trajectory) < window_size:
            logger.warning("轨迹长度小于窗口大小，无法平滑")
            return trajectory
        
        smoothed = []
        
        for i in range(len(trajectory)):
            # 计算窗口范围
            start_idx = max(0, i - window_size // 2)
            end_idx = min(len(trajectory), i + window_size // 2 + 1)
            
            # 提取窗口内的位姿
            window_poses = trajectory[start_idx:end_idx]
            
            # 分别平滑位置和姿态
            positions = [pose[:3] for pose in window_poses]
            quaternions = [pose[3:] for pose in window_poses]
            
            # 位置平均
            avg_pos = np.mean(positions, axis=0)
            
            # 姿态平均（使用四元数平均）
            avg_quat = self._average_quaternions(quaternions)
            
            smoothed_pose = np.concatenate([avg_pos, avg_quat]).tolist()
            smoothed.append(smoothed_pose)
        
        logger.info(f"轨迹平滑完成: {len(trajectory)}个点")
        return smoothed
    
    def _average_quaternions(self, quaternions: List[List[float]]) -> List[float]:
        """计算四元数平均"""
        if not quaternions:
            return [0, 0, 0, 1]
        
        # 转换为旋转矩阵
        rotations = [R.from_quat(q) for q in quaternions]
        
        # 计算平均旋转
        avg_rotation = R.mean(rotations)
        
        return avg_rotation.as_quat().tolist()
    
    def check_cartesian_limits(self, 
                              trajectory: List[List[float]], 
                              cartesian_limits: dict) -> bool:
        """
        检查笛卡尔轨迹是否在限位内
        
        Args:
            trajectory: 位姿轨迹
            cartesian_limits: 笛卡尔限位 {"x": (min, max), "y": (min, max), "z": (min, max)}
            
        Returns:
            bool: 是否在限位内
        """
        for i, pose in enumerate(trajectory):
            if len(pose) != 7:
                logger.error(f"第{i+1}个轨迹点位姿维度错误")
                return False
            
            x, y, z = pose[:3]
            
            if "x" in cartesian_limits:
                min_x, max_x = cartesian_limits["x"]
                if not (min_x <= x <= max_x):
                    logger.error(f"第{i+1}个轨迹点X坐标超出限位: {x:.3f} not in [{min_x:.3f}, {max_x:.3f}]")
                    return False
            
            if "y" in cartesian_limits:
                min_y, max_y = cartesian_limits["y"]
                if not (min_y <= y <= max_y):
                    logger.error(f"第{i+1}个轨迹点Y坐标超出限位: {y:.3f} not in [{min_y:.3f}, {max_y:.3f}]")
                    return False
            
            if "z" in cartesian_limits:
                min_z, max_z = cartesian_limits["z"]
                if not (min_z <= z <= max_z):
                    logger.error(f"第{i+1}个轨迹点Z坐标超出限位: {z:.3f} not in [{min_z:.3f}, {max_z:.3f}]")
                    return False
        
        return True