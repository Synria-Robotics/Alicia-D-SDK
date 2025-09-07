"""
FastAPI Main Application
Alicia-D Robot Control Backend using SDK v5.5.0
"""
import logging
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from models import (
    ConnectionRequest, ConnectionResponse, RobotState,
    MoveJRequest, MoveCartesianRequest, GripperControlRequest,
    TorqueControlRequest, OperationResponse, ErrorResponse
)
from robot_manager import robot_manager
from robot_service import robot_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("Starting Alicia-D Robot Control Backend v5.5.0")
    yield
    logger.info("Shutting down robot connection...")
    robot_manager.disconnect()

# Create FastAPI app
app = FastAPI(
    title="Alicia-D Robot Control API",
    description="FastAPI backend for controlling Alicia-D robotic arm using SDK v5.5.0",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc)
        ).dict()
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "robot_connected": robot_manager.is_ready()
    }

# Connection endpoints
@app.post("/api/robot/connect", response_model=ConnectionResponse)
async def connect_robot(request: ConnectionRequest):
    """Connect to the robot"""
    try:
        success = robot_manager.connect(
            port=request.port,
            baudrate=request.baudrate
        )
        
        return ConnectionResponse(
            success=success,
            message="Connected to robot successfully" if success else "Failed to connect to robot",
            is_connected=robot_manager.is_connected
        )
    except Exception as e:
        logger.error(f"Connection error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Connection failed: {str(e)}"
        )

@app.post("/api/robot/disconnect", response_model=ConnectionResponse)
async def disconnect_robot():
    """Disconnect from the robot"""
    try:
        robot_manager.disconnect()
        return ConnectionResponse(
            success=True,
            message="Disconnected from robot",
            is_connected=robot_manager.is_connected
        )
    except Exception as e:
        logger.error(f"Disconnection error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Disconnection failed: {str(e)}"
        )

@app.get("/api/robot/status", response_model=ConnectionResponse)
async def get_robot_status():
    """Get robot connection status"""
    return ConnectionResponse(
        success=True,
        message="Status retrieved",
        is_connected=robot_manager.is_connected
    )

# State endpoints
@app.get("/api/robot/state")
async def get_robot_state(format: str = "rad") -> RobotState:
    """Get current robot state"""
    if not robot_manager.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Robot not connected"
        )
    
    return robot_service.get_robot_state(output_format=format)

@app.get("/api/robot/joints")
async def get_joints(format: str = "rad"):
    """Get current joint angles"""
    if not robot_manager.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Robot not connected"
        )
    
    state = robot_service.get_robot_state(output_format=format)
    if format == "deg":
        return {"joints": state.joints_deg, "format": "degrees"}
    else:
        return {"joints": state.joints, "format": "radians"}

@app.get("/api/robot/pose")
async def get_pose():
    """Get current end effector pose"""
    if not robot_manager.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Robot not connected"
        )
    
    state = robot_service.get_robot_state()
    return {"pose": state.pose, "description": "[x, y, z, qx, qy, qz, qw]"}

@app.get("/api/robot/gripper")
async def get_gripper(format: str = "rad"):
    """Get current gripper angle"""
    if not robot_manager.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Robot not connected"
        )
    
    state = robot_service.get_robot_state(output_format=format)
    if format == "deg":
        return {"gripper": state.gripper_deg, "format": "degrees"}
    else:
        return {"gripper": state.gripper, "format": "radians"}

# Movement endpoints
@app.post("/api/robot/move/joints", response_model=OperationResponse)
async def move_joints(request: MoveJRequest):
    """Move robot to target joint positions"""
    if not robot_manager.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Robot not connected"
        )
    
    result = robot_service.move_joints(
        target_joints=request.target_joints,
        joint_format=request.joint_format,
        speed_factor=request.speed_factor,
        T_default=request.T_default,
        n_steps_ref=request.n_steps_ref,
        visualize=request.visualize
    )
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message
        )
    
    return result

@app.post("/api/robot/move/cartesian", response_model=OperationResponse)
async def move_cartesian(request: MoveCartesianRequest):
    """Move robot through Cartesian waypoints"""
    if not robot_manager.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Robot not connected"
        )
    
    result = robot_service.move_cartesian(
        waypoints=request.waypoints,
        planner_name=request.planner_name,
        move_time=request.move_time,
        visualize=request.visualize,
        show_ori=request.show_ori,
        reverse=request.reverse
    )
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message
        )
    
    return result

@app.post("/api/robot/move/home", response_model=OperationResponse)
async def move_home():
    """Move robot to home position"""
    if not robot_manager.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Robot not connected"
        )
    
    result = robot_service.move_home()
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message
        )
    
    return result

# Gripper control endpoint
@app.post("/api/robot/gripper", response_model=OperationResponse)
async def control_gripper(request: GripperControlRequest):
    """Control robot gripper"""
    if not robot_manager.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Robot not connected"
        )
    
    result = robot_service.control_gripper(
        command=request.command,
        angle_deg=request.angle_deg,
        angle_rad=request.angle_rad,
        wait_for_completion=request.wait_for_completion
    )
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message
        )
    
    return result

# Torque control endpoint
@app.post("/api/robot/torque", response_model=OperationResponse)
async def control_torque(request: TorqueControlRequest):
    """Control robot torque (teaching mode)"""
    if not robot_manager.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Robot not connected"
        )
    
    result = robot_service.control_torque(command=request.command)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message
        )
    
    return result

# Calibration endpoint
@app.post("/api/robot/calibrate", response_model=OperationResponse)
async def zero_calibration():
    """Perform zero calibration"""
    if not robot_manager.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Robot not connected"
        )
    
    result = robot_service.zero_calibration()
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message
        )
    
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)