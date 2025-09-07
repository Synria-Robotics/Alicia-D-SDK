"""
Robot Connection Manager for Alicia-D SDK v5.5.0
Handles robot session creation and connection management
"""
import logging
from typing import Optional
from contextlib import asynccontextmanager
from alicia_d_sdk.controller import create_session, SynriaRobotAPI
from alicia_d_sdk.controller.motion_session import MotionSession

logger = logging.getLogger(__name__)

class RobotConnectionManager:
    """Manages robot connection and session"""
    
    def __init__(self):
        self.session: Optional[MotionSession] = None
        self.controller: Optional[SynriaRobotAPI] = None
        self.is_connected: bool = False
        
    def connect(self, port: str = "", baudrate: int = 1000000) -> bool:
        """
        Connect to the robot
        
        Args:
            port: Serial port (empty string for auto-detect)
            baudrate: Communication baudrate (default: 1000000 for v5.4.19+)
            
        Returns:
            bool: True if connection successful
        """
        try:
            if self.is_connected:
                logger.warning("Robot is already connected")
                return True
                
            logger.info(f"Connecting to robot on port '{port}' with baudrate {baudrate}")
            self.session = create_session(port=port, baudrate=baudrate)
            self.controller = SynriaRobotAPI(session=self.session)
            
            # Test connection by trying to get robot state
            joints = self.controller.get_joints()
            if joints is not None:
                self.is_connected = True
                logger.info("Robot connected successfully")
                return True
            else:
                logger.error("Failed to read robot state after connection")
                self.disconnect()
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to robot: {str(e)}")
            self.disconnect()
            return False
    
    def disconnect(self):
        """Disconnect from the robot"""
        try:
            if self.session and self.session.joint_controller:
                self.session.joint_controller.disconnect()
                logger.info("Robot disconnected")
        except Exception as e:
            logger.error(f"Error during disconnect: {str(e)}")
        finally:
            self.session = None
            self.controller = None
            self.is_connected = False
    
    def is_ready(self) -> bool:
        """Check if robot is connected and ready"""
        return self.is_connected and self.controller is not None
    
    def get_controller(self) -> Optional[SynriaRobotAPI]:
        """Get the robot controller instance"""
        return self.controller if self.is_ready() else None

# Global robot manager instance
robot_manager = RobotConnectionManager()