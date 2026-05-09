# API 参考文档

本节介绍 Alicia-D SDK 的核心类与方法接口。

---

##  初始化接口：`create_robot`

```python
from alicia_d_sdk import create_robot

robot = create_robot(
    port="",                    # 串口（留空自动查找）
    gripper_type=None,          # 夹爪类型（"50mm" 或 "100mm"），None 时从缓存文件读取或默认 "50mm"
    debug_mode=False,           # 调试模式
    auto_connect=True,          # 自动连接
    base_link="base_link",      # 基座链路名称
    end_link="tool0",           # 末端执行器链路名称
    backend=None,               # 计算后端，'cpp'、'numpy' 或 'torch'（默认: None，使用 'cpp'）
    device="cpu"                # torch 后端设备，'cpu' 或 'cuda'（默认: 'cpu'，对 'cpp' / 'numpy' 忽略）
)
```

---

##  控制接口：`alicia_d_sdk.api.synria_robot_api.SynriaRobotAPI`

```python
from alicia_d_sdk import create_robot

robot = create_robot()
```

### 主要方法一览：

#### 连接管理：
- `connect()`  
  连接机械臂并检测固件版本

- `disconnect()`  
  断开机械臂连接并停止更新线程

- `is_connected()`  
  检查机械臂是否连接

#### 运动控制：
- `set_home(speed_deg_s=10, gripper_speed_deg_s=483.4)`  
  移动机械臂到初始位置
  
  **参数：**
  - `speed_deg_s`: 关节运动速度（度/秒），可以是 int/float（所有关节相同）或 list/array（每个关节不同速度），默认 10
  - `gripper_speed_deg_s`: 夹爪运动速度（度/秒），如果为 None，使用默认 5500 ticks/s (≈483.4 deg/s)，默认 483.4

- `set_robot_state(target_joints=None, gripper_value=None, joint_format='rad', speed_deg_s=10, gripper_speed_deg_s=483.4, tolerance=0.1, timeout=10.0, wait_for_completion=True)`  
  统一的关节和夹爪目标设置接口，支持同时设置关节角度和夹爪位置
  
  **参数：**
  - `target_joints`: 可选的目标关节角度列表（弧度或度数）。如果为 None，保持当前角度
  - `gripper_value`: 可选的夹爪值（0-1000，0为完全闭合，1000为完全张开）。如果为 None，保持当前值
  - `joint_format`: 关节角度单位格式，'rad'（弧度）或 'deg'（度数），默认 'rad'
  - `speed_deg_s`: 关节运动速度（度/秒），可以是 int/float（所有关节相同）或 list/array（每个关节不同速度，范围 4.39-439.45 deg/s），默认 10
  - `gripper_speed_deg_s`: 夹爪运动速度（度/秒），如果为 None，使用默认 5500 ticks/s (≈483.4 deg/s)，默认 483.4
  - `tolerance`: 关节目标容差（弧度），默认 0.1
  - `timeout`: 最大等待时间（秒），默认 10.0
  - `wait_for_completion`: 如果为 True，等待到达目标位置，默认 True
  
  **返回值：** 成功返回 True，失败返回 False

