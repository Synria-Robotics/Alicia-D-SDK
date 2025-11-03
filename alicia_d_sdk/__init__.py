"""
Alicia-D SDK v6.0.0 - 与 RoboCore 桥接

架构层次：
- 用户层: SynriaRobotAPI (统一用户接口)
- 规划层: 使用 RoboCore 轨迹规划功能
- 控制层: MotionController (运动控制)
- 执行层: HardwareExecutor (硬件执行)
- 硬件层: ServoDriver (底层驱动)
- 运动学层: 使用 RoboCore 运动学功能 (FK/IK/Jacobian)

Bridge with RoboCore:
- robocore.kinematics: 提供 FK/IK/Jacobian 计算
- robocore.planning: 提供轨迹规划功能
- robocore.modeling: 提供 RobotModel
"""

from .api import SynriaRobotAPI
from .hardware import ServoDriver
from .execution import HardwareExecutor

# Import from RoboCore for kinematics and modeling
from robocore.modeling import RobotModel
from robocore.kinematics import forward_kinematics, inverse_kinematics, jacobian
from robocore.planning import (
    cubic_polynomial_trajectory,
    quintic_polynomial_trajectory,
    linear_joint_trajectory,
    linear_cartesian_trajectory,
    trapezoidal_velocity_profile
)

__version__ = "6.0.0"
__author__ = "Alicia-D Team"
__description__ = "Alicia-D机械臂SDK v6.0.0 - Bridged with RoboCore"

# Re-export RoboCore components for convenience
__all__ = [
    # Core API
    "SynriaRobotAPI",
    "create_robot",
    "create_session",
    
    # Hardware Layer
    "ServoDriver",
    
    
    # Execution Layer
    "HardwareExecutor",
    
    # RoboCore - Modeling
    "RobotModel",
    
    # RoboCore - Kinematics
    "forward_kinematics",
    "inverse_kinematics",
    "jacobian",
    
    # RoboCore - Planning
    "cubic_polynomial_trajectory",
    "quintic_polynomial_trajectory",
    "linear_joint_trajectory",
    "linear_cartesian_trajectory",
    "trapezoidal_velocity_profile",
]


def create_robot(
        port: str = "", 
        baudrate: int = 1000000, 
        robot_version: str = "v5_6",
        gripper_type: str = "50mm",
        firmware_version: None = None,
        debug_mode: bool = False,
        speed_deg_s: float = 20.0
    ) -> SynriaRobotAPI:
    """
    :param port: Serial port
    :param baudrate: Baud rate
    :param robot_version: Robot version (e.g., "v5_6", "v5_4")
    :param gripper_type: Gripper type (e.g., "50mm", "30mm")
    :param debug_mode: Debug mode
    :return: Robot API instance
    """
    # 创建硬件层
    servo_driver = ServoDriver(port=port, baudrate=baudrate, debug_mode=debug_mode, firmware_version=firmware_version)
    
    # 创建运动学层 (使用 RoboCore)
    try:
        from synriard import get_model_path
        urdf_path = get_model_path("Alicia_D", version=robot_version, variant=f"gripper_{gripper_type}")
        end_link = 'tool0'
        robot_model = RobotModel(str(urdf_path), end_link=end_link)
    except ImportError:
        print("Warning: synriard not found, using default URDF path")
        # Fallback to default path
        from pathlib import Path
        default_urdf = Path(__file__).parent.parent / "assets" / "robot" / "urdf" / f"Alicia-D_{robot_version}" / "alicia_duo_with_gripper.urdf"
        if default_urdf.exists():
            robot_model = RobotModel(str(default_urdf), end_link='tool0')
        else:
            raise FileNotFoundError(f"Cannot find URDF file for {robot_version}")
    
    # 创建用户层 (不再需要 ik_controller，直接使用 robocore.kinematics 函数)
    robot = SynriaRobotAPI(
        servo_driver=servo_driver,
        robot_model=robot_model, 
        firmware_version=firmware_version,
        speed_deg_s = speed_deg_s
    )
    
    return robot
