"""
HardwareExecutor - 硬件执行器

职责：
- 执行硬件命令
- 管理执行状态
- 提供执行监控
- 处理执行错误
"""

import time
import threading
from typing import List, Optional, Callable, Dict, Any
import numpy as np
from scipy.spatial.transform import Rotation as R

from ..hardware import ServoDriver, JointState
from ..utils.logger import logger


class HardwareExecutor:
    """硬件执行器 - 负责执行硬件命令"""
    
    def __init__(self, servo_driver: ServoDriver):
        """
        初始化硬件执行器
        
        Args:
            servo_driver: 舵机驱动实例
        """
        self.servo_driver = servo_driver
        self._lock = threading.Lock()
        
        # 执行状态
        self._is_executing = False
        self._current_trajectory = None
        self._execution_thread = None
        self._stop_execution = threading.Event()
        
        # 执行参数
        self.default_delay = 0.02  # 默认执行延迟
        self.max_delay = 0.1
        self.min_delay = 0.001
        
        # 回调函数
        self._progress_callback: Optional[Callable] = None
        self._completion_callback: Optional[Callable] = None
        self._error_callback: Optional[Callable] = None
        
        logger.info("初始化硬件执行器")
    
    # ==================== 轨迹执行接口 ====================
    
    def execute_trajectory(self, 
                          joint_trajectory: List[List[float]], 
                          delay: Optional[float] = None,
                          gripper_trajectory: Optional[List[float]] = None,
                          progress_callback: Optional[Callable] = None,
                          completion_callback: Optional[Callable] = None,
                          error_callback: Optional[Callable] = None) -> bool:
        """
        执行关节轨迹
        
        Args:
            joint_trajectory: 关节轨迹点列表
            delay: 执行延迟，None则使用默认值
            gripper_trajectory: 夹爪轨迹，可选
            progress_callback: 进度回调函数
            completion_callback: 完成回调函数
            error_callback: 错误回调函数
            
        Returns:
            bool: 是否成功开始执行
        """
        if self._is_executing:
            logger.warning("执行器正在执行中，无法开始新任务")
            return False
        
        if not joint_trajectory:
            logger.error("轨迹为空，无法执行")
            return False
        
        # 设置回调函数
        self._progress_callback = progress_callback
        self._completion_callback = completion_callback
        self._error_callback = error_callback
        
        # 设置执行参数
        self._current_delay = delay if delay is not None else self.default_delay
        self._current_delay = max(self.min_delay, min(self._current_delay, self.max_delay))
        
        # 开始执行
        self._is_executing = True
        self._stop_execution.clear()
        self._current_trajectory = joint_trajectory
        
        # 启动执行线程
        self._execution_thread = threading.Thread(
            target=self._execute_trajectory_loop,
            args=(joint_trajectory, gripper_trajectory),
            daemon=True
        )
        self._execution_thread.start()
        
        logger.info(f"开始执行轨迹，共{len(joint_trajectory)}个点，延迟{self._current_delay:.3f}s")
        return True
    
    def execute_single_point(self, 
                            joint_angles: List[float], 
                            gripper_angle: Optional[float] = None) -> bool:
        """
        执行单个关节点
        
        Args:
            joint_angles: 关节角度
            gripper_angle: 夹爪角度，可选
            
        Returns:
            bool: 是否成功执行
        """
        try:
            with self._lock:
                success = self.servo_driver.set_joint_angles(joint_angles)
                if success and gripper_angle is not None:
                    success = self.servo_driver.set_gripper(gripper_angle)
            return success
        except Exception as e:
            logger.error(f"执行单点失败: {e}")
            return False
    
    def stop_execution(self) -> bool:
        """
        停止当前执行
        
        Returns:
            bool: 是否成功停止
        """
        if not self._is_executing:
            logger.warning("没有正在执行的任务")
            return False
        
        self._stop_execution.set()
        
        if self._execution_thread and self._execution_thread.is_alive():
            self._execution_thread.join(timeout=2.0)
        
        self._is_executing = False
        self._current_trajectory = None
        
        logger.info("执行已停止")
        return True
    
    # ==================== 状态查询接口 ====================
    
    def is_executing(self) -> bool:
        """是否正在执行"""
        return self._is_executing
    
    def get_execution_progress(self) -> Dict[str, Any]:
        """获取执行进度"""
        if not self._is_executing or not self._current_trajectory:
            return {"progress": 0.0, "current_point": 0, "total_points": 0}
        
        # 这里需要根据实际执行情况计算进度
        # 简化实现，实际应该跟踪当前执行的点
        return {
            "progress": 0.0,  # 0.0-1.0
            "current_point": 0,
            "total_points": len(self._current_trajectory)
        }
    
    def get_current_state(self) -> Optional[JointState]:
        """获取当前状态"""
        return self.servo_driver.get_joint_state()
    
    # ==================== 配置接口 ====================
    
    def set_default_delay(self, delay: float):
        """设置默认执行延迟"""
        self.default_delay = max(self.min_delay, min(delay, self.max_delay))
        logger.info(f"设置默认执行延迟: {self.default_delay:.3f}s")
    
    def set_delay_limits(self, min_delay: float, max_delay: float):
        """设置延迟限制"""
        self.min_delay = max(0.001, min_delay)
        self.max_delay = max(self.min_delay, max_delay)
        logger.info(f"设置延迟限制: {self.min_delay:.3f}s - {self.max_delay:.3f}s")
    
    # ==================== 内部方法 ====================
    
    def _execute_trajectory_loop(self, 
                                joint_trajectory: List[List[float]], 
                                gripper_trajectory: Optional[List[float]] = None):
        """轨迹执行循环"""
        try:
            total_points = len(joint_trajectory)
            
            for i, joint_point in enumerate(joint_trajectory):
                # 检查停止信号
                if self._stop_execution.is_set():
                    logger.info("收到停止信号，终止执行")
                    break
                
                # 执行关节点
                success = self.servo_driver.set_joint_angles(joint_point)
                if not success:
                    logger.error(f"执行第{i+1}个点失败")
                    self._handle_execution_error(f"执行第{i+1}个点失败")
                    break
                
                # 执行夹爪点
                if gripper_trajectory and i < len(gripper_trajectory):
                    gripper_angle = gripper_trajectory[i]
                    if gripper_angle is not None:
                        self.servo_driver.set_gripper(gripper_angle)
                
                # 调用进度回调
                if self._progress_callback:
                    try:
                        self._progress_callback(i + 1, total_points, joint_point)
                    except Exception as e:
                        logger.error(f"进度回调函数执行失败: {e}")
                
                # 延迟
                time.sleep(self._current_delay)
            
            # 执行完成
            self._is_executing = False
            self._current_trajectory = None
            
            # 调用完成回调
            if self._completion_callback:
                try:
                    self._completion_callback(total_points)
                except Exception as e:
                    logger.error(f"完成回调函数执行失败: {e}")
            
            logger.info("轨迹执行完成")
            
        except Exception as e:
            logger.error(f"轨迹执行异常: {e}")
            self._handle_execution_error(str(e))
        finally:
            self._is_executing = False
            self._current_trajectory = None
    
    def _handle_execution_error(self, error_message: str):
        """处理执行错误"""
        self._is_executing = False
        self._current_trajectory = None
        
        if self._error_callback:
            try:
                self._error_callback(error_message)
            except Exception as e:
                logger.error(f"错误回调函数执行失败: {e}")
        
        logger.error(f"执行错误: {error_message}")
    
    # ==================== 工具方法 ====================
    
    def calculate_trajectory_error(self, 
                                  target_pose: List[float], 
                                  robot_model) -> Dict[str, float]:
        """
        计算轨迹执行误差
        
        Args:
            target_pose: 目标位姿 [x, y, z, qx, qy, qz, qw]
            robot_model: 机器人模型，用于正运动学
            
        Returns:
            Dict: 包含位置误差和姿态误差
        """
        try:
            # 获取当前关节角度
            current_joints = self.servo_driver.get_joint_angles()
            if not current_joints:
                return {"position_error": float('inf'), "orientation_error": float('inf')}
            
            # 计算当前位姿
            current_pos, current_quat = robot_model.forward_kinematics(current_joints)
            
            # 计算位置误差
            target_pos = np.array(target_pose[:3])
            current_pos = np.array(current_pos)
            position_error = np.linalg.norm(target_pos - current_pos)
            
            # 计算姿态误差
            target_rot = R.from_quat(target_pose[3:])
            current_rot = R.from_quat(current_quat)
            rot_diff = target_rot.inv() * current_rot
            orientation_error = np.degrees(rot_diff.magnitude())
            
            return {
                "position_error": float(position_error),
                "orientation_error": float(orientation_error)
            }
            
        except Exception as e:
            logger.error(f"计算轨迹误差失败: {e}")
            return {"position_error": float('inf'), "orientation_error": float('inf')}
    
    def __del__(self):
        """析构函数"""
        try:
            if self._is_executing:
                self.stop_execution()
        except Exception as e:
            logger.error(f"硬件执行器析构异常: {e}")