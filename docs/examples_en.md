# Example Code Guide

The `examples/` directory contains multiple demonstration scripts showing how to use the Alicia-D SDK to control the robotic arm.

---

## 📁 File Structure

```
examples/
├── 00_demo_read_version.py          # Read version number
├── 01_torque_switch.py               # Torque control
├── 02_demo_set_new_zero_configuration.py  # Set new zero configuration
├── 03_demo_read_state.py            # Read state
├── 04_demo_move_gripper.py          # Gripper control
├── 05_demo_move_joint.py            # Joint space motion
├── 06_demo_forward_kinematics.py    # Forward kinematics
├── 07_demo_inverse_kinematics.py    # Inverse kinematics
├── 08_demo_drag_teaching.py         # Drag teaching
├── 09_demo_joint_traj.py            # Joint space trajectory planning
├── 10_demo_cartesian_traj.py        # Cartesian space trajectory planning
├── 11_benchmark_read_joints.py      # Joint reading performance benchmark
└── 12_utmostFPS.py                  # Maximum FPS test
```

## 📜 Example List

### 0. `00_demo_read_version.py`
**Read Robot Firmware Version**
- Always run this script first to detect firmware version before use
- Uses `get_robot_state("version")` to get version information
- Uses `get_robot_state("gripper_type")` to get gripper type
- If timeout or no version output is displayed, baud rate may need adjustment

**Usage:**
```bash
python 00_demo_read_version.py
```

---

### 1. `01_torque_switch.py`
Switch the torque state (power on/off) of all robot joints. After power off, the robot arm can be freely dragged.

**Parameters:**
- `--port`: Serial port (optional)

**Features:**
- First disable torque, then enable torque
- Robot arm can be manually dragged after torque is disabled
- Re-enable torque after teaching is complete

**Notes:**
- Manually support the robot arm before disabling torque to prevent sudden drop
- Always re-enable torque after teaching is complete

**Usage:**
```bash
python 01_torque_switch.py
```

---

### 2. `02_demo_set_new_zero_configuration.py`
Set the current position of the robot arm as the new zero point. **This operation is irreversible, use with caution.**

**Parameters:**
- `--port`: Serial port (optional)

**Use Cases:**
- First use of robot arm or after long period of non-use
- When joint angles show deviation
- When need to re-establish zero reference

**Usage:**
```bash
python 02_demo_set_new_zero_configuration.py
```

---

### 3. `03_demo_read_state.py`
Continuously read and print robot arm joint angles, end-effector pose, and gripper state. Supports single or continuous printing mode.

**Parameters:**
- `--port`: Serial port (optional)
- `--gripper_type`: Gripper model, default `50mm`
- `--format`: Angle display format, optional `rad` (radians) or `deg` (degrees), default `deg`
- `--single`: Print state once, default is continuous printing
- `--fps`: Target frames per second for continuous mode, default `30.0`

**Use Cases:**
- Debugging and troubleshooting
- Real-time monitoring of robot arm state
- Verifying control command execution effects

**Usage:**
```bash
# Continuous printing (press Ctrl+C to stop)
python 03_demo_read_state.py --gripper_type 50mm --fps 30

# Single print
python 03_demo_read_state.py --single
```

---

### 4. `04_demo_move_gripper.py`
Gripper control: Control gripper to open or close to specified angle. Gripper value range is 0-1000 (0 is fully closed, 1000 is fully open).

**Parameters:**
- `--port`: Serial port (optional)

**Features:**
- Automatic demo execution: fully open → fully close → half open
- Uses `set_robot_state(gripper_value=...)` to control gripper
- Uses `get_robot_state("gripper")` to read current gripper value
- Supports waiting for gripper motion completion

**Usage:**
```bash
python 04_demo_move_gripper.py
```

---

### 5. `05_demo_move_joint.py`
Use joint space motion to control robot arm movement to set angles. Supports degree and radian input, automatically performs joint angle interpolation.

**Parameters:**
- `--port`: Serial port (optional)
- `--speed_deg_s`: Joint motion speed (degrees/second), default 10, range 5-400

**Features:**
- Automatic demo execution: home → move to target angle → home
- Uses unified joint and gripper target interface `set_robot_state()`
- Supports `wait_for_completion=True` to wait for motion completion

**Usage:**
```bash
python 05_demo_move_joint.py --port /dev/ttyUSB0 --speed_deg_s 10
```

---

---

### 6. `06_demo_forward_kinematics.py`
Forward kinematics solving. Calculate end-effector pose based on current joint angles, display position, rotation matrix, Euler angles, quaternion and other representation forms.

**Parameters:**
- `--port`: Serial port (optional)
- `--version`: Robot version, default `v5_6`
- `--variant`: Robot variant, optional `gripper_50mm`, `gripper_100mm`, `leader_ur`, `leader`, `vertical_50mm`, default `gripper_50mm`
- `--model_format`: Model format, optional `urdf` or `mjcf`, default `urdf`
- `--base_link`: Base link name, default `base_link`
- `--end_link`: End-effector link name, default `tool0`

