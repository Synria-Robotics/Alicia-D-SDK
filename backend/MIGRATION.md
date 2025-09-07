# Migration Guide: Old FastAPI → New SDK v5.5.0

This guide shows how to migrate from the old FastAPI patterns to the new SDK v5.5.0 architecture.

## Old vs New Architecture

### Old Pattern (Problematic)
```python
# Old: Direct serial communication, mixed responsibilities
import serial
import time

class OldRobotController:
    def __init__(self, port, baudrate):
        self.serial = serial.Serial(port, baudrate)
        self.current_position = None
        # Mixed serial communication with business logic
    
    def move_robot(self, positions):
        # Direct serial commands mixed with movement logic
        for pos in positions:
            self.serial.write(self.build_frame(pos))
            time.sleep(0.1)
    
    def get_status(self):
        # Manual frame parsing
        raw_data = self.serial.read(20)
        return self.parse_frame(raw_data)
```

### New Pattern (Clean)
```python
# New: Clean separation using SDK
from alicia_d_sdk.controller import create_session, SynriaRobotAPI

class RobotControlService:
    def __init__(self):
        self.session = None
        self.controller = None
    
    def connect(self, port="", baudrate=1000000):
        self.session = create_session(port=port, baudrate=baudrate)
        self.controller = SynriaRobotAPI(session=self.session)
        return self.controller.get_joints() is not None
    
    def move_joints(self, target_joints, format='rad'):
        return self.controller.moveJ(
            target_joints=target_joints,
            joint_format=format
        )
    
    def get_state(self):
        return {
            'joints': self.controller.get_joints(),
            'pose': self.controller.get_pose(),
            'gripper': self.controller.get_gripper()
        }
```

## API Endpoint Migration

### Connection Management

#### Old Pattern
```python
@app.post("/connect")
async def connect(port: str, baudrate: int):
    try:
        robot.serial = serial.Serial(port, baudrate)
        return {"status": "connected"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

#### New Pattern
```python
@app.post("/api/robot/connect")
async def connect_robot(request: ConnectionRequest):
    success = robot_manager.connect(
        port=request.port,
        baudrate=request.baudrate
    )
    return ConnectionResponse(
        success=success,
        message="Connected successfully" if success else "Connection failed",
        is_connected=robot_manager.is_connected
    )
```

### State Reading

#### Old Pattern
```python
@app.get("/status")
async def get_status():
    try:
        # Manual frame reading and parsing
        data = robot.serial.read(20)
        joints = parse_joint_frame(data)
        return {"joints": joints}
    except:
        return {"error": "Failed to read"}
```

#### New Pattern
```python
@app.get("/api/robot/state")
async def get_robot_state(format: str = "rad") -> RobotState:
    if not robot_manager.is_ready():
        raise HTTPException(status_code=503, detail="Robot not connected")
    
    return robot_service.get_robot_state(output_format=format)
```

### Movement Control

#### Old Pattern
```python
@app.post("/move")
async def move_robot(joints: List[float]):
    try:
        for i, joint in enumerate(joints):
            frame = build_joint_frame(i, joint)
            robot.serial.write(frame)
            time.sleep(0.05)
        return {"status": "moved"}
    except Exception as e:
        return {"error": str(e)}
```

#### New Pattern
```python
@app.post("/api/robot/move/joints")
async def move_joints(request: MoveJRequest):
    if not robot_manager.is_ready():
        raise HTTPException(status_code=503, detail="Robot not connected")
    
    result = robot_service.move_joints(
        target_joints=request.target_joints,
        joint_format=request.joint_format,
        speed_factor=request.speed_factor,
        visualize=request.visualize
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    
    return result
```

### Gripper Control

#### Old Pattern
```python
@app.post("/gripper/{action}")
async def control_gripper(action: str, angle: float = None):
    if action == "open":
        frame = build_gripper_frame(100)  # Manual frame building
    elif action == "close":
        frame = build_gripper_frame(0)
    else:
        frame = build_gripper_frame(angle)
    
    robot.serial.write(frame)
    return {"status": "done"}
```

#### New Pattern
```python
@app.post("/api/robot/gripper")
async def control_gripper(request: GripperControlRequest):
    if not robot_manager.is_ready():
        raise HTTPException(status_code=503, detail="Robot not connected")
    
    result = robot_service.control_gripper(
        command=request.command,
        angle_deg=request.angle_deg,
        angle_rad=request.angle_rad
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    
    return result
```

## Error Handling Migration

### Old Pattern (Poor Error Handling)
```python
@app.post("/move")
async def move_robot(data):
    try:
        # Unsafe operations
        robot.move(data["joints"])
        return {"status": "ok"}
    except:
        return {"error": "something went wrong"}
```

### New Pattern (Robust Error Handling)
```python
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

@app.post("/api/robot/move/joints")
async def move_joints(request: MoveJRequest):
    # Validation happens automatically via Pydantic
    if not robot_manager.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Robot not connected"
        )
    
    result = robot_service.move_joints(**request.dict())
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message
        )
    
    return result