- `set_pose(target_pose, backend=None, method='dls', pos_tol=1e-3, ori_tol=1e-3, max_iters=500, num_initial_guesses=10, initial_guess_strategy='current', initial_guess_scale=1.0, random_seed=None, speed_deg_s=10, gripper_speed_deg_s=483.4, execute=True, force_execute=False)`  
  使用逆运动学移动末端执行器到目标位姿
  
  **参数：**
  - `target_pose`: 目标位姿，格式为 [x, y, z, qx, qy, qz, qw]（位置 + 四元数）
  - `backend`: 计算后端，'cpp'、'numpy' 或 'torch'（默认: None，使用初始化时设置的后端；SDK 默认是 'cpp'）
  - `method`: IK 求解方法，'dls'（阻尼最小二乘）、'pinv'（伪逆）或 'transpose'（转置），默认 'dls'
  - `pos_tol`: 位置容差（米），默认 1e-3
  - `ori_tol`: 姿态容差（弧度），默认 1e-3
  - `max_iters`: 最大迭代次数，默认 500
  - `num_initial_guesses`: 初始猜测数量（多起点），默认 10
  - `initial_guess_strategy`: 初始猜测策略，'zero', 'random', 'sobol', 'latin', 'center', 'uniform', 'current'（默认: 'current'，使用当前关节角度）
  - `initial_guess_scale`: 初始猜测缩放因子（0.0 到 1.0），默认 1.0
  - `random_seed`: 随机种子，用于可重复性，默认 None
  - `speed_deg_s`: 关节运动速度（度/秒），可以是 int/float（所有关节相同）或 list/array（每个关节不同速度），默认 10
  - `gripper_speed_deg_s`: 夹爪运动速度（度/秒），如果为 None，使用默认 5500 ticks/s (≈483.4 deg/s)，默认 483.4
  - `execute`: 如果为 True 且 IK 成功，执行运动，默认 True
  - `force_execute`: 如果为 True，即使 IK 失败也强制执行（需要 q 可用），默认 False
  
  **返回值：** 包含 success, q, iters, pos_err, ori_err, message, motion_executed, computation_time 的字典

#### 轨迹规划：
- `plan_joint_trajectory(waypoints, planner_type='b_spline', duration=None, num_points=800, bspline_degree=5, segment_method='quintic', duration_per_segment=None, num_points_per_segment=100, gripper_waypoints=None)`  
  规划关节空间轨迹，支持 B-Spline 和多段轨迹规划器
  
  **参数：**
  - `waypoints`: 关节路径点数组 [n_waypoints, n_dof]（弧度）
  - `planner_type`: 规划器类型，'b_spline' 或 'multi_segment'，默认 'b_spline'
  - `duration`: 轨迹总时长（秒）（B-Spline 使用）
  - `num_points`: 轨迹点数（B-Spline 使用），默认 800
  - `bspline_degree`: B-Spline 阶数，3（三次）或 5（五次），默认 5
  - `segment_method`: 多段方法，'cubic' 或 'quintic'，默认 'quintic'
  - `duration_per_segment`: 每段时长（秒）（Multi-Segment 使用）
  - `num_points_per_segment`: 每段点数（Multi-Segment 使用），默认 100
  - `gripper_waypoints`: 可选的夹爪值数组 [n_waypoints]（0-1000）
  
  **返回值：** 包含 't', 'q', 'qd', 'qdd' 和可选 'gripper' 的字典

- `plan_cartesian_trajectory(waypoints, duration=None, num_points=100, backend=None)`  
  规划笛卡尔空间样条轨迹
  
  **参数：**
  - `waypoints`: 路径点数组 [n_waypoints, 4, 4]（变换矩阵）或 [n_waypoints, 3]（仅位置）
  - `duration`: 轨迹总时长（秒），可选，如果为 None 则自动估算
  - `num_points`: 轨迹点数，默认 100
  - `backend`: 计算后端，'cpp'、'numpy' 或 'torch'（默认: None，使用初始化时设置的后端；SDK 默认是 'cpp'）
  
  **返回值：** 包含 't', 'poses', 'positions', 'orientations', 'velocities', 'accelerations' 的字典

