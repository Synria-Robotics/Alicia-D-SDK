"""
Robot Control Service
Provides high-level robot control functions using Alicia-D SDK v5.5.0
"""
import logging
import time
from typing import List, Optional, Dict, Any
from robot_manager import robot_manager
from models import RobotState, OperationResponse

logger = logging.getLogger(__name__)

class RobotControlService:
    """High-level robot control service"""
    
    @staticmethod
    def get_robot_state(output_format: str = "rad") -> RobotState:
        """
        Get current robot state
        
        Args:
            output_format: "rad" or "deg" for angle units
            
        Returns:
            RobotState: Current state information
        """
        controller = robot_manager.get_controller()
        if not controller:
            return RobotState()
        
        try:
            joints_rad = controller.get_joints()
            pose = controller.get_pose()
            gripper_rad = controller.get_gripper()
            
            state = RobotState(
                joints=joints_rad,
                pose=pose,
                gripper=gripper_rad,
                timestamp=time.time()
            )
            
            # Convert to degrees if requested
            if output_format == "deg" and joints_rad:
                state.joints_deg = [round(j * 180.0 / 3.14159, 2) for j in joints_rad]
                if gripper_rad is not None:
                    state.gripper_deg = round(gripper_rad * 180.0 / 3.14159, 2)
            
            return state
            
        except Exception as e:
            logger.error(f"Failed to get robot state: {str(e)}")
            return RobotState()
    
    @staticmethod
    def move_joints(target_joints: List[float], joint_format: str = "rad", 
                   speed_factor: float = 1.0, T_default: float = 4.0,
                   n_steps_ref: int = 200, visualize: bool = False) -> OperationResponse:
        """
        Move robot to target joint positions
        
        Args:
            target_joints: Target joint angles
            joint_format: "rad" or "deg"
            speed_factor: Speed multiplier (0.1 to 2.0)
            T_default: Default movement time
            n_steps_ref: Interpolation steps
            visualize: Enable visualization
            
        Returns:
            OperationResponse: Operation result
        """
        controller = robot_manager.get_controller()
        if not controller:
            return OperationResponse(success=False, message="Robot not connected")
        
        try:
            start_time = time.time()
            
            controller.moveJ(
                target_joints=target_joints,
                joint_format=joint_format,
                speed_factor=speed_factor,
                T_default=T_default,
                n_steps_ref=n_steps_ref,
                visualize=visualize
            )
            
            execution_time = time.time() - start_time
            return OperationResponse(
                success=True,
                message=f"Joint movement completed successfully",
                execution_time=execution_time
            )
            
        except Exception as e:
            logger.error(f"Joint movement failed: {str(e)}")
            return OperationResponse(success=False, message=f"Joint movement failed: {str(e)}")
    
    @staticmethod
    def move_cartesian(waypoints: List[List[float]], planner_name: str = "cartesian",
                      move_time: float = 3.0, visualize: bool = False,
                      show_ori: bool = False, reverse: bool = False) -> OperationResponse:
        """
        Move robot through Cartesian waypoints
        
        Args:
            waypoints: List of pose waypoints [x,y,z,qx,qy,qz,qw] or with gripper
            planner_name: "cartesian" or "lqt"
            move_time: Total movement time
            visualize: Enable visualization
            show_ori: Show orientation in visualization
            reverse: Execute in reverse order
            
        Returns:
            OperationResponse: Operation result
        """
        controller = robot_manager.get_controller()
        if not controller:
            return OperationResponse(success=False, message="Robot not connected")
        
        try:
            start_time = time.time()
            
            controller.moveCartesian(
                waypoints=waypoints,
                planner_name=planner_name,
                move_time=move_time,
                visualize=visualize,
                show_ori=show_ori,
                reverse=reverse
            )
            
            execution_time = time.time() - start_time
            return OperationResponse(
                success=True,
                message=f"Cartesian movement completed successfully",
                execution_time=execution_time
            )
            
        except Exception as e:
            logger.error(f"Cartesian movement failed: {str(e)}")
            return OperationResponse(success=False, message=f"Cartesian movement failed: {str(e)}")
    
    @staticmethod
    def move_home() -> OperationResponse:
        """
        Move robot to home position
        
        Returns:
            OperationResponse: Operation result
        """
        controller = robot_manager.get_controller()
        if not controller:
            return OperationResponse(success=False, message="Robot not connected")
        
        try:
            start_time = time.time()
            controller.moveHome()
            execution_time = time.time() - start_time
            
            return OperationResponse(
                success=True,
                message="Robot moved to home position",
                execution_time=execution_time
            )
            
        except Exception as e:
            logger.error(f"Move home failed: {str(e)}")
            return OperationResponse(success=False, message=f"Move home failed: {str(e)}")
    
    @staticmethod
    def control_gripper(command: Optional[str] = None, angle_deg: Optional[float] = None,
                       angle_rad: Optional[float] = None, wait_for_completion: bool = True) -> OperationResponse:
        """
        Control robot gripper
        
        Args:
            command: "open" or "close"
            angle_deg: Specific angle in degrees (0-100)
            angle_rad: Specific angle in radians
            wait_for_completion: Wait for completion
            
        Returns:
            OperationResponse: Operation result
        """
        controller = robot_manager.get_controller()
        if not controller:
            return OperationResponse(success=False, message="Robot not connected")
        
        try:
            start_time = time.time()
            
            if command:
                controller.gripper_control(command=command)
                message = f"Gripper {command} command executed"
            elif angle_deg is not None:
                controller.gripper_control(angle_deg=angle_deg)
                message = f"Gripper set to {angle_deg} degrees"
            elif angle_rad is not None:
                # Convert radians to degrees for the SDK
                angle_deg_converted = angle_rad * 180.0 / 3.14159
                controller.gripper_control(angle_deg=angle_deg_converted)
                message = f"Gripper set to {angle_rad} radians ({angle_deg_converted:.1f} degrees)"
            else:
                return OperationResponse(success=False, message="No gripper command or angle specified")
            
            execution_time = time.time() - start_time
            return OperationResponse(
                success=True,
                message=message,
                execution_time=execution_time
            )
            
        except Exception as e:
            logger.error(f"Gripper control failed: {str(e)}")
            return OperationResponse(success=False, message=f"Gripper control failed: {str(e)}")
    
    @staticmethod
    def control_torque(command: str) -> OperationResponse:
        """
        Control robot torque (teaching mode)
        
        Args:
            command: "on" or "off"
            
        Returns:
            OperationResponse: Operation result
        """
        controller = robot_manager.get_controller()
        if not controller:
            return OperationResponse(success=False, message="Robot not connected")
        
        try:
            start_time = time.time()
            controller.torque_control(command=command)
            execution_time = time.time() - start_time
            
            return OperationResponse(
                success=True,
                message=f"Torque {command} completed",
                execution_time=execution_time
            )
            
        except Exception as e:
            logger.error(f"Torque control failed: {str(e)}")
            return OperationResponse(success=False, message=f"Torque control failed: {str(e)}")
    
    @staticmethod
    def zero_calibration() -> OperationResponse:
        """
        Perform zero calibration
        
        Returns:
            OperationResponse: Operation result
        """
        controller = robot_manager.get_controller()
        if not controller:
            return OperationResponse(success=False, message="Robot not connected")
        
        try:
            start_time = time.time()
            controller.zero_calibration()
            execution_time = time.time() - start_time
            
            return OperationResponse(
                success=True,
                message="Zero calibration completed",
                execution_time=execution_time
            )
            
        except Exception as e:
            logger.error(f"Zero calibration failed: {str(e)}")
            return OperationResponse(success=False, message=f"Zero calibration failed: {str(e)}")

# Global service instance
robot_service = RobotControlService()