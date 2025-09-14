"""
Alicia-D SDK v5.6.0

重构后的机械臂SDK，采用清晰的分层架构设计。

架构层次：
- 用户层: SynriaRobotAPI (统一用户接口)
- 规划层: TrajectoryPlanner (轨迹规划)
- 控制层: MotionController (运动控制)
- 执行层: HardwareExecutor (硬件执行)
- 硬件层: ServoDriver (底层驱动)
"""

from .api import SynriaRobotAPI
from .hardware import ServoDriver
from .control import MotionController, StateManager
from .execution import HardwareExecutor
from .planning import TrajectoryPlanner, OnlineInterpolator
from .kinematics import RobotModel, IKController

# 版本信息
__version__ = "5.6.0"
__author__ = "Alicia-D Team"
__description__ = "Alicia-D机械臂SDK - 重构版本"

# 主要导出
__all__ = [
    "SynriaRobotAPI",
    "ServoDriver", 
    "MotionController",
    "StateManager",
    "HardwareExecutor",
    "TrajectoryPlanner",
    "OnlineInterpolator",
    "RobotModel",
    "IKController",
    "create_robot",
    "create_session"
]

# 工厂函数
def create_robot(port: str = "", baudrate: int = 1000000, debug_mode: bool = False) -> SynriaRobotAPI:
    """
    创建机械臂实例（推荐使用）
    
    Args:
        port: 串口端口
        baudrate: 波特率
        debug_mode: 调试模式
        
    Returns:
        SynriaRobotAPI: 机械臂API实例
    """
    # 创建硬件层
    servo_driver = ServoDriver(port=port, baudrate=baudrate, debug_mode=debug_mode)
    
    # 创建运动学层
    robot_model = RobotModel()
    ik_controller = IKController(robot_model)
    
    # 创建用户层
    robot = SynriaRobotAPI(
        servo_driver=servo_driver,
        robot_model=robot_model,
        ik_controller=ik_controller
    )
    
    return robot

def create_session(port: str = "", baudrate: int = 1000000, debug_mode: bool = False) -> dict:
    """
    创建会话（兼容旧版本）
    
    Args:
        port: 串口端口
        baudrate: 波特率
        debug_mode: 调试模式
        
    Returns:
        dict: 包含各层组件的会话字典
    """
    # 创建硬件层
    servo_driver = ServoDriver(port=port, baudrate=baudrate, debug_mode=debug_mode)
    
    # 创建运动学层
    robot_model = RobotModel()
    ik_controller = IKController(robot_model)
    
    # 创建各层组件
    hardware_executor = HardwareExecutor(servo_driver)
    motion_controller = MotionController(
        servo_driver=servo_driver,
        robot_model=robot_model,
        ik_controller=ik_controller,
        hardware_executor=hardware_executor
    )
    state_manager = StateManager(servo_driver=servo_driver, robot_model=robot_model)
    trajectory_planner = TrajectoryPlanner(robot_model=robot_model, ik_controller=ik_controller)
    online_interpolator = OnlineInterpolator(servo_driver)
    
    # 创建用户层
    robot_api = SynriaRobotAPI(
        servo_driver=servo_driver,
        robot_model=robot_model,
        ik_controller=ik_controller
    )
    
    return {
        'robot_api': robot_api,
        'servo_driver': servo_driver,
        'robot_model': robot_model,
        'ik_controller': ik_controller,
        'hardware_executor': hardware_executor,
        'motion_controller': motion_controller,
        'state_manager': state_manager,
        'trajectory_planner': trajectory_planner,
        'online_interpolator': online_interpolator
    }