# 例程代码说明

`examples/` 目录包含了多个演示脚本，用于展示如何使用 Alicia-D SDK 控制机械臂。

---

## 📁 文件结构

```
examples/
├── 00_demo_read_version.py          # 读取版本号
├── 01_torque_switch.py               # 扭矩控制
├── 02_demo_set_new_zero_configuration.py  # 设置新零点
├── 03_demo_read_state.py            # 读取状态
├── 04_demo_move_gripper.py          # 夹爪控制
├── 05_demo_move_joint.py            # 关节空间运动
├── 06_demo_forward_kinematics.py    # 正向运动学
├── 07_demo_inverse_kinematics.py    # 逆向运动学
├── 08_demo_drag_teaching.py         # 拖动示教
├── 09_demo_joint_traj.py            # 关节空间轨迹规划
├── 10_demo_cartesian_traj.py        # 笛卡尔空间轨迹规划
├── 11_benchmark_read_joints.py      # 关节读取性能测试
└── 12_utmostFPS.py                  # 最大帧率测试
```

## 📜 例程列表

### 0. `00_demo_read_version.py`
**读取机械臂固件版本号**
- 在使用前务必先运行此脚本检测固件版本
- 使用 `get_robot_state("version")` 获取版本信息
- 使用 `get_robot_state("gripper_type")` 获取夹爪类型
- 如果显示超时或没有版本号输出，可能需要调整波特率

**使用方式：**
```bash
python 00_demo_read_version.py
```

---

### 1. `01_torque_switch.py`
切换机械臂所有关节的力矩状态（上电/掉电）。调电后可以自由拖动机械臂。

**参数说明：**
- `--port`: 串口端口（可选）

**功能说明：**
- 先关力矩后开力矩
- 关闭扭矩后机械臂可以手动拖动
- 示教完成后重新开启扭矩

**注意事项：**
- 关闭扭矩前请手动托住机械臂以免其突然掉落
- 示教完成后务必重新开启扭矩

**使用方式：**
```bash
python 01_torque_switch.py
```

---

### 2. `02_demo_set_new_zero_configuration.py`
将机械臂当前位置设置为新的零点。**此操作不可逆，请谨慎使用。**

**参数说明：**
- `--port`: 串口端口（可选）

**适用场景：**
- 机械臂首次使用或长时间未使用后
- 关节角度出现偏差时
- 需要重新建立零点参考时

**使用方式：**
```bash
python 02_demo_set_new_zero_configuration.py
```

---

### 3. `03_demo_read_state.py`
持续读取并打印机械臂的关节角度、末端姿态和夹爪状态。支持单次或持续打印模式。

**参数说明：**
- `--port`: 串口端口（可选）
- `--gripper_type`: 夹爪型号，默认 `50mm`
- `--format`: 角度显示格式，可选 `rad`（弧度）或 `deg`（角度），默认 `deg`
- `--single`: 单次打印状态，默认持续打印
- `--fps`: 持续模式的帧率（Hz），默认 `30.0`

**使用场景：**
- 调试和故障排查
- 实时监控机械臂状态
- 验证控制指令执行效果

**使用方式：**
```bash
# 持续打印状态（按 Ctrl+C 停止）
python 03_demo_read_state.py --gripper_type 50mm --fps 30

# 单次打印状态
python 03_demo_read_state.py --single
```

---

### 4. `04_demo_move_gripper.py`
夹爪控制：控制夹爪张开或闭合到指定角度。夹爪值范围为 0-1000（0为完全闭合，1000为完全张开）。

**参数说明：**
- `--port`: 串口端口（可选）

**功能说明：**
- 演示自动执行：完全张开 → 完全闭合 → 半开
- 使用 `set_robot_state(gripper_value=...)` 控制夹爪
- 使用 `get_robot_state("gripper")` 读取当前夹爪值
- 支持等待夹爪运动完成

**使用方式：**
```bash
python 04_demo_move_gripper.py
```

---