**Features:**
- Uses RoboCore library robot model
- Displays robot model information and kinematic chain
- Returns and displays: position, rotation matrix, Euler angles (radians/degrees), quaternion, homogeneous transformation matrix
- Note: Quaternions q and -q represent the same rotation

**Usage:**
```bash
python 06_demo_forward_kinematics.py --port /dev/ttyUSB0
```

---

### 7. `07_demo_inverse_kinematics.py`
Demonstrate inverse kinematics solving: Calculate and optionally execute joint angles based on given end-effector target pose. Supports multiple IK solving methods and multi-start optimization.

**Parameters:**
- `--port`: Serial port (optional)
- `--speed_deg_s`: Joint motion speed (degrees/second), default 10, range 5-400
- `--gripper_type`: Gripper type, default `50mm`
- `--base_link`: Base link name, default `base_link`
- `--end_link`: End-effector link name, default `tool0`
- `--end-pose`: Target pose (7 floats: px py pz qx qy qz qw), default value is preset
- `--method`: IK method, optional `dls` (damped least squares), `pinv` (pseudo-inverse), `transpose` (Jacobian transpose), default `dls`
- `--max-iters`: Maximum iterations, default 500
- `--pos-tol`: Position tolerance (meters), default 1e-3
- `--ori-tol`: Orientation tolerance (radians), default 1e-3
- `--num-inits`: Number of initial guesses, default 10
- `--init-strategy`: Initial guess strategy, optional `zero`, `random`, `sobol`, `latin`, `center`, `uniform`, `current`, default `current`
- `--init-scale`: Joint limit scale factor (0.0 to 1.0), default 1.0
- `--seed`: Random seed (optional)
- `--backend`: Computation backend, optional `cpp`, `numpy`, or `torch`, default `cpp`
- `--execute`: Execute movement to solved position
- `--force-execute`: Force execute movement, even if solving fails

**Features:**
- Displays detailed solving results (success/failure, iteration count, position error, orientation error)
- If movement is executed, automatically returns to initial position
- Supports multi-start optimization to improve success rate

**Usage:**
```bash
# Only calculate inverse solution, do not execute motion
python 07_demo_inverse_kinematics.py

# Calculate inverse solution and control robot arm to move to target pose
python 07_demo_inverse_kinematics.py --execute --speed_deg_s 10

# Use multi-start optimization to improve success rate
python 07_demo_inverse_kinematics.py --execute --num-inits 10
```

---

### 8. `08_demo_drag_teaching.py`
Drag teaching demonstration: Record a series of trajectory points by manually dragging the robot arm, and can replay. Supports manual interpolation, automatic fast, and replay-only modes.

**Parameters:**
- `--port`: Serial port (optional)
- `--speed_deg_s`: Joint motion speed (degrees/second), default 15, range 10-80
- `--mode`: Drag teaching mode, optional `manual` (manual interpolation), `auto` (automatic fast), or `replay_only` (replay only), default `auto`
- `--sample-hz`: Automatic mode sampling frequency, default 200.0 Hz
- `--save-motion`: Motion name (recording mode: new motion name; replay mode: existing motion name), default `my_demo`
- `--list-motions`: List all available motions and exit

**Features:**
- Disable torque to enter teaching mode
- Manually drag robot arm to record trajectory
- Supports manual mode (record key points) and automatic mode (continuous sampling)
- Replay recorded trajectory

**Usage:**
```bash
# List all available motions
python 08_demo_drag_teaching.py --list-motions

# Automatic mode record trajectory named "my_demo"
python 08_demo_drag_teaching.py --mode auto --save-motion my_demo

# Manual mode record key point trajectory
python 08_demo_drag_teaching.py --mode manual --save-motion key_points

# Replay existing trajectory "my_demo"
python 08_demo_drag_teaching.py --mode replay_only --save-motion my_demo
```

---

### 9. `09_demo_joint_traj.py`
**Joint Space Trajectory Planning and Execution**

Demonstrates how to generate smooth joint trajectories using joint space trajectory planning and execute through multiple waypoints.

**Parameters:**
- `--port`: Serial port (optional)
- `--gripper_type`: Gripper type, default `50mm`
- `--base_link`: Base link name, default `base_link`
- `--end_link`: End-effector link name, default `tool0`
- `--no-record`: Disable recording mode
- `--save-file`: Path to save recorded waypoints file
- `--waypoints-file`: Load waypoints from JSON file
- `--num-waypoints`: Number of waypoints for random generation, default 6
- `--planner`: Planner type, optional `b_spline` or `multi_segment`, default `b_spline`
- `--duration`: Trajectory duration (B-Spline), default 2.0 seconds
- `--num-points`: Number of trajectory points (B-Spline), default 800
- `--bspline-degree`: B-Spline degree, optional 3 or 5, default 5
- `--speed-deg-s`: Joint motion speed (degrees/second), default 20
- `--plot`: Disable trajectory visualization

**Features:**
- Supports manual waypoint recording or loading from file
- Uses B-Spline or Multi-Segment planner to generate smooth trajectories
- Supports gripper trajectory interpolation
- Optional trajectory visualization

