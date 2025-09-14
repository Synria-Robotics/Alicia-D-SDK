# Alicia-D SDK v5.6.0 架构设计

## 分层架构

```
用户层: SynriaRobotAPI (统一用户接口)
    ↓
规划层: TrajectoryPlanner (轨迹规划)
    ↓  
控制层: MotionController (运动控制)
    ↓
执行层: HardwareExecutor (硬件执行)
    ↓
硬件层: ServoDriver (底层驱动)
```

## 各层职责

### 1. 用户层 (SynriaRobotAPI)
- **职责**: 提供简洁统一的用户接口
- **功能**: 
  - 高级运动命令 (moveJ, moveCartesian, moveHome)
  - 状态查询 (get_joints, get_pose, get_gripper)
  - 系统控制 (torque_control, zero_calibration)
  - 夹爪控制 (gripper_control)
- **特点**: 不直接处理底层细节，委托给下层

### 2. 规划层 (TrajectoryPlanner)
- **职责**: 纯轨迹规划，不涉及执行
- **功能**:
  - 关节空间轨迹规划 (JointSpacePlanner)
  - 笛卡尔空间轨迹规划 (CartesianSpacePlanner)
  - 在线插值规划 (OnlineInterpolator)
- **特点**: 输入目标，输出轨迹点序列

### 3. 控制层 (MotionController)
- **职责**: 运动控制和状态管理
- **功能**:
  - 轨迹执行控制
  - 在线实时控制
  - 状态监控和反馈
  - 安全检查和限位
- **特点**: 连接规划层和执行层

### 4. 执行层 (HardwareExecutor)
- **职责**: 硬件命令执行
- **功能**:
  - 关节命令发送
  - 夹爪命令发送
  - 状态数据读取
  - 通信管理
- **特点**: 纯执行，不涉及控制逻辑

### 5. 硬件层 (ServoDriver)
- **职责**: 底层硬件驱动
- **功能**:
  - 串口通信
  - 数据解析
  - 硬件协议处理
- **特点**: 最底层，与硬件直接交互

## 数据流

```
用户调用 → SynriaRobotAPI → TrajectoryPlanner → MotionController → HardwareExecutor → ServoDriver
    ↓           ↓              ↓                ↓                 ↓
    └─── 状态查询 ←─── 状态管理 ←─── 状态监控 ←─── 状态读取 ←─── 硬件反馈
```

## 重构原则

1. **单一职责**: 每层只负责自己的核心功能
2. **依赖倒置**: 上层依赖下层接口，不依赖具体实现
3. **接口隔离**: 每层提供清晰的接口
4. **开闭原则**: 对扩展开放，对修改封闭
5. **组合优于继承**: 使用组合而非继承实现功能

## 文件结构

```
alicia_d_sdk/
├── api/                    # 用户层
│   ├── __init__.py
│   └── synria_robot_api.py
├── planning/               # 规划层
│   ├── __init__.py
│   ├── trajectory_planner.py
│   ├── joint_space_planner.py
│   ├── cartesian_space_planner.py
│   └── online_interpolator.py
├── control/                # 控制层
│   ├── __init__.py
│   ├── motion_controller.py
│   └── state_manager.py
├── execution/              # 执行层
│   ├── __init__.py
│   └── hardware_executor.py
├── hardware/               # 硬件层
│   ├── __init__.py
│   ├── servo_driver.py
│   ├── serial_comm.py
│   └── data_parser.py
├── kinematics/             # 运动学 (工具层)
│   ├── __init__.py
│   ├── robot_model.py
│   └── ik_controller.py
└── utils/                  # 工具层
    ├── __init__.py
    ├── logger/
    └── coord/
```