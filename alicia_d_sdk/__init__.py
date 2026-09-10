# Copyright (c) 2025 Synria Robotics Co., Ltd.
# Licensed under the MIT License.
#
# Author: Synria Robotics Team
# Website: https://synriarobotics.ai

"""
Alicia-D SDK v6.1.8 - Bridged with RoboCore

Architecture Layers:
- User Layer: SynriaRobotAPI (unified user interface)
- Execution Layer: TrajectoryExecutor, DragTeaching (trajectory execution)
- Hardware Layer: ServoDriver, SerialComm, DataParser (low-level hardware drivers)
- Kinematics Layer: RoboCore kinematics functions (FK/IK/Jacobian)
- Planning Layer: RoboCore trajectory planning functions

RoboCore Integration:
- Default compute backend: RoboCore cpp backend when available
- robocore.kinematics: Provides FK/IK/Jacobian calculations
- robocore.planning: Provides trajectory planning functionality
- robocore.modeling: Provides RobotModel for robot representation
"""

from alicia_d_sdk.api import SynriaRobotAPI
from alicia_d_sdk.hardware import ServoDriver
from alicia_d_sdk.api.synria_robot_api import BackendName

# Import from RoboCore for kinematics and modeling
from robocore.modeling import RobotModel
from robocore.kinematics import forward_kinematics, inverse_kinematics, jacobian
from synriard import get_model_path
from pathlib import Path
from typing import Optional


__version__ = "6.1.8"
__author__ = "Synria Robotics"
__description__ = "Alicia-D Robot Arm SDK v6.1.8 - Bridged with RoboCore"

_BUNDLED_MODEL_VARIANT = "alicia_duo"
_BUNDLED_MODEL_PATH = (
    Path(__file__).parent
    / "models"
    / "Alicia_duo"
    / "urdf"
    / "Alicia-duo.urdf"
)


# Re-export RoboCore components for convenience
__all__ = [
    # Core API
    "SynriaRobotAPI",
    "create_robot",

    # Hardware Layer
    "ServoDriver",

    # RoboCore - Modeling
    "RobotModel",

    # RoboCore - Kinematics
    "forward_kinematics",
    "inverse_kinematics",
    "jacobian",

]


def create_robot(
    port: str = "",
    version: str = "v5_6",
    variant: str = None,
    model_format: str = "urdf",
    debug_mode: bool = False,
    auto_connect: bool = True,
    base_link: str = "base_link",
    end_link: str = "tool0",
    backend: Optional[BackendName] = None,
    device: str = "cpu",
    model_path: str = None,
    gripper_type: str = None,
) -> SynriaRobotAPI:
    """
    Create robot instance.

    :param port: Serial port
    :param version: Version name, e.g., "v5_6", "v7_0", etc.
    :param variant: Model variant. None or "alicia_duo" selects the bundled force-control leader model.
        Other values such as "gripper_50mm" and "leader" use the legacy synriard model package.
    :param model_format: Model format, 'urdf' or 'mjcf', default is 'urdf'
    :param debug_mode: Debug mode
    :param base_link: Base link name in the robot model (default 'base_link')
    :param end_link: End link name in the robot model (default 'tool0')
    :param backend: Computation backend, 'cpp', 'numpy', or 'torch' (default: None, uses 'cpp')
    :param device: Device for torch backend, 'cpu' or 'cuda' (default: 'cpu', ignored for 'cpp' and 'numpy')
    :param model_path: Model path, if None, use default model path
    :param gripper_type: Deprecated compatibility option. An explicit value such as
        "50mm" selects the matching legacy gripper model when variant is not provided.
    :return: SynriaRobotAPI instance
    """
    servo_driver = ServoDriver(port=port, debug_mode=debug_mode)

    if model_path is None:
        selected_variant = variant
        if selected_variant is None and gripper_type is not None:
            selected_variant = f"gripper_{gripper_type}"

        if selected_variant is None or selected_variant == _BUNDLED_MODEL_VARIANT:
            if model_format != "urdf":
                raise ValueError(
                    "The bundled Alicia-duo model is currently available only in URDF format"
                )
            model_path = _BUNDLED_MODEL_PATH
        else:
            model_path = get_model_path(
                "Alicia_D",
                version=version,
                variant=selected_variant,
                model_format=model_format
            )

    model_path = Path(model_path)
    if not model_path.is_file():
        raise FileNotFoundError(f"Robot model file not found: {model_path}")
    robot_model = RobotModel(str(model_path), base_link=base_link, end_link=end_link)

    robot = SynriaRobotAPI(
        servo_driver=servo_driver,
        robot_model=robot_model,
        auto_connect=auto_connect,
        backend=backend,
        device=device
    )

    return robot