**Usage:**
```bash
# Run with default parameters
python 09_demo_joint_traj.py

# Load waypoints from file
python 09_demo_joint_traj.py --waypoints-file waypoints.json

# Use Multi-Segment planner
python 09_demo_joint_traj.py --planner multi_segment
```

---

### 10. `10_demo_cartesian_traj.py`
**Cartesian Space Trajectory Planning and Execution**

Demonstrates how to generate smooth end-effector trajectories using Cartesian space spline trajectory planning and execute through inverse kinematics solving.

**Parameters:**
- `--port`: Serial port (optional)
- `--gripper_type`: Gripper type, default `50mm`
- `--base_link`: Base link name, default `base_link`
- `--end_link`: End-effector link name, default `tool0`
- `--no-record`: Disable recording mode
- `--save-file`: Path to save recorded waypoints file
- `--waypoints-file`: Load waypoints from JSON file
- `--num-waypoints`: Number of waypoints for random generation, default 2
- `--duration`: Trajectory duration (seconds), default 1.0
- `--num-points`: Number of trajectory points, default 10
- `--method`: IK method, optional `dls`, `pinv`, `transpose`, default `dls`
- `--max-iters`: Maximum IK iterations, default 100
- `--pos-tol`: Position tolerance (meters), default 1e-2
- `--ori-tol`: Orientation tolerance (radians), default 1e-2
- `--num-inits`: Number of initial guesses, default 5
- `--init-strategy`: Initial guess strategy, default `current`
- `--speed-deg-s`: Joint motion speed (degrees/second), default 20
- `--plot`: Disable trajectory visualization

**Features:**
- Supports manual Cartesian waypoint recording or loading from file
- Uses spline curves to generate smooth Cartesian trajectories
- Batch inverse kinematics solving (ensures continuity)
- Verifies that waypoints are accurately passed through
- Optional trajectory and IK results visualization

**Usage:**
```bash
# Run with default parameters
python 10_demo_cartesian_traj.py

# Load waypoints from file
python 10_demo_cartesian_traj.py --waypoints-file cartesian_waypoints.json

# Increase trajectory points for smoother motion
python 10_demo_cartesian_traj.py --num-points 100
```

---

### 11. `11_benchmark_read_joints.py`
**Joint Reading Performance Benchmark**

Tests the API call frequency and actual data update frequency for reading joint angles.

**Parameters:**
- `--port`: Serial port (optional)
- `--gripper_type`: Gripper type, default `50mm`
- `--duration`: Test duration (seconds), default 5.0
- `--fast`: Enable fast mode (set update interval to 1ms)

**Features:**
- Tests API read frequency (speed of reading cached data from Python memory)
- Tests data update frequency (actual rate of new data arriving from robot)
- Displays serial statistics (frames processed, frames dropped, etc.)

**Usage:**
```bash
# Basic test (5 seconds)
python 11_benchmark_read_joints.py

# Fast mode test
python 11_benchmark_read_joints.py --fast --duration 10
```

---

### 12. `12_utmostFPS.py`
**Maximum FPS Test**

Tests the maximum send and receive frame rate for serial communication.

**Parameters:**
- `--port`: Serial port (required, e.g., /dev/ttyUSB0 for Linux, COM3 for Windows, /dev/cu.* for macOS)
- `--baudrate`: Baud rate, default 1000000
- `--timeout`: Serial read timeout (seconds), default 0.015
- `--test-timeout`: Test duration (seconds), default 300.0

**Features:**
- Tests the extreme performance of serial communication
- Displays send frame rate, receive frame rate, and sync rate
- Suitable for performance optimization and hardware testing

**Usage:**
```bash
# Linux/Ubuntu
python 12_utmostFPS.py --port /dev/ttyACM0

# Windows
python 12_utmostFPS.py --port COM3

# macOS
python 12_utmostFPS.py --port /dev/cu.wchusbserial5B140413941

# Custom settings
python 12_utmostFPS.py --port /dev/ttyUSB0 --baudrate 2000000 --test-timeout 60
```

---

## ⚙️ Common Parameter Adjustment Scenarios

### Motion Control Parameter Adjustment:

*New Firmware (6.1.0 and above)*

- **Speed too fast**: Reduce `speed_deg_s` (range: 5-400 degrees/second)
- **Motion not smooth**: Increase `num_points` (trajectory interpolation points)
- **Movement time too long**: Reduce `move_duration` (movement time per waypoint)

### IK Solving Parameter Adjustment:
- **Solving fails**: Try different `method` (`dls`, `pinv`, `transpose`), increase `multi_start` (recommended 5-10)
- **Local optimum**: Use `use_random_init=True` or increase `multi_start`
- **High precision required**: Reduce `tolerance` to 1e-5 or smaller, increase `max_iters`
- **High speed required**: Use `method='pinv'` or `method='transpose'`

### Drag Teaching Parameter Adjustment:
- **Sampling frequency**: Adjust `--sample-hz` (default 300.0 Hz), higher frequency records more detail but larger files
- **Mode selection**: `manual` mode suitable for recording key points, `auto` mode suitable for continuous trajectory

---

