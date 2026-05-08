# Installation Guide

This guide will walk you through the installation and runtime environment configuration of the Alicia D SDK.

---

## Environment Requirements

- Python 3.6 or higher (Python 3.8 recommended)
- Computer with serial port support (USB to serial chip is integrated in the robot arm)

---

## Installation Steps

### Method 1: Install from PyPI (Recommended)

```bash
pip install alicia_d_sdk
```

This will automatically install all dependencies, including `synria-robocore`.

Starting from `synria-robocore v2.5.0`, Alicia-D SDK uses RoboCore's `cpp` backend by default.
To make the default path work out of the box, ensure the local machine has the required native build prerequisites:
- macOS: Install Xcode Command Line Tools: `xcode-select --install`
- macOS: Install Eigen3: `brew install eigen`
- Linux: Install a C++ compiler and Eigen3 (for example `build-essential` and `libeigen3-dev`)

If the C++ extensions are not built successfully, you can still explicitly pass `backend='numpy'` or `backend='torch'` as a fallback.

### Method 2: Install from Source (Development Mode)

If you need to modify the source code or contribute to development, you can clone from GitHub and install:

```bash
# 1. Clone the project
git clone https://github.com/Synria-Robotics/Alicia-D-SDK.git -b v6.1.0
cd Alicia-D-SDK

# 2. Create Python environment (Conda recommended)
conda create -n alicia python=3.8
conda activate alicia

# 3. Install dependencies and SDK (development mode)
pip install -e .
```

To force-upgrade the local RoboCore installation to the version declared by the SDK, run:

```bash
pip install --upgrade --force-reinstall "synria-robocore @ git+https://github.com/Synria-Robotics/RoboCore.git@v2.5.0"
```

---

## Quick Start

### Basic Usage Example

```python
from alicia_d_sdk import create_robot

# Create robot instance (auto-search for serial port)
robot = create_robot()

# Connect to robot arm
if robot.connect():
    print("Connection successful!")
    
    # Print current state
    robot.print_state()
    
    # Move to initial position
    robot.set_home()
    
    # Disconnect
    robot.disconnect()
else:
    print("Connection failed, please check serial port")
```

### Manually Specify Serial Port

If auto-connection fails, you can manually specify the serial port:

```python
# Linux
robot = create_robot(port="/dev/ttyACM0")

# Windows
robot = create_robot(port="COM3")
```

---

## Hardware Connection

- Connect the robot arm to the computer via USB
- Ensure power is on
- System should automatically recognize serial port devices, such as:
  - Linux: `/dev/ttyACM0`, `/dev/ttyACM1` ...
  - Windows: `COM3`, `COM4` ...

---

## Example Verification

Execute the following commands to test connection and read status:
```bash
cd examples
python3 00_demo_read_version.py   # Read firmware version
python3 03_demo_read_state.py     # Read robot arm state
```

If connection is successful, the terminal will output firmware version, current joint angles, end-effector pose, and gripper state.

---

## ⚠️ Troubleshooting

### Cannot Find Serial Port/Connection Failed
- Check USB cable and power
- Linux users need to ensure they are in the `dialout` user group:
  ```bash
  sudo usermod -a -G dialout $USER
  # Then log out and log back in
  ```
- Run `00_demo_read_version.py` to detect firmware version

### Baud Rate Issues
- New firmware (6.x.x): Default baud rate 1000000
- Old firmware (<6.x.x): May need to use baud rate 921600

Manually specify baud rate:
```python
robot = create_robot(port="/dev/ttyACM0")
```

### Permission Error (Permission denied)
- Try running with sudo or check user serial port permissions
- Linux: Ensure user is in dialout group
- Check if serial port is occupied by another program

### Firmware Version Detection Failed
- Run `00_demo_read_version.py` multiple times
- Check if serial port connection is stable

---

## 📦 Dependency Package Description

Main dependencies (automatically installed with `pip install alicia_d_sdk`):
- `pyserial`: Serial communication
- `numpy`: Numerical computation
- `scipy`: Scientific computing
- `matplotlib`: Plotting
- `pycrc`: CRC checksum
- `synria-robocore`: Kinematics and trajectory planning library
- `synriard`: Robot description files

Note: `synria-robocore v2.5.0` supports `cpp`, `numpy`, and `torch` backends, and Alicia-D SDK now defaults to `cpp`.

---

After successful installation, you can control the robot arm to perform various actions through the `SynriaRobotAPI` interface.

