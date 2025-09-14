# MuJoCo仿真集成指南

## 概述

Alicia-D SDK v5.6.0现已集成MuJoCo仿真环境，提供与真实机械臂API完全兼容的仿真接口。这使得开发者可以在没有真实硬件的情况下进行算法开发、测试和验证。

## 功能特性

### ✅ 已实现功能

1. **完整的API兼容性** - 与真实机械臂API完全兼容
2. **可视化支持** - 实时3D可视化窗口
3. **关节空间控制** - 支持6自由度关节控制
4. **夹爪控制** - 支持夹爪开合控制
5. **轨迹规划** - 支持多点轨迹运动
6. **在线控制** - 支持实时在线控制
7. **限位检查** - 关节和夹爪限位保护
8. **回调支持** - 进度、完成、错误回调
9. **参数配置** - 运动参数和限位设置
10. **状态查询** - 实时状态信息获取

### 🎯 核心优势

- **零硬件依赖** - 无需真实机械臂即可开发
- **快速迭代** - 算法开发和测试更高效
- **安全测试** - 避免硬件损坏风险
- **成本节约** - 降低开发和测试成本
- **教学友好** - 适合教学和培训

## 安装配置

### 1. 安装MuJoCo依赖

```bash
# 安装MuJoCo
pip install mujoco>=2.3.0
pip install mujoco-python-viewer>=0.1.0
pip install gymnasium>=0.29.0

# 或者使用requirements.txt
pip install -r requirements.txt
```

### 2. 验证安装

```python
import mujoco
print(f"MuJoCo版本: {mujoco.__version__}")

# 测试基本功能
import mujoco_viewer
print("MuJoCo安装成功！")
```

## 快速开始

### 基本使用

```python
from alicia_d_sdk import create_simulation_robot

# 创建仿真机械臂
robot = create_simulation_robot(enable_viewer=True)

# 连接仿真环境
if robot.connect():
    print("仿真环境连接成功！")
    
    # 获取当前状态
    joint_angles = robot.get_joint_angles()
    print(f"当前关节角度: {joint_angles}")
    
    # 执行关节运动
    robot.moveJ([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])
    
    # 执行夹爪运动
    robot.moveGripper(0.5)
    
    # 断开连接
    robot.disconnect()
```

### 高级使用

```python
from alicia_d_sdk import create_simulation_robot
import time

# 创建仿真机械臂
robot = create_simulation_robot(enable_viewer=True)

if robot.connect():
    # 设置运动参数
    robot.set_motion_parameters(
        max_velocity=1.0,
        max_acceleration=4.0
    )
    
    # 设置关节限位
    custom_limits = [
        (-2.0, 2.0),  # 关节1
        (-1.0, 1.0),  # 关节2
        (-2.0, 2.0),  # 关节3
        (-2.0, 2.0),  # 关节4
        (-1.0, 1.0),  # 关节5
        (-2.0, 2.0),  # 关节6
    ]
    robot.set_joint_limits(custom_limits)
    
    # 设置回调函数
    def progress_callback(current, total, joint_point):
        print(f"进度: {current}/{total}")
    
    def completion_callback():
        print("运动完成")
    
    robot.set_callbacks(
        progress_callback=progress_callback,
        completion_callback=completion_callback
    )
    
    # 执行多点轨迹
    waypoints = [
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [0.2, 0.1, 0.1, 0.0, 0.0, 0.0],
        [0.3, 0.2, 0.2, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    ]
    
    robot.moveJ_waypoints(waypoints, speed_factor=0.5)
    
    robot.disconnect()
```

## API参考

### SimulationInterface类

#### 连接管理

```python
def connect() -> bool:
    """连接仿真环境"""
    
def disconnect() -> bool:
    """断开仿真环境"""
```

#### 状态查询

```python
def get_joint_angles(joint_format: str = 'rad') -> List[float]:
    """获取当前关节角度"""
    
def get_gripper_angle(joint_format: str = 'rad') -> float:
    """获取当前夹爪角度"""
    
def get_end_effector_pose() -> List[float]:
    """获取末端执行器位姿 [x, y, z, qx, qy, qz, qw]"""
    
def is_moving() -> bool:
    """检查机械臂是否在运动"""
    
def is_online_control_active() -> bool:
    """检查在线控制是否激活"""
```

#### 运动控制

```python
def moveJ(target_joints: List[float], 
          joint_format: str = 'rad',
          speed_factor: float = 1.0,
          interpolation_type: str = 'cubic') -> bool:
    """关节空间运动"""
    
def moveGripper(target_angle: float,
                joint_format: str = 'rad',
                speed_factor: float = 1.0) -> bool:
    """夹爪运动"""
    
def moveJ_waypoints(waypoints: List[List[float]],
                   joint_format: str = 'rad',
                   speed_factor: float = 1.0,
                   interpolation_type: str = 'cubic') -> bool:
    """多点关节轨迹运动"""
    
def stop_motion():
    """停止运动"""
```

#### 在线控制

```python
def start_online_control(command_rate_hz: float = 200.0) -> bool:
    """启动在线控制"""
    
def stop_online_control() -> bool:
    """停止在线控制"""
    
def set_joint_target(target_joints: List[float], 
                    joint_format: str = 'rad') -> bool:
    """设置在线控制目标"""
    
def set_gripper_target(target_angle: float,
                      joint_format: str = 'rad') -> bool:
    """设置夹爪目标"""
```

#### 配置管理

