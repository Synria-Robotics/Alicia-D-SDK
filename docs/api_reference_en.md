# API Reference

This section introduces the core classes and method interfaces of the Alicia-D SDK.

---

## Initialization Interface: `create_robot`

```python
from alicia_d_sdk import create_robot

robot = create_robot(
    port="",                    # Serial port (empty string for auto-detection)
    gripper_type=None,          # Gripper type ("50mm" or "100mm"), None to read from cache or default "50mm"
    debug_mode=False,           # Debug mode
    auto_connect=True,          # Auto-connect on creation
    base_link="base_link",      # Base link name
    end_link="tool0",           # End-effector link name
    backend=None,               # Computation backend, 'cpp', 'numpy', or 'torch' (default: None, uses 'cpp')
    device="cpu"                # Device for torch backend, 'cpu' or 'cuda' (default: 'cpu', ignored for 'cpp' / 'numpy')
)
```

---

## Control Interface: `alicia_d_sdk.api.synria_robot_api.SynriaRobotAPI`

```python
from alicia_d_sdk import create_robot

robot = create_robot()
```

### Main Methods:

#### Connection Management:
- `connect()`  
  Connect to the robot and detect firmware version

- `disconnect()`  
  Disconnect from the robot and stop update thread

- `is_connected()`  
  Check if the robot is connected

#### Motion Control:
- `set_home(speed_deg_s=10, gripper_speed_deg_s=483.4)`  
  Move the robot to the initial position
  
  **Parameters:**
  - `speed_deg_s`: Joint motion speed (degrees per second), can be int/float (same for all joints) or list/array (per-joint speeds), default 10
  - `gripper_speed_deg_s`: Gripper speed (degrees per second), if None, uses default 5500 ticks/s (≈483.4 deg/s), default 483.4

- `set_robot_state(target_joints=None, gripper_value=None, joint_format='rad', speed_deg_s=10, gripper_speed_deg_s=483.4, tolerance=0.1, timeout=10.0, wait_for_completion=True)`  
  Unified interface for setting joint and gripper targets, supports simultaneous setting of joint angles and gripper position
  
  **Parameters:**
  - `target_joints`: Optional target joint angles list (radians or degrees). If None, keeps current angles
  - `gripper_value`: Optional gripper value (0-1000, 0 is fully closed, 1000 is fully open). If None, keeps current value
  - `joint_format`: Unit format for joints, 'rad' (radians) or 'deg' (degrees), default 'rad'
  - `speed_deg_s`: Joint motion speed (degrees per second), can be int/float (same for all joints) or list/array (per-joint speeds, range 4.39-439.45 deg/s), default 10
  - `gripper_speed_deg_s`: Gripper speed (degrees per second), if None, uses default 5500 ticks/s (≈483.4 deg/s), default 483.4
  - `tolerance`: Joint target tolerance (radians), default 0.1
  - `timeout`: Maximum wait time (seconds), default 10.0
  - `wait_for_completion`: If True, wait until target reached, default True
  
  **Returns:** True if successful, False otherwise

- `set_pose(target_pose, backend=None, method='dls', pos_tol=1e-3, ori_tol=1e-3, max_iters=500, num_initial_guesses=10, initial_guess_strategy='current', initial_guess_scale=1.0, random_seed=None, speed_deg_s=10, gripper_speed_deg_s=483.4, execute=True, force_execute=False)`  
  Move the end-effector to target pose using inverse kinematics
  
  **Parameters:**
  - `target_pose`: Target pose as [x, y, z, qx, qy, qz, qw] (position + quaternion)
  - `backend`: Computation backend, 'cpp', 'numpy', or 'torch' (default: None, uses backend set at initialization; SDK default is 'cpp')
  - `method`: IK solver method, 'dls' (damped least squares), 'pinv' (pseudo-inverse), or 'transpose', default 'dls'
  - `pos_tol`: Position tolerance in meters, default 1e-3
  - `ori_tol`: Orientation tolerance in radians, default 1e-3
  - `max_iters`: Maximum number of iterations, default 500
  - `num_initial_guesses`: Number of initial guesses (multi-start), default 10
  - `initial_guess_strategy`: Initial guess strategy, 'zero', 'random', 'sobol', 'latin', 'center', 'uniform', 'current' (default: 'current', uses current joint angles)
  - `initial_guess_scale`: Scale factor for initial guesses (0.0 to 1.0), default 1.0
  - `random_seed`: Random seed for reproducibility, default None
  - `speed_deg_s`: Joint motion speed (degrees per second), can be int/float (same for all joints) or list/array (per-joint speeds), default 10
  - `gripper_speed_deg_s`: Gripper speed (degrees per second), if None, uses default 5500 ticks/s (≈483.4 deg/s), default 483.4
  - `execute`: Execute motion if True and IK succeeds, default True
  - `force_execute`: Force execute motion even if IK failed (requires q to be available), default False
  
  **Returns:** Dictionary with success, q, iters, pos_err, ori_err, message, motion_executed, computation_time

