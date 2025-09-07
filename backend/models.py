"""
Pydantic models for API request/response validation
"""
from typing import List, Optional, Union
from pydantic import BaseModel, Field

class ConnectionRequest(BaseModel):
    """Request model for robot connection"""
    port: str = Field(default="", description="Serial port (empty for auto-detect)")
    baudrate: int = Field(default=1000000, description="Communication baudrate")

class ConnectionResponse(BaseModel):
    """Response model for connection status"""
    success: bool
    message: str
    is_connected: bool

class RobotState(BaseModel):
    """Robot state information"""
    joints: Optional[List[float]] = Field(None, description="Joint angles in radians")
    joints_deg: Optional[List[float]] = Field(None, description="Joint angles in degrees")
    pose: Optional[List[float]] = Field(None, description="End effector pose [x,y,z,qx,qy,qz,qw]")
    gripper: Optional[float] = Field(None, description="Gripper angle in radians")
    gripper_deg: Optional[float] = Field(None, description="Gripper angle in degrees")
    timestamp: Optional[float] = Field(None, description="Timestamp of the state")

class MoveJRequest(BaseModel):
    """Request model for joint movement"""
    target_joints: List[float] = Field(..., description="Target joint angles")
    joint_format: str = Field(default="rad", description="Joint angle format: 'rad' or 'deg'")
    speed_factor: float = Field(default=1.0, description="Speed factor (0.1 to 2.0)")
    T_default: float = Field(default=4.0, description="Default move time in seconds")
    n_steps_ref: int = Field(default=200, description="Reference interpolation steps")
    visualize: bool = Field(default=False, description="Enable trajectory visualization")

class MoveCartesianRequest(BaseModel):
    """Request model for Cartesian movement"""
    waypoints: List[List[float]] = Field(..., description="List of waypoints [x,y,z,qx,qy,qz,qw] or with gripper [x,y,z,qx,qy,qz,qw,gripper]")
    planner_name: str = Field(default="cartesian", description="Planner type: 'cartesian' or 'lqt'")
    move_time: float = Field(default=3.0, description="Total movement time in seconds")
    visualize: bool = Field(default=False, description="Enable trajectory visualization")
    show_ori: bool = Field(default=False, description="Show orientation in visualization")
    reverse: bool = Field(default=False, description="Execute trajectory in reverse order")

class GripperControlRequest(BaseModel):
    """Request model for gripper control"""
    command: Optional[str] = Field(None, description="Gripper command: 'open' or 'close'")
    angle_deg: Optional[float] = Field(None, description="Specific gripper angle in degrees (0-100)")
    angle_rad: Optional[float] = Field(None, description="Specific gripper angle in radians")
    wait_for_completion: bool = Field(default=True, description="Wait for gripper to reach target")

class TorqueControlRequest(BaseModel):
    """Request model for torque control"""
    command: str = Field(..., description="Torque command: 'on' or 'off'")

class OperationResponse(BaseModel):
    """Generic response model for operations"""
    success: bool
    message: str
    execution_time: Optional[float] = None

class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    error: str
    detail: Optional[str] = None