- `solve_ik_for_trajectory(target_poses, q_init=None, method='dls', max_iters=100, pos_tol=1e-2, ori_tol=1e-2, num_initial_guesses=5, initial_guess_strategy='random', initial_guess_scale=0.6, random_seed=None, backend=None, use_previous_solution=True)`  
  为一系列笛卡尔位姿批量求解逆运动学
  
  **参数：**
  - `target_poses`: 目标位姿数组 [n_poses, 4, 4]（变换矩阵）
  - `q_init`: 初始关节配置（如果为 None，使用当前关节角度）
  - `method`: IK 求解方法，'dls', 'pinv' 或 'transpose'，默认 'dls'
  - `max_iters`: 每个位姿的最大 IK 迭代次数，默认 100
  - `pos_tol`: 位置容差（米），默认 1e-2
  - `ori_tol`: 姿态容差（弧度），默认 1e-2
  - `num_initial_guesses`: 多起点初始猜测数量，默认 5
  - `initial_guess_strategy`: 初始猜测策略，默认 'random'
  - `initial_guess_scale`: 初始猜测缩放因子（0.0 到 1.0），默认 0.6
  - `random_seed`: 随机种子，默认 None
  - `backend`: 计算后端，'cpp'、'numpy' 或 'torch'（默认: None，使用初始化时设置的后端；SDK 默认是 'cpp'）
  - `use_previous_solution`: 如果为 True，使用前一个解作为初始猜测（确保连续性），默认 True
  
  **返回值：** 包含 'joint_angles', 'ik_results', 'success_rate', 'statistics' 的字典

#### 状态获取：
- `get_robot_state(info_type="joint_gripper", timeout=1.0, cache=True)`  
  统一的机械臂状态获取接口，根据 `info_type` 返回不同类型的数据：
  
  **参数：**
  - `info_type`: 信息类型，可选值：
    - `"joint_gripper"`: 返回 `JointState` 对象（默认），包含：
      - `angles`: 六个关节角度列表（弧度）
      - `gripper`: 夹爪开合度（0-1000，0为完全闭合，1000为完全张开）
      - `timestamp`: 时间戳（秒）
      - `run_status_text`: 运行状态文本（"idle", "locked", "sync", "sync_locked", "overheat", "overheat_protect", "unknown"）
    - `"joint"`: 仅返回关节角度列表 `List[float]`（弧度）
    - `"gripper"`: 仅返回夹爪值 `float`（0-1000）
    - `"version"`: 返回版本信息字典，包含 `serial_number`, `hardware_version`, `firmware_version`
    - `"temperature"`: 返回舵机温度列表 `List[float]`（摄氏度）
    - `"velocity"`: 返回舵机速度列表 `List[float]`（度/秒）
    - `"self_check"`: 返回自检状态字典，包含 `raw_mask`, `bits`, `timestamp`
    - `"gripper_type"`: 返回夹爪类型字符串（如 "50mm" 或 "100mm"），失败时返回 None
  - `timeout`: 最大等待时间（秒），默认 1.0
  - `cache`: 是否使用缓存（仅对 gripper_type 有效），默认 True
  
  **返回值：** 根据 `info_type` 返回相应类型的数据，失败返回 `None`

- `get_pose(backend=None)`  
  获取当前末端执行器位置与姿态，返回字典包含 `transform`, `position`, `rotation`, `euler_xyz`, `quaternion_xyzw`
  
  **参数：**
  - `backend`: 计算后端，'cpp'、'numpy' 或 'torch'（默认: None，使用初始化时设置的后端；SDK 默认是 'cpp'）
  
  **返回值：** 包含位姿信息的字典，失败返回 None

- `print_state(continuous=False, output_format='deg', fps=200.0)`  
  打印当前机械臂信息，可持续打印，支持角度/弧度格式。包含关节角度、夹爪状态、末端位姿、温度、速度等信息
  
  **参数：**
  - `continuous`: 如果为 True，持续打印；如果为 False，仅打印一次，默认 False
  - `output_format`: 角度格式，'deg'（度）或 'rad'（弧度），默认 'deg'
  - `fps`: 连续模式的目标帧率（Hz），默认 200.0

#### 夹爪控制：
- `set_robot_state(gripper_value=...)`  
  通过统一接口控制夹爪，gripper_value 范围 0-1000（0为完全闭合，1000为完全张开）
  
  **示例：**
  ```python
  # 打开夹爪
  robot.set_robot_state(gripper_value=1000)
  
  # 关闭夹爪
  robot.set_robot_state(gripper_value=0)
  
  # 同时设置关节和夹爪
  robot.set_robot_state(target_joints=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6], gripper_value=500)
  ```

