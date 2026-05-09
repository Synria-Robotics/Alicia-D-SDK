# 安装指南

本指南将引导您完成 Alicia D SDK 的安装与运行环境配置。

---

##  环境要求

- Python 3.6 及以上版本（推荐 Python 3.8）
- 支持串口的计算机（USB 转串口芯片已集成在机械臂）

---

##  安装步骤

### 方法一：从 PyPI 安装（推荐）

```bash
pip install alicia_d_sdk
```

这将自动安装所有依赖包，包括 `synria-robocore`。

自 `synria-robocore v2.5.0` 起，Alicia-D SDK 默认使用 RoboCore 的 `cpp` backend。
如果希望默认路径直接可用，请确保本机具备以下构建条件：
- macOS: 安装 Xcode Command Line Tools: `xcode-select --install`
- macOS: 安装 Eigen3: `brew install eigen`
- Linux: 安装 C++ 编译器与 Eigen3（如 `build-essential` 和 `libeigen3-dev`）

如果 C++ 扩展未成功构建，您仍可在代码中显式传入 `backend='numpy'` 或 `backend='torch'` 作为回退方案。

### 方法二：从源码安装（开发模式）

如果您需要修改源码或参与开发，可以从 GitHub 克隆并安装：

```bash
# 1. 克隆项目
git clone https://github.com/Synria-Robotics/Alicia-D-SDK.git -b v6.1.0
cd Alicia-D-SDK

# 2. 创建 Python 环境（推荐使用 Conda）
conda create -n alicia python=3.8
conda activate alicia

# 3. 安装依赖与 SDK（开发模式）
pip install -e .
```

如需强制升级本地 RoboCore 到 SDK 依赖声明的版本，可执行：

```bash
pip install --upgrade --force-reinstall "synria-robocore @ git+https://github.com/Synria-Robotics/RoboCore.git@v2.5.0"
```

---

##  快速开始

### 基本使用示例

```python
from alicia_d_sdk import create_robot

# 创建机器人实例（自动搜索串口）
robot = create_robot()

# 连接机械臂
if robot.connect():
    print("Connection successful!")
    
    # 打印当前状态
    robot.print_state()
    
    # 移动到初始位置
    robot.set_home()
    
    # 断开连接
    robot.disconnect()
else:
    print("Connection failed, please check serial port")
```

### 手动指定串口

如果自动连接失败，可手动指定串口：

```python
# Linux
robot = create_robot(port="/dev/ttyACM0")

# Windows
robot = create_robot(port="COM3")
```

---

##  连接硬件

- 将机械臂通过 USB 连接到计算机
- 确保电源打开
- 系统应自动识别串口设备，如：
  - Linux: `/dev/ttyACM0`, `/dev/ttyACM1` ...
  - Windows: `COM3`, `COM4` ...

---

##  示例验证

执行以下命令测试连接和读取状态：
```bash
cd examples
python3 00_demo_read_version.py   # 读取固件版本
python3 03_demo_read_state.py     # 读取机械臂状态
```

若连接成功，终端将输出固件版本、当前关节角度、末端位姿与夹爪状态。

---

## ⚠️ 故障排查

### 找不到串口/连接失败
- 检查 USB 线与电源
- Linux 用户需确保在 `dialout` 用户组中：
  ```bash
  sudo usermod -a -G dialout $USER
  # 然后重新登录
  ```
- 运行 `00_demo_read_version.py` 检测固件版本



手动指定波特率：
```python
robot = create_robot(port="/dev/ttyACM0")
```

### 权限错误 (Permission denied)
- 可尝试以 sudo 运行或检查用户串口权限
- Linux: 确保用户在 dialout 组中
- 检查串口是否被其他程序占用

### 固件版本检测失败
- 多次运行 `00_demo_read_version.py`
- 检查串口连接是否稳定

---

## 📦 依赖包说明

主要依赖（使用 `pip install alicia_d_sdk` 时会自动安装）：
- `pyserial`: 串口通信
- `numpy`: 数值计算
- `scipy`: 科学计算
- `matplotlib`: 绘图
- `pycrc`: CRC校验
- `synria-robocore`: 运动学和轨迹规划库
- `synriard`: 机器人描述文件

说明：`synria-robocore v2.5.0` 默认支持 `cpp`、`numpy`、`torch` 三种后端，Alicia-D SDK 默认选择 `cpp`。

---

安装成功后，即可通过 `SynriaRobotAPI` 接口控制机械臂完成各种动作。