# Alicia-D Robot Control Backend

A completely refactored FastAPI backend for controlling Alicia-D robotic arms using SDK v5.5.0.

## Overview

This backend provides a clean, RESTful API for robot control with the following key improvements:

- **Modular Architecture**: Separated concerns with dedicated modules for connection management, robot services, and API models
- **Proper Session Management**: Uses the new SDK's session-based architecture
- **Comprehensive Error Handling**: Robust error handling and logging throughout
- **Type Safety**: Full Pydantic model validation for all API endpoints
- **CORS Support**: Ready for frontend integration

## Project Structure

```
backend/
├── main.py              # FastAPI application and route definitions
├── models.py            # Pydantic models for request/response validation  
├── robot_manager.py     # Robot connection and session management
├── robot_service.py     # High-level robot control services
├── requirements.txt     # Python dependencies
└── __init__.py         # Package initialization
```

## API Endpoints

### Connection Management
- `POST /api/robot/connect` - Connect to robot
- `POST /api/robot/disconnect` - Disconnect from robot  
- `GET /api/robot/status` - Get connection status

### Robot State
- `GET /api/robot/state` - Get complete robot state
- `GET /api/robot/joints` - Get joint angles
- `GET /api/robot/pose` - Get end effector pose
- `GET /api/robot/gripper` - Get gripper angle

### Movement Control
- `POST /api/robot/move/joints` - Move to joint positions
- `POST /api/robot/move/cartesian` - Move through Cartesian waypoints
- `POST /api/robot/move/home` - Move to home position

### Device Control
- `POST /api/robot/gripper` - Control gripper
- `POST /api/robot/torque` - Control torque (teaching mode)
- `POST /api/robot/calibrate` - Perform zero calibration

### Utilities
- `GET /health` - Server health check
- `GET /docs` - Interactive API documentation

## Running the Backend

### Option 1: Using npm (recommended)
```bash
npm run dev        # Development with auto-reload
npm run start      # Production
```

### Option 2: Direct Python
```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## SDK v5.5.0 Integration

The backend fully utilizes the new SDK features:

### Session Management
```python
from alicia_d_sdk.controller import create_session, SynriaRobotAPI

session = create_session(port="", baudrate=1000000)
controller = SynriaRobotAPI(session=session)
```

### Movement API
```python
# Joint movement with enhanced parameters
controller.moveJ(
    target_joints=[0, 30, 45, 0, 0, 0],
    joint_format='deg',
    speed_factor=1.0,
    visualize=False
)

# Cartesian movement with multiple planners
controller.moveCartesian(
    waypoints=[[x, y, z, qx, qy, qz, qw]],
    planner_name='cartesian',  # or 'lqt'
    move_time=3.0,
    reverse=False
)
```

### State Reading
```python
joints = controller.get_joints()          # Radians
pose = controller.get_pose()              # [x,y,z,qx,qy,qz,qw]
gripper = controller.get_gripper()        # Radians
```

### Control Functions
```python
controller.gripper_control(command='open')
controller.gripper_control(angle_deg=50)
controller.torque_control(command='off')  # Teaching mode
controller.zero_calibration()
```

## Frontend Integration

The backend is designed to work seamlessly with frontend applications. See `frontend/robot-api-client.js` for a complete JavaScript client implementation.

### Example Frontend Usage
```javascript
const robotAPI = new RobotAPIClient('http://localhost:8000');

// Connect
await robotAPI.connect();

// Get state
const state = await robotAPI.getRobotState('deg');

// Move robot
await robotAPI.moveJoints([0, 30, 45, 0, 0, 0], { format: 'deg' });

// Control gripper
await robotAPI.controlGripper('open');
```

## Error Handling

The backend provides comprehensive error handling:

- **Connection Errors**: Graceful handling of robot connection issues
- **Validation Errors**: Pydantic model validation with detailed error messages
- **Robot Errors**: SDK exceptions caught and returned as meaningful HTTP responses
- **Logging**: Detailed logging for debugging and monitoring

## Configuration

### Connection Settings
- **Port**: Leave empty for auto-detection
- **Baudrate**: 
  - `1000000` for SDK v5.4.19+ (default)
  - `921600` for older versions

### Logging
Logging is configured in `main.py` and can be adjusted as needed:
```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## Key Improvements Over Previous Version

1. **Clean Architecture**: Separated concerns with dedicated modules
2. **Modern FastAPI**: Uses latest FastAPI features and best practices
3. **Type Safety**: Full Pydantic validation throughout
4. **Session Management**: Proper SDK session handling
5. **Error Handling**: Comprehensive error handling and logging
6. **Documentation**: Self-documenting API with OpenAPI/Swagger
7. **CORS Support**: Ready for frontend integration
8. **Health Monitoring**: Health check and status endpoints

## Testing

The backend can be tested without a physical robot:
- Health endpoint works without robot connection
- Connection status endpoints provide meaningful responses
- API documentation is available at `/docs`

For full testing with a robot, ensure the robot is connected via serial/USB and use the appropriate port and baudrate settings.