"""
MuJoCo仿真管理器

负责MuJoCo仿真环境的初始化、管理和控制。
"""

import os
import numpy as np
import mujoco
import mujoco_viewer
from typing import Optional, List, Dict, Any
import threading
import time
import platform

from ..utils.logger import logger


class MuJoCoManager:
    """MuJoCo仿真管理器

    新增:
        end_effector_body_name: 可选指定末端执行器 body 名称；若未找到将使用候选列表自动回退。
    """
    
    def __init__(self, model_path: str = None, enable_viewer: bool = True, end_effector_body_name: Optional[str] = None):
        """
        初始化MuJoCo管理器
        
        Args:
            model_path: 模型文件路径
            enable_viewer: 是否启用可视化
        """
        self.model_path = model_path or self._get_default_model_path()
        self.enable_viewer = enable_viewer
        
        # MuJoCo对象
        self.model: Optional[mujoco.MjModel] = None
        self.data: Optional[mujoco.MjData] = None
        self.viewer: Optional[mujoco_viewer.MujocoViewer] = None
        
        # 仿真状态
        self.is_running = False
        self.is_paused = False
        self.simulation_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # 仿真参数
        self.timestep = 0.001  # 1ms时间步长
        self.max_speed = 10.0  # 最大仿真速度倍数
        
        # 关节 & 末端执行器信息
        self.joint_names = []
        self.joint_ids = []
        self.gripper_joint_id = None
        # 双指夹爪（slide joints）
        self.left_finger_joint_id = None
        self.right_finger_joint_id = None
        self.end_effector_body_name = end_effector_body_name  # 用户显式指定
        self._resolved_end_effector_body = None  # 实际解析结果
        
        logger.info("初始化MuJoCo管理器")
    
    def _get_default_model_path(self) -> str:
        """获取默认模型路径"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(current_dir, "models", "alicia_arm.xml")
    
    def load_model(self, model_path: str = None) -> bool:
        """
        加载MuJoCo模型
        
        Args:
            model_path: 模型文件路径
            
        Returns:
            bool: 是否加载成功
        """
        try:
            if model_path:
                self.model_path = model_path
            
            if not os.path.exists(self.model_path):
                logger.error(f"模型文件不存在: {self.model_path}")
                return False
            
            # 加载模型
            self.model = mujoco.MjModel.from_xml_path(self.model_path)
            self.data = mujoco.MjData(self.model)
            
            # 设置时间步长
            self.model.opt.timestep = self.timestep
            
            # 获取关节信息
            self._extract_joint_info()
            
            logger.info(f"成功加载模型: {self.model_path}")
            logger.info(f"关节数量: {len(self.joint_names)}")
            logger.info(f"关节名称: {self.joint_names}")
            
            return True
            
        except Exception as e:
            logger.error(f"加载模型失败: {e}")
            return False
    
    def _extract_joint_info(self):
        """提取关节信息"""
        if not self.model:
            return
        
        self.joint_names = []
        self.joint_ids = []
        
        for i in range(self.model.njnt):
            joint_name = mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_JOINT, i)
            if joint_name:
                self.joint_names.append(joint_name)
                self.joint_ids.append(i)
                
                # 查找夹爪关节
                if joint_name == "gripper":
                    self.gripper_joint_id = i
                elif joint_name == "left_finger":
                    self.left_finger_joint_id = i
                elif joint_name == "right_finger":
                    self.right_finger_joint_id = i
        # 解析末端执行器 body
        self._resolve_end_effector_body()

    def _resolve_end_effector_body(self):
        """解析末端执行器 body 名称，支持候选回退。

        优先级:
            1. 用户构造时显式传入的名称
            2. 内置候选列表: end_effector, tool0, Link6, tcp, gripper_base, Link7, Link8
            3. 最后回退: 具有最大深度的末端链路 (启发式: 名称最长或层级最深的 body)
        """
        if not self.model:
            return

        candidates = []
        if self.end_effector_body_name:
            candidates.append(self.end_effector_body_name)
        # 常见命名候选
        candidates.extend(["end_effector", "tool0", "Link6", "tcp", "gripper_base", "Link7", "Link8"])

        found = None
        for name in candidates:
            try:
                bid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, name)
                if bid != -1:
                    found = name
                    break
            except Exception:
                continue

        if not found:
            # 回退策略: 选择 id 最大的 body (通常是末端) 作为近似
            try:
                max_id = -1
                max_name = None
                # 遍历 body id
                for i in range(self.model.nbody):
                    name = mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_BODY, i)
                    if name and i > max_id:
                        max_id = i
                        max_name = name
                found = max_name
            except Exception:
                found = None

        self._resolved_end_effector_body = found
        if found:
            logger.info(f"末端执行器 body 解析为: {found}")
        else:
            logger.warning("未能解析末端执行器 body，后续位姿查询将返回 None")
    
    def start_viewer(self) -> bool:
        """
        启动可视化窗口
        
        Returns:
            bool: 是否启动成功
        """
        if not self.enable_viewer or not self.model:
            return False
        
        try:
            self.viewer = mujoco_viewer.MujocoViewer(self.model, self.data)
            logger.info("MuJoCo可视化窗口已启动")
            return True
        except Exception as e:
            logger.error(f"启动可视化窗口失败: {e}")
            return False
    
    def start_simulation(self) -> bool:
        """
        启动仿真
        
        Returns:
            bool: 是否启动成功
        """
        if not self.model or not self.data:
            logger.error("模型未加载")
            return False
        
        if self.is_running:
            logger.warning("仿真已在运行")
            return True
        
        try:
            self.is_running = True
            self.is_paused = False
            
            # 启动仿真线程
            self.simulation_thread = threading.Thread(target=self._simulation_loop, daemon=True)
            self.simulation_thread.start()
            
            logger.info("MuJoCo仿真已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动仿真失败: {e}")
            self.is_running = False
            return False
    
    def stop_simulation(self) -> bool:
        """
        停止仿真
        
        Returns:
            bool: 是否停止成功
        """
        if not self.is_running:
            logger.warning("仿真未运行")
            return True
        
        try:
            self.is_running = False
            
            if self.simulation_thread and self.simulation_thread.is_alive():
                self.simulation_thread.join(timeout=2.0)
            
            logger.info("MuJoCo仿真已停止")
            return True
            
        except Exception as e:
            logger.error(f"停止仿真失败: {e}")
            return False
    
    def pause_simulation(self):
        """暂停仿真"""
        self.is_paused = True
        logger.info("仿真已暂停")
    
    def resume_simulation(self):
        """恢复仿真"""
        self.is_paused = False
        logger.info("仿真已恢复")
    
    def reset_simulation(self):
        """重置仿真"""
        if self.data:
            mujoco.mj_resetData(self.model, self.data)
            logger.info("仿真已重置")
    
    def _simulation_loop(self):
        """仿真循环"""
        logger.info("仿真循环开始")
        
        while self.is_running:
            try:
                if not self.is_paused:
                    # 执行仿真步骤 (加锁避免与外部 set_joint / forward 并发导致不一致或内存错误)
                    with self._lock:
                        mujoco.mj_step(self.model, self.data)
                
                # 更新可视化 (兼容 is_alive 既可能是方法也可能是布尔属性)
                if self.viewer:
                    # macOS 上 GLFW/OpenGL 通常要求在主线程渲染，后台线程调用可能触发 segfault
                    if platform.system() == "Darwin" and threading.current_thread() is not threading.main_thread():
                        # 仅做最小运行保持，不调用 render，避免崩溃
                        # 可以未来通过事件队列在主线程调用 render
                        pass
                    else:
                        viewer_alive_attr = getattr(self.viewer, 'is_alive', None)
                        try:
                            if callable(viewer_alive_attr):
                                is_viewer_alive = viewer_alive_attr()
                            elif isinstance(viewer_alive_attr, bool):
                                is_viewer_alive = viewer_alive_attr
                            else:
                                is_viewer_alive = True
                        except Exception:
                            is_viewer_alive = False

                        if is_viewer_alive:
                            try:
                                self.viewer.render()
                            except Exception as render_e:
                                logger.error(f"可视化渲染异常: {render_e}")
                        else:
                            self.is_running = False
                            break
                
                # 控制仿真速度
                time.sleep(self.timestep / self.max_speed)
                
            except Exception as e:
                logger.error(f"仿真循环异常: {e}")
                break
        
        logger.info("仿真循环结束")
    
    def set_joint_angles(self, joint_angles: List[float]) -> bool:
        """
        设置关节角度
        
        Args:
            joint_angles: 关节角度列表 (6个关节)
            
        Returns:
            bool: 是否设置成功
        """
        if not self.model or not self.data:
            logger.error("模型未加载")
            return False
        
        if len(joint_angles) != 6:
            logger.error(f"关节角度数量错误: {len(joint_angles)}, 期望6个")
            return False
        
        try:
            with self._lock:
                # 设置关节位置
                for i, angle in enumerate(joint_angles):
                    if i < len(self.joint_ids):
                        joint_id = self.joint_ids[i]
                        self.data.qpos[joint_id] = angle
                
                # 前向运动学
                mujoco.mj_forward(self.model, self.data)
            
            return True
            
        except Exception as e:
            logger.error(f"设置关节角度失败: {e}")
            return False
    
    def get_joint_angles(self) -> Optional[List[float]]:
        """
        获取当前关节角度
        
        Returns:
            List[float]: 关节角度列表
        """
        if not self.model or not self.data:
            return None
        
        try:
            with self._lock:
                joint_angles = []
                for i in range(6):  # 6个关节
                    if i < len(self.joint_ids):
                        joint_id = self.joint_ids[i]
                        joint_angles.append(self.data.qpos[joint_id])
                
                return joint_angles
                
        except Exception as e:
            logger.error(f"获取关节角度失败: {e}")
            return None
    
    def set_gripper_angle(self, angle: float) -> bool:
        """
        设置夹爪角度
        
        Args:
            angle: 夹爪角度 (0-1.57弧度)
            
        Returns:
            bool: 是否设置成功
        """
        if not self.model or not self.data:
            logger.error("模型未加载")
            return False
        
        # 优先使用双指逻辑
        try:
            with self._lock:
                if self.left_finger_joint_id is not None and self.right_finger_joint_id is not None:
                    # angle 视为张开宽度 (0 ~ 0.05)；模型限制：left: [-0.025,0]  right: [0,0.025]
                    max_open = 0.05
                    width = max(0.0, min(max_open, angle))
                    left_pos = -width / 2.0
                    right_pos = width / 2.0
                    # 夹紧范围裁剪
                    left_pos = max(-0.025, min(0.0, left_pos))
                    right_pos = max(0.0, min(0.025, right_pos))
                    self.data.qpos[self.left_finger_joint_id] = left_pos
                    self.data.qpos[self.right_finger_joint_id] = right_pos
                    mujoco.mj_forward(self.model, self.data)
                    return True
                # 回退单关节模型
                if self.gripper_joint_id is not None:
                    self.data.qpos[self.gripper_joint_id] = angle
                    mujoco.mj_forward(self.model, self.data)
                    return True
                logger.error("夹爪关节未找到 (left/right_finger 或 gripper)")
                return False
        except Exception as e:
            logger.error(f"设置夹爪角度失败: {e}")
            return False
    
    def get_gripper_angle(self) -> Optional[float]:
        """
        获取当前夹爪角度
        
        Returns:
            float: 夹爪角度
        """
        if not self.model or not self.data:
            return None
        try:
            with self._lock:
                if self.left_finger_joint_id is not None and self.right_finger_joint_id is not None:
                    left_pos = self.data.qpos[self.left_finger_joint_id]
                    right_pos = self.data.qpos[self.right_finger_joint_id]
                    # 宽度 = 右 - 左（左为负，右为正）
                    return right_pos - left_pos
                if self.gripper_joint_id is not None:
                    return self.data.qpos[self.gripper_joint_id]
                return None
        except Exception as e:
            logger.error(f"获取夹爪角度失败: {e}")
            return None
    
    def get_end_effector_pose(self) -> Optional[List[float]]:
        """
        获取末端执行器位姿
        
        Returns:
            List[float]: [x, y, z, qx, qy, qz, qw]
        """
        if not self.model or not self.data:
            return None
        
        try:
            with self._lock:
                if not self._resolved_end_effector_body:
                    self._resolve_end_effector_body()
                if not self._resolved_end_effector_body:
                    logger.error("末端执行器未找到 (解析失败)")
                    return None

                end_effector_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, self._resolved_end_effector_body)
                if end_effector_id == -1:
                    logger.error(f"末端执行器未找到: {self._resolved_end_effector_body}")
                    return None

                pos = self.data.xpos[end_effector_id].copy()
                quat = self.data.xquat[end_effector_id].copy()
                pose = [pos[0], pos[1], pos[2], quat[1], quat[2], quat[3], quat[0]]
                return pose
        except Exception as e:
            logger.error(f"获取末端执行器位姿失败: {e}")
            return None
    
    def set_timestep(self, timestep: float):
        """
        设置仿真时间步长
        
        Args:
            timestep: 时间步长 (秒)
        """
        self.timestep = max(0.0001, timestep)
        if self.model:
            self.model.opt.timestep = self.timestep
        logger.info(f"时间步长设置为: {self.timestep}s")
    
    def set_max_speed(self, max_speed: float):
        """
        设置最大仿真速度
        
        Args:
            max_speed: 最大速度倍数
        """
        self.max_speed = max(0.1, max_speed)
        logger.info(f"最大仿真速度设置为: {self.max_speed}x")
    
    def is_simulation_running(self) -> bool:
        """检查仿真是否运行"""
        return self.is_running and not self.is_paused
    
    def close(self):
        """关闭仿真环境"""
        self.stop_simulation()
        
        if self.viewer:
            self.viewer.close()
            self.viewer = None
        
        self.model = None
        self.data = None
        
        logger.info("MuJoCo环境已关闭")

    # ==================== 主线程渲染辅助 ====================
    def render_if_possible(self):
        """在主线程调用的安全渲染接口（用于 macOS 避免后台线程渲染问题）。

        使用场景:
            - 后台线程循环被 macOS 绕过渲染时，用户层可在控制循环里周期性调用以刷新画面。
        """
        if not self.viewer:
            return
        if platform.system() == "Darwin" and threading.current_thread() is not threading.main_thread():
            # 必须在主线程调用
            return
        viewer_alive_attr = getattr(self.viewer, 'is_alive', None)
        is_viewer_alive = True
        try:
            if callable(viewer_alive_attr):
                is_viewer_alive = viewer_alive_attr()
            elif isinstance(viewer_alive_attr, bool):
                is_viewer_alive = viewer_alive_attr
        except Exception:
            is_viewer_alive = False
        if not is_viewer_alive:
            return
        try:
            self.viewer.render()
        except Exception as e:
            logger.error(f"主线程渲染异常: {e}")
    
    def __del__(self):
        """析构函数"""
        try:
            self.close()
        except Exception as e:
            logger.error(f"MuJoCo管理器析构异常: {e}")