#### Trajectory Planning:
- `plan_joint_trajectory(waypoints, planner_type='b_spline', duration=None, num_points=800, bspline_degree=5, segment_method='quintic', duration_per_segment=None, num_points_per_segment=100, gripper_waypoints=None)`  
  Plan joint space trajectory, supports B-Spline and multi-segment planners
  
  **Parameters:**
  - `waypoints`: Array of joint waypoints [n_waypoints, n_dof] in radians
  - `planner_type`: Planner type, 'b_spline' or 'multi_segment', default 'b_spline'
  - `duration`: Total trajectory duration in seconds (for B-Spline)
  - `num_points`: Number of points in trajectory (for B-Spline), default 800
  - `bspline_degree`: B-Spline degree, 3 (cubic) or 5 (quintic), default 5
  - `segment_method`: Multi-segment method, 'cubic' or 'quintic', default 'quintic'
  - `duration_per_segment`: Duration per segment in seconds (for Multi-Segment)
  - `num_points_per_segment`: Number of points per segment (for Multi-Segment), default 100
  - `gripper_waypoints`: Optional array of gripper values [n_waypoints] (0-1000)
  
  **Returns:** Dictionary with 't', 'q', 'qd', 'qdd', and optionally 'gripper'

- `plan_cartesian_trajectory(waypoints, duration=None, num_points=100, backend=None)`  
  Plan Cartesian space spline trajectory
  
  **Parameters:**
  - `waypoints`: Array of waypoint poses [n_waypoints, 4, 4] (transformation matrices) or [n_waypoints, 3] (positions only)
  - `duration`: Total trajectory duration in seconds (optional, auto-estimated if None)
  - `num_points`: Number of points in trajectory, default 100
  - `backend`: Computation backend, 'cpp', 'numpy', or 'torch' (default: None, uses backend set at initialization; SDK default is 'cpp')
  
  **Returns:** Dictionary with 't', 'poses', 'positions', 'orientations', 'velocities', 'accelerations'

- `solve_ik_for_trajectory(target_poses, q_init=None, method='dls', max_iters=100, pos_tol=1e-2, ori_tol=1e-2, num_initial_guesses=5, initial_guess_strategy='random', initial_guess_scale=0.6, random_seed=None, backend=None, use_previous_solution=True)`  
  Batch solve inverse kinematics for a sequence of Cartesian poses
  
  **Parameters:**
  - `target_poses`: Array of target poses [n_poses, 4, 4] (transformation matrices)
  - `q_init`: Initial joint configuration (uses current joints if None)
  - `method`: IK solver method, 'dls', 'pinv', or 'transpose', default 'dls'
  - `max_iters`: Maximum IK iterations per pose, default 100
  - `pos_tol`: Position tolerance in meters, default 1e-2
  - `ori_tol`: Orientation tolerance in radians, default 1e-2
  - `num_initial_guesses`: Number of initial guesses for multi-start, default 5
  - `initial_guess_strategy`: Initial guess strategy, default 'random'
  - `initial_guess_scale`: Scale factor for initial guesses (0.0 to 1.0), default 0.6
  - `random_seed`: Random seed for reproducibility, default None
  - `backend`: Computation backend, 'cpp', 'numpy', or 'torch' (default: None, uses backend set at initialization; SDK default is 'cpp')
  - `use_previous_solution`: If True, use previous solution as initial guess (ensures continuity), default True
  
  **Returns:** Dictionary with 'joint_angles', 'ik_results', 'success_rate', 'statistics'