```python
def set_joint_limits(joint_limits: List[tuple]) -> bool:
    """设置关节限位"""
    
def set_gripper_limits(gripper_limits: tuple) -> bool:
    """设置夹爪限位"""
    
def set_motion_parameters(max_velocity: float = None,
                         max_acceleration: float = None) -> bool:
    """设置运动参数"""
    
def set_callbacks(progress_callback: Callable = None,
                 completion_callback: Callable = None,
                 error_callback: Callable = None):
    """设置回调函数"""
```

## 使用示例

### 示例1: 基本运动控制

```python
from alicia_d_sdk import create_simulation_robot

robot = create_simulation_robot(enable_viewer=True)

if robot.connect():
    # 单点运动
    robot.moveJ([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])
    
    # 夹爪控制
    robot.moveGripper(0.5)
    
    robot.disconnect()
```

### 示例2: 轨迹规划

```python
from alicia_d_sdk import create_simulation_robot

robot = create_simulation_robot(enable_viewer=True)

if robot.connect():
    # 多点轨迹
    waypoints = [
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [0.2, 0.1, 0.1, 0.0, 0.0, 0.0],
        [0.3, 0.2, 0.2, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    ]
    
    robot.moveJ_waypoints(waypoints, speed_factor=0.5)
    
    robot.disconnect()
```

### 示例3: 在线控制

```python
from alicia_d_sdk import create_simulation_robot
import time

robot = create_simulation_robot(enable_viewer=True)

if robot.connect():
    # 启动在线控制
    robot.start_online_control(command_rate_hz=100.0)
    
    # 在线控制命令
    targets = [
        [0.1, 0.1, 0.1, 0.0, 0.0, 0.0],
        [0.2, 0.2, 0.2, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    ]
    
    for target in targets:
        robot.set_joint_target(target)
        time.sleep(2)
    
    # 停止在线控制
    robot.stop_online_control()
    
    robot.disconnect()
```

### 示例4: 回调函数

```python
from alicia_d_sdk import create_simulation_robot

def progress_callback(current, total, joint_point):
    print(f"进度: {current}/{total}, 关节角度: {joint_point}")

def completion_callback():
    print("运动完成")

def error_callback(error_message):
    print(f"错误: {error_message}")

robot = create_simulation_robot(enable_viewer=True)

if robot.connect():
    # 设置回调函数
    robot.set_callbacks(
        progress_callback=progress_callback,
        completion_callback=completion_callback,
        error_callback=error_callback
    )
    
    # 执行运动
    robot.moveJ([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])
    
    robot.disconnect()
```

## 配置选项

### 模型配置

```python
# 使用自定义模型
robot = create_simulation_robot(
    model_path="/path/to/custom_model.xml",
    enable_viewer=True
)
```

### 运动参数配置

```python
# 设置运动参数
robot.set_motion_parameters(
    max_velocity=1.0,      # 最大关节速度 (rad/s)
    max_acceleration=4.0   # 最大关节加速度 (rad/s²)
)
```

### 限位配置

```python
# 设置关节限位
joint_limits = [
    (-3.14, 3.14),  # 关节1
    (-1.57, 1.57),  # 关节2
    (-3.14, 3.14),  # 关节3
    (-3.14, 3.14),  # 关节4
    (-1.57, 1.57),  # 关节5
    (-3.14, 3.14),  # 关节6
]
robot.set_joint_limits(joint_limits)

# 设置夹爪限位
robot.set_gripper_limits((0.0, 1.57))  # 0-90度
```

## 故障排除

### 常见问题

1. **MuJoCo安装失败**
   ```bash
   # 确保Python版本兼容
   python --version  # 需要Python 3.8+
   
   # 重新安装
   pip uninstall mujoco
   pip install mujoco>=2.3.0
   ```

2. **可视化窗口无法显示**
   ```python
   # 禁用可视化
   robot = create_simulation_robot(enable_viewer=False)
   
   # 或者检查显示环境
   echo $DISPLAY  # Linux
   ```

3. **模型加载失败**
   ```python
   # 检查模型文件路径
   import os
   model_path = "alicia_d_sdk/simulation/models/alicia_arm.xml"
   print(f"模型文件存在: {os.path.exists(model_path)}")
   ```

4. **运动执行失败**
   ```python
   # 检查关节限位
   joint_angles = robot.get_joint_angles()
   print(f"当前关节角度: {joint_angles}")
   
   # 检查限位设置
   limits = robot.joint_limits
   print(f"关节限位: {limits}")
   ```

### 调试模式

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 创建仿真机器人
robot = create_simulation_robot(enable_viewer=True)
```

## 性能优化

### 仿真速度优化

```python
# 调整仿真参数
robot.simulator.mujoco_manager.set_timestep(0.002)  # 2ms时间步长
robot.simulator.mujoco_manager.set_max_speed(2.0)   # 2倍速度
```

### 内存优化

```python
# 定期重置仿真
robot.reset_simulation()
```

## 扩展开发

### 自定义模型

1. 创建自定义MuJoCo模型文件
2. 放置在 `alicia_d_sdk/simulation/models/` 目录
3. 使用自定义模型创建仿真机器人

```python
robot = create_simulation_robot(
    model_path="path/to/custom_model.xml",
    enable_viewer=True
)
```

### 添加传感器

```python
# 在MuJoCo模型中添加传感器
# 在simulation_interface.py中添加传感器接口
```

## 总结

MuJoCo仿真集成为Alicia-D SDK v5.6.0提供了强大的仿真能力，使得开发者可以：

1. **无硬件开发** - 在没有真实机械臂的情况下进行开发
2. **快速迭代** - 算法开发和测试更加高效
3. **安全测试** - 避免硬件损坏的风险
4. **教学友好** - 适合教学和培训使用

通过完整的API兼容性，开发者可以无缝地在仿真和真实硬件之间切换，大大提高了开发效率和灵活性。