#### 系统控制：
- `torque_control(command, timeout=1.0)`  
  启用或关闭扭矩（'on' 或 'off'）
  
  **参数：**
  - `command`: 命令，'on' 或 'off'
  - `timeout`: 最大等待响应时间（秒），默认 1.0
  
  **返回值：** 成功返回 True，失败返回 False

- `zero_calibration()`  
  执行归零校准流程：关闭扭矩 → 手动拖动 → 重启扭矩 → 记录零点


---

##  硬件层接口：`alicia_d_sdk.hardware.ServoDriver`

提供底层串口通信、数据解析和舵机控制功能。

### 主要方法：

#### 连接管理：
- `connect() -> bool`  
  连接机械臂硬件并启动状态更新线程

- `disconnect()`  
  断开机械臂硬件连接并停止状态更新线程

#### 信息获取：
- `acquire_info(info_type: str, wait: bool = False, timeout: float = 2.0, retry_interval: float = 0.2) -> bool`  
  向机械臂硬件请求信息。支持的 `info_type` 值：
  - `"version"`: 固件版本信息
  - `"joint_gripper"`: 关节角度和夹爪状态
  - `"temperature"`: 舵机温度
  - `"velocity"`: 舵机速度
  - `"self_check"`: 自检状态
  - `"gripper_type"`: 夹爪类型信息
  - `"torque_on"` / `"torque_off"`: 启用/禁用扭矩
  - `"zero_cali"`: 将当前位置设置为零点

#### 控制：
- `set_joint_and_gripper(joint_angles: Optional[List[float]] = None, gripper_value: Optional[float] = None, speed_deg_s: int = 10) -> bool`  
  统一方法，可在单个命令中设置关节、夹爪或两者。这是主要的控制方法。

#### 线程管理：
- `start_update_thread()`  
  启动后台线程，持续读取和解析传入的数据帧

- `stop_update_thread()`  
  停止后台状态更新线程

- `is_update_thread_running() -> bool`  
  检查更新线程是否正在运行

### 数据解析器：`alicia_d_sdk.hardware.DataParser`

通过 `servo_driver.data_parser` 访问 `DataParser`，提供解析后的数据：

- `get_info(info_type: str)`  
  统一的解析信息获取方法。根据 `info_type` 返回数据（与 `acquire_info` 相同的值）

- `get_joint_state() -> Optional[JointState]`  
  获取当前关节状态（旧方法，建议使用 `get_info("joint_gripper")`）

**注意：** 不推荐用户直接使用硬件层。建议通过 `SynriaRobotAPI` 高级接口操作，该接口提供了更简洁、更用户友好的 API。


---

##  RoboCore 集成

SDK 集成了 [RoboCore](https://github.com/Synria-Robotics/RoboCore) 库，提供高性能运动学和轨迹规划功能：

### 运动学功能（来自 robocore.kinematics）：
- `forward_kinematics(robot_model, q, backend='cpp', return_end=True)`
- `inverse_kinematics(robot_model, pose, q_init, backend='cpp', method='dls', ...)`
- `jacobian(robot_model, q, backend='cpp', method='analytic')`

说明：SDK 默认使用 `cpp` backend，也可显式切换为 `numpy` 或 `torch`。

### 轨迹规划功能（来自 robocore.planning）：
- `cubic_polynomial_trajectory(q_start, q_end, duration, num_points)`
- `quintic_polynomial_trajectory(q_start, q_end, duration, num_points)`
- `linear_joint_trajectory(q_start, q_end, duration, num_points)`
- `linear_cartesian_trajectory(robot_model, pose_start, pose_end, duration, ...)`
- `trapezoidal_velocity_profile(distance, max_vel, max_acc)`

---

如需更多细节，请参考源码文档或查看 `logs/` 下日志文件输出。