### 5. `05_demo_move_joint.py`
使用关节空间运动控制机械臂移动到设定角度。支持度数和弧度输入，自动进行关节角度插值。

**参数说明：**
- `--port`: 串口端口（可选）
- `--speed_deg_s`: 关节运动速度（度/秒），默认 10，范围 5-400

**功能说明：**
- 演示自动执行：回零 → 移动到目标角度 → 回零
- 使用统一的关节和夹爪目标接口 `set_robot_state()`
- 支持 `wait_for_completion=True` 等待运动完成

**使用方式：**
```bash
python 05_demo_move_joint.py --speed_deg_s 10
```

---

---

### 6. `06_demo_forward_kinematics.py`
正运动学求解。根据当前关节角度计算末端执行器的位姿，显示位置、旋转矩阵、欧拉角、四元数等多种表示形式。

**参数说明：**
- `--port`: 串口端口（可选）
- `--version`: 机器人版本，默认 `v5_6`
- `--variant`: 机器人变体，可选 `gripper_50mm`、`gripper_100mm`、`leader_ur`、`leader`、`vertical_50mm`，默认 `gripper_50mm`
- `--model_format`: 模型格式，可选 `urdf` 或 `mjcf`，默认 `urdf`
- `--base_link`: 基座链路名称，默认 `base_link`
- `--end_link`: 末端执行器链路名称，默认 `tool0`

**功能说明：**
- 使用 RoboCore 库的机器人模型
- 显示机器人模型信息和运动学链
- 返回并显示：位置、旋转矩阵、欧拉角（弧度/角度）、四元数、齐次变换矩阵
- 注意：四元数 q 和 -q 表示相同的旋转

**使用方式：**
```bash
python 06_demo_forward_kinematics.py
```

---

### 7. `07_demo_inverse_kinematics.py`
演示逆向运动学求解：根据给定的末端目标位姿，计算并可选地执行关节角度。支持多种IK求解方法和多起点优化。

**参数说明：**
- `--port`: 串口端口（可选）
- `--speed_deg_s`: 关节运动速度（度/秒），默认 10，范围 5-400
- `--gripper_type`: 夹爪类型，默认 `50mm`
- `--base_link`: 基座链路名称，默认 `base_link`
- `--end_link`: 末端执行器链路名称，默认 `tool0`
- `--end-pose`: 目标位姿（7个浮点数：px py pz qx qy qz qw），默认值已预设
- `--method`: IK方法，可选 `dls`（阻尼最小二乘）、`pinv`（伪逆）、`transpose`（雅可比转置），默认 `dls`
- `--max-iters`: 最大迭代次数，默认 500
- `--pos-tol`: 位置容差（米），默认 1e-3
- `--ori-tol`: 姿态容差（弧度），默认 1e-3
- `--num-inits`: 初始猜测数量，默认 10
- `--init-strategy`: 初始猜测策略，可选 `zero`、`random`、`sobol`、`latin`、`center`、`uniform`、`current`，默认 `current`
- `--init-scale`: 关节限制缩放因子（0.0 到 1.0），默认 1.0
- `--seed`: 随机种子（可选）
- `--backend`: 计算后端，可选 `cpp`、`numpy` 或 `torch`，默认 `cpp`
- `--execute`: 执行移动到求解的位置
- `--force-execute`: 强制执行移动，即使求解失败

**功能说明：**
- 显示详细的求解结果（成功/失败、迭代次数、位置误差、姿态误差）
- 如果执行移动，会自动返回初始位置
- 支持多起点优化提高成功率

**使用方式：**
```bash
# 仅计算逆解，不执行动作
python 07_demo_inverse_kinematics.py

# 计算逆解并控制机械臂移动到目标位姿
python 07_demo_inverse_kinematics.py --execute --speed_deg_s 10

# 使用多起点优化提高成功率
python 07_demo_inverse_kinematics.py --execute --num-inits 10
```

---