```

## Data Model Migration

### Old Pattern (No Validation)
```python
@app.post("/move")
async def move_robot(data: dict):
    # No validation - dangerous!
    joints = data.get("joints", [])
    # What if joints is None? Wrong type? Wrong length?
    robot.move(joints)
```

### New Pattern (Type-Safe Models)
```python
class MoveJRequest(BaseModel):
    target_joints: List[float] = Field(..., description="Target joint angles")
    joint_format: str = Field(default="rad", description="'rad' or 'deg'")
    speed_factor: float = Field(default=1.0, description="Speed factor (0.1 to 2.0)")
    visualize: bool = Field(default=False, description="Enable visualization")

@app.post("/api/robot/move/joints")
async def move_joints(request: MoveJRequest):
    # Automatic validation - safe!
    result = robot_service.move_joints(**request.dict())
    return result
```

## Configuration Migration

### Old Pattern (Hardcoded Values)
```python
# Scattered throughout code
SERIAL_PORT = "/dev/ttyUSB0"
BAUDRATE = 921600
TIMEOUT = 1.0

robot = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=TIMEOUT)
```

### New Pattern (Flexible Configuration)
```python
# Centralized in ConnectionRequest model
class ConnectionRequest(BaseModel):
    port: str = Field(default="", description="Serial port (empty for auto-detect)")
    baudrate: int = Field(default=1000000, description="Communication baudrate")

# Usage
def connect(self, port: str = "", baudrate: int = 1000000):
    self.session = create_session(port=port, baudrate=baudrate)
```

## Frontend Integration Migration

### Old Pattern (Manual Fetch)
```javascript
// Old: Manual error handling, inconsistent responses
async function moveRobot(joints) {
    try {
        const response = await fetch('/move', {
            method: 'POST',
            body: JSON.stringify({joints: joints})
        });
        const data = await response.json();
        if (data.error) {
            console.error(data.error);
            return false;
        }
        return true;
    } catch (e) {
        console.error(e);
        return false;
    }
}
```

### New Pattern (Clean Client API)
```javascript
// New: Clean, consistent API client
class RobotAPIClient {
    async moveJoints(targetJoints, options = {}) {
        const request = {
            target_joints: targetJoints,
            joint_format: options.format || 'rad',
            speed_factor: options.speed || 1.0,
            visualize: options.visualize || false
        };
        return this.request('/api/robot/move/joints', 'POST', request);
    }
}

// Usage
const robot = new RobotAPIClient();
const result = await robot.moveJoints([0, 30, 45, 0, 0, 0], {format: 'deg'});
```

## Key Benefits of Migration

1. **Type Safety**: Pydantic models prevent runtime errors
2. **Clean Architecture**: Separated concerns, easier to maintain
3. **Better Error Handling**: Meaningful error messages and proper HTTP status codes
4. **SDK Integration**: Leverages proven, tested SDK functionality
5. **Documentation**: Auto-generated OpenAPI documentation
6. **Testing**: Easier to test individual components
7. **Scalability**: Modular design allows easy extension
8. **Reliability**: SDK handles low-level communication details

## Migration Checklist

- [ ] Replace direct serial communication with SDK session management
- [ ] Create Pydantic models for all request/response data
- [ ] Implement proper error handling with meaningful HTTP status codes
- [ ] Separate business logic from API routing
- [ ] Add proper logging throughout the application
- [ ] Update frontend to use new API endpoints
- [ ] Test all endpoints without robot (health, status)
- [ ] Test all endpoints with robot connected
- [ ] Update documentation and examples