#### Status Retrieval:
- `get_robot_state(info_type="joint_gripper", timeout=1.0, cache=True)`  
  Unified interface for retrieving robot state information. Returns different data types based on `info_type`:
  
  **Parameters:**
  - `info_type`: Type of information to retrieve. Options:
    - `"joint_gripper"`: Returns `JointState` object (default), containing:
      - `angles`: List of six joint angles (radians)
      - `gripper`: Gripper opening value (0-1000, 0 is fully closed, 1000 is fully open)
      - `timestamp`: Timestamp (seconds)
      - `run_status_text`: Run status text ("idle", "locked", "sync", "sync_locked", "overheat", "overheat_protect", "unknown")
    - `"joint"`: Returns only joint angles as `List[float]` (radians)
    - `"gripper"`: Returns only gripper value as `float` (0-1000)
    - `"version"`: Returns version info dictionary with `serial_number`, `hardware_version`, `firmware_version`
    - `"temperature"`: Returns servo temperatures as `List[float]` (Celsius)
    - `"velocity"`: Returns servo velocities as `List[float]` (degrees per second)
    - `"self_check"`: Returns self-check status dictionary with `raw_mask`, `bits`, `timestamp`
    - `"gripper_type"`: Returns gripper type string (e.g., "50mm" or "100mm"), or None if unavailable
  - `timeout`: Maximum wait time in seconds (default: 1.0)
  - `cache`: Whether to use cache (only effective for gripper_type), default True
  
  **Returns:** Data of the requested type, or `None` if failed

- `get_pose(backend=None)`  
  Get current end-effector position and orientation, returns a dictionary containing `transform`, `position`, `rotation`, `euler_xyz`, `quaternion_xyzw`
  
  **Parameters:**
  - `backend`: Computation backend, 'cpp', 'numpy', or 'torch' (default: None, uses backend set at initialization; SDK default is 'cpp')
  
  **Returns:** Dictionary with pose information, or None if failed

- `print_state(continuous=False, output_format='deg', fps=200.0)`  
  Print current robot information, supports continuous printing, supports angle/radian format. Includes joint angles, gripper state, end-effector pose, temperature, velocity, and more
  
  **Parameters:**
  - `continuous`: If True, print continuously; if False, print once, default False
  - `output_format`: Angle format, 'deg' (degrees) or 'rad' (radians), default 'deg'
  - `fps`: Target frames per second for continuous mode (Hz), default 200.0

#### Gripper Control:
- `set_robot_state(gripper_value=...)`  
  Control gripper through unified interface, gripper_value range 0-1000 (0 is fully closed, 1000 is fully open)
  
  **Examples:**
  ```python
  # Open gripper
  robot.set_robot_state(gripper_value=1000)
  
  # Close gripper
  robot.set_robot_state(gripper_value=0)
  
  # Set joints and gripper together
  robot.set_robot_state(target_joints=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6], gripper_value=500)
  ```

#### System Control:
- `torque_control(command, timeout=1.0)`  
  Enable or disable torque ('on' or 'off')
  
  **Parameters:**
  - `command`: Command, 'on' or 'off'
  - `timeout`: Maximum time to wait for response in seconds, default 1.0
  
  **Returns:** True if successful, False otherwise

- `zero_calibration()`  
  Execute zero calibration process: disable torque → manual drag → re-enable torque → record zero point


---

---

## RoboCore Integration

The SDK integrates the [RoboCore](https://github.com/Synria-Robotics/RoboCore) library, providing high-performance kinematics and trajectory planning functionality:

### Kinematics Functions (from robocore.kinematics):
- `forward_kinematics(robot_model, q, backend='cpp', return_end=True)`
- `inverse_kinematics(robot_model, pose, q_init, backend='cpp', method='dls', ...)`
- `jacobian(robot_model, q, backend='cpp', method='analytic')`

Note: the SDK defaults to the `cpp` backend, while `numpy` and `torch` remain available as explicit overrides.


---

For more details, please refer to the source code documentation or check the log files in the `logs/` directory.

