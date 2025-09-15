# kinematics/__init__.py
from .robot_model import AliciaFollower
from .robot_model import AliciaFollower as RobotModel
from .advanced_ik_solver import Advanced6DOFIKSolver
from .ik_controller import IKController

__all__ = [
    "AliciaFollower",
    "Advanced6DOFIKSolver",
    "IKController",
    "RobotModel"    
]
