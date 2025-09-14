# Alicia-D SDK v5.6.0

## 概述

Alicia-D SDK v5.6.0 是经过完全重构的机械臂控制SDK，采用清晰的分层架构设计，解决了v5.5.x版本中功能重叠、职责不清、架构混乱的问题。

## 主要改进

### 1. 清晰的分层架构
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

### 2. 职责分离
- **用户层**: 提供简洁统一的API接口
- **规划层**: 纯轨迹规划，不涉及执行
- **控制层**: 运动控制和状态管理
- **执行层**: 硬件命令执行
- **硬件层**: 底层硬件驱动

### 3. 功能优化
- 消除了功能重叠
- 明确了各层职责
- 提供了清晰的接口
- 支持更好的扩展性

## 快速开始

### 安装

```bash
# 克隆仓库
git clone <repository-url>
cd alicia-d-sdk

# 切换到v5.6.0分支
git checkout v5.6.0

# 安装依赖
pip install -r requirements.txt
```

### 基本使用

```python
from alicia_d_sdk_v5_6_0 import create_robot

# 创建机械臂实例
robot = create_robot(port="COM6", baudrate=1000000)

# 连接
robot.connect()

# 基本运动
robot.moveJ(target_joints=[0.1, 0.2, 0.3, 0.0, 0.0, 0.0])
robot.movePose(target_pose=[0.3, 0.1, 0.2, 0, 0, 0, 1])

# 夹爪控制
robot.gripper_control(command="open")

# 断开连接
robot.disconnect()
```

## 架构详解

### 用户层 (SynriaRobotAPI)

提供简洁统一的用户接口，封装了所有高级功能。

**主要功能：**
- 关节空间运动 (`moveJ`, `moveJ_waypoints`)
- 笛卡尔空间运动 (`moveCartesian`, `movePose`)
- 在线控制 (`start_online_control`, `set_joint_target`)
- 夹爪控制 (`gripper_control`)
- 状态查询 (`get_joints`, `get_pose`, `get_gripper`)
- 系统控制 (`torque_control`, `zero_calibration`)

### 规划层 (TrajectoryPlanner)

负责轨迹规划，不涉及执行。

**主要功能：**
- 关节空间轨迹规划
- 笛卡尔空间轨迹规划
- 多种插值算法 (线性、三次、五次)
- 轨迹验证和优化

### 控制层 (MotionController)

负责运动控制和状态管理。

**主要功能：**
- 轨迹执行控制
- 在线实时控制
- 安全检查和限位
- 状态监控和反馈

### 执行层 (HardwareExecutor)

负责硬件命令执行。

**主要功能：**
- 轨迹执行
- 实时控制
- 执行监控
- 错误处理

### 硬件层 (ServoDriver)

负责底层硬件驱动。

**主要功能：**
- 串口通信
- 数据解析
- 硬件协议处理
- 状态读取

## API参考

### SynriaRobotAPI

#### 连接管理
```python
robot.connect() -> bool
robot.disconnect()
robot.is_connected() -> bool
```

#### 关节空间运动
```python
robot.moveJ(target_joints, joint_format='rad', speed_factor=1.0, ...)
robot.moveJ_waypoints(waypoints, joint_format='rad', speed_factor=1.0, ...)
```

#### 笛卡尔空间运动
```python
robot.moveCartesian(waypoints, speed_factor=1.0, ...)
robot.movePose(target_pose, speed_factor=1.0, ...)
```

#### 在线控制
```python
robot.start_online_control(command_rate_hz=200.0, ...)
robot.stop_online_control()
robot.set_joint_target(joint_angles)
robot.set_pose_target(pose)
```

#### 夹爪控制
```python
robot.gripper_control(command="open"|"close", angle_deg=None, ...)
```

#### 状态查询
```python
robot.get_joints() -> List[float]
robot.get_pose() -> List[float]
robot.get_gripper() -> float
robot.is_moving() -> bool
```

#### 系统控制
```python
robot.moveHome()
robot.torque_control(command="on"|"off")
robot.zero_calibration()
robot.emergency_stop()
```

## 示例代码