### 8. `08_demo_drag_teaching.py`
拖动示教演示：通过手动拖动机械臂来录制一系列轨迹点，并可以回放。支持手动插值、自动快速和仅回放三种模式。

**参数说明：**
- `--port`: 串口端口（可选）
- `--speed_deg_s`: 关节运动速度（度/秒），默认 15，范围 10-80
- `--mode`: 拖动示教模式，可选 `manual`（手动插值）、`auto`（自动快速）或 `replay_only`（仅回放），默认 `auto`
- `--sample-hz`: 自动模式采样频率，默认 200.0 Hz
- `--save-motion`: 动作名称（录制模式：新动作名；回放模式：已有动作名），默认 `my_demo`
- `--list-motions`: 列出所有可用的动作并退出

**功能说明：**
- 关闭扭矩进入示教模式
- 手动拖动机械臂记录轨迹
- 支持手动模式（记录关键点）和自动模式（连续采样）
- 回放记录的轨迹

**使用方式：**
```bash
# 列出所有可用的动作
python 08_demo_drag_teaching.py --list-motions

# 自动模式录制名为 "my_demo" 的轨迹
python 08_demo_drag_teaching.py --mode auto --save-motion my_demo

# 手动模式录制关键点轨迹
python 08_demo_drag_teaching.py --mode manual --save-motion key_points

# 回放已有轨迹 "my_demo"
python 08_demo_drag_teaching.py --mode replay_only --save-motion my_demo
```

---

### 9. `09_demo_joint_traj.py`
**关节空间轨迹规划与执行**

演示如何使用关节空间轨迹规划生成平滑的关节轨迹，并通过多个路径点执行。

**参数说明：**
- `--port`: 串口端口（可选）
- `--gripper_type`: 夹爪类型，默认 `50mm`
- `--base_link`: 基座链路名称，默认 `base_link`
- `--end_link`: 末端执行器链路名称，默认 `tool0`
- `--no-record`: 禁用记录模式
- `--save-file`: 保存记录的路径点文件路径
- `--waypoints-file`: 从JSON文件加载路径点
- `--num-waypoints`: 随机生成的路径点数量，默认 6
- `--planner`: 规划器类型，可选 `b_spline` 或 `multi_segment`，默认 `b_spline`
- `--duration`: 轨迹持续时间（B-Spline），默认 2.0 秒
- `--num-points`: 轨迹点数（B-Spline），默认 800
- `--bspline-degree`: B-Spline 度数，可选 3 或 5，默认 5
- `--speed-deg-s`: 关节运动速度（度/秒），默认 20
- `--plot`: 禁用轨迹可视化

**功能说明：**
- 支持手动记录路径点或从文件加载
- 使用 B-Spline 或 Multi-Segment 规划器生成平滑轨迹
- 支持夹爪轨迹插值
- 可视化轨迹（可选）

**使用方式：**
```bash
# 使用默认参数运行
python 09_demo_joint_traj.py

# 从文件加载路径点
python 09_demo_joint_traj.py --waypoints-file waypoints.json

# 使用 Multi-Segment 规划器
python 09_demo_joint_traj.py --planner multi_segment
```

---

### 10. `10_demo_cartesian_traj.py`
**笛卡尔空间轨迹规划与执行**

演示如何使用笛卡尔空间样条轨迹规划生成平滑的末端执行器轨迹，并通过逆运动学求解执行。

**参数说明：**
- `--port`: 串口端口（可选）
- `--gripper_type`: 夹爪类型，默认 `50mm`
- `--base_link`: 基座链路名称，默认 `base_link`
- `--end_link`: 末端执行器链路名称，默认 `tool0`
- `--no-record`: 禁用记录模式
- `--save-file`: 保存记录的路径点文件路径
- `--waypoints-file`: 从JSON文件加载路径点
- `--num-waypoints`: 随机生成的路径点数量，默认 2
- `--duration`: 轨迹持续时间（秒），默认 1.0
- `--num-points`: 轨迹点数，默认 10
- `--method`: IK方法，可选 `dls`、`pinv`、`transpose`，默认 `dls`
- `--max-iters`: 最大IK迭代次数，默认 100
- `--pos-tol`: 位置容差（米），默认 1e-2
- `--ori-tol`: 姿态容差（弧度），默认 1e-2
- `--num-inits`: 初始猜测数量，默认 5
- `--init-strategy`: 初始猜测策略，默认 `current`
- `--speed-deg-s`: 关节运动速度（度/秒），默认 20
- `--plot`: 禁用轨迹可视化

**功能说明：**
- 支持手动记录笛卡尔路径点或从文件加载
- 使用样条曲线生成平滑的笛卡尔轨迹
- 批量求解逆运动学（确保连续性）
- 验证路径点是否被准确通过
- 可视化轨迹和IK结果（可选）

**使用方式：**
```bash
# 使用默认参数运行
python 10_demo_cartesian_traj.py

# 从文件加载路径点
python 10_demo_cartesian_traj.py --waypoints-file cartesian_waypoints.json

# 增加轨迹点数以提高平滑度
python 10_demo_cartesian_traj.py --num-points 100
```

---

### 11. `11_benchmark_read_joints.py`
**关节读取性能测试**

测试关节角度读取的API调用频率和实际数据更新频率。

**参数说明：**
- `--port`: 串口端口（可选）
- `--gripper_type`: 夹爪类型，默认 `50mm`
- `--duration`: 测试持续时间（秒），默认 5.0
- `--fast`: 启用快速模式（设置更新间隔为1ms）

**功能说明：**
- 测试API读取频率（从Python内存读取缓存数据的速度）
- 测试数据更新频率（从机器人实际接收新数据的速率）
- 显示串口统计信息（处理的帧数、丢弃的帧数等）

**使用方式：**
```bash
# 基本测试（5秒）
python 11_benchmark_read_joints.py

# 快速模式测试
python 11_benchmark_read_joints.py --fast --duration 10
```

---

### 12. `12_utmostFPS.py`
**最大帧率测试**

测试串口通信的最大发送和接收帧率。

**参数说明：**
- `--port`: 串口端口（必需，例如：/dev/ttyUSB0 或 COM3）
- `--baudrate`: 波特率，默认 1000000
- `--timeout`: 串口读取超时（秒），默认 0.015
- `--test-timeout`: 测试持续时间（秒），默认 300.0

**功能说明：**
- 测试串口通信的极限性能
- 显示发送帧率、接收帧率和同步率
- 适用于性能优化和硬件测试

**使用方式：**
```bash
# Linux/Ubuntu
python 12_utmostFPS.py --port /dev/ttyACM0

# Windows
python 12_utmostFPS.py --port COM3

# macOS
python 12_utmostFPS.py --port /dev/cu.wchusbserial5B140413941

# 自定义设置
python 12_utmostFPS.py --port /dev/ttyUSB0 --baudrate 2000000 --test-timeout 60
```

---

## ⚙️ 常见参数调整场景

### 运动控制参数调整：

*新固件（6.1.0及以上）*

- **速度过快**：降低 `speed_deg_s`（范围：5-400度/秒）
- **运动不流畅**：增加 `num_points`（轨迹插值点数）
- **移动时间过长**：减少 `move_duration`（每个路径点的移动时间）

### IK 求解参数调整：
- **求解失败**：尝试不同 `method`（`dls`、`pinv`、`transpose`），增加 `multi_start`（建议 5-10）
- **局部最优**：使用 `use_random_init=True` 或增加 `multi_start`
- **精度要求高**：降低 `tolerance` 到 1e-5 或更小，增加 `max_iters`
- **速度要求高**：使用 `method='pinv'` 或 `method='transpose'`

### 拖动示教参数调整：
- **采样频率**：调整 `--sample-hz`（默认 300.0 Hz），更高频率记录更详细但文件更大
- **模式选择**：`manual` 模式适合记录关键点，`auto` 模式适合连续轨迹

---