### 基本使用
```python
from alicia_d_sdk_v5_6_0 import create_robot

robot = create_robot(port="COM6")
robot.connect()

# 关节运动
robot.moveJ([0.1, 0.2, 0.3, 0.0, 0.0, 0.0])

# 位姿运动
robot.movePose([0.3, 0.1, 0.2, 0, 0, 0, 1])

# 夹爪控制
robot.gripper_control("open")

robot.disconnect()
```

### 高级控制
```python
# 多点轨迹
waypoints = [
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    [0.5, -0.3, 0.2, 0.0, 0.5, 0.0],
    [0.3, 0.2, 0.3, 0.0, 0.0, 0.0]
]

robot.moveJ_waypoints(
    waypoints=waypoints,
    speed_factor=0.5,
    progress_callback=lambda step, total, angles: print(f"进度: {step}/{total}"),
    completion_callback=lambda total: print(f"完成: {total}个点")
)

# 在线控制
robot.start_online_control()
robot.set_joint_target([0.1, 0.2, 0.3, 0.0, 0.0, 0.0])
robot.stop_online_control()
```

### 架构演示
```python
from alicia_d_sdk_v5_6_0 import (
    ServoDriver, RobotModel, IKController,
    HardwareExecutor, MotionController, StateManager,
    TrajectoryPlanner, OnlineInterpolator
)

# 创建各层组件
servo_driver = ServoDriver(port="COM6")
robot_model = RobotModel()
ik_controller = IKController(robot_model)
hardware_executor = HardwareExecutor(servo_driver)
motion_controller = MotionController(servo_driver, robot_model, ik_controller, hardware_executor)
state_manager = StateManager(servo_driver, robot_model)
trajectory_planner = TrajectoryPlanner(robot_model, ik_controller)
online_interpolator = OnlineInterpolator(servo_driver)

# 使用各层组件...
```

## 迁移指南

### 从v5.5.x迁移到v5.6.0

#### 1. 导入方式变化
```python
# 旧版本
from alicia_d_sdk.controller import create_session, SynriaRobotAPI

# 新版本
from alicia_d_sdk_v5_6_0 import create_robot, SynriaRobotAPI
```

#### 2. 创建实例方式变化
```python
# 旧版本
session = create_session(port="COM6", baudrate=1000000)
controller = SynriaRobotAPI(session=session)

# 新版本
robot = create_robot(port="COM6", baudrate=1000000)
```

#### 3. API调用方式基本不变
```python
# 这些调用方式在新版本中保持不变
robot.moveJ(target_joints=[0.1, 0.2, 0.3, 0.0, 0.0, 0.0])
robot.moveCartesian(waypoints=[[0.3, 0.1, 0.2, 0, 0, 0, 1]])
robot.gripper_control(command="open")
```

## 性能优化

### 1. 分层设计优势
- 各层职责明确，便于优化
- 可以独立测试和调试
- 支持更好的扩展性

### 2. 内存管理
- 更好的资源管理
- 减少内存泄漏
- 支持长时间运行

### 3. 错误处理
- 分层错误处理
- 更好的错误定位
- 支持错误恢复

## 故障排除

### 常见问题

1. **连接失败**
   - 检查串口设置
   - 确认波特率正确
   - 检查硬件连接

2. **运动失败**
   - 检查关节限位
   - 确认目标位置可达
   - 检查紧急停止状态

3. **IK求解失败**
   - 检查目标位姿是否可达
   - 调整初始关节角度
   - 检查机器人模型

### 调试模式

```python
# 启用调试模式
robot = create_robot(port="COM6", debug_mode=True)

# 查看详细日志
robot.print_state(continuous=True)
```

## 贡献指南

### 开发环境设置
```bash
git clone <repository-url>
cd alicia-d-sdk
git checkout v5.6.0
pip install -e .
```

### 代码规范
- 遵循PEP 8
- 使用类型注解
- 编写单元测试
- 更新文档

### 提交规范
- 使用清晰的提交信息
- 一个提交只做一件事
- 包含测试用例

## 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

## 联系方式

- 项目主页: <repository-url>
- 问题反馈: <issues-url>
- 邮箱: <email>

---

**注意**: 这是v5.6.0版本，与v5.5.x版本不兼容。请参考迁移指南进行升级。