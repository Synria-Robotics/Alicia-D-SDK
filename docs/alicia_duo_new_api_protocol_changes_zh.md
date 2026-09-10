# Alicia-D 力控示教臂新增接口与协议变更说明

> 文档状态：冻结前候选稿  
> 整理日期：2026-09-01  
> 对比基线：官网当前公开的 Alicia-D v6.1.x 固件 / Alicia-D SDK v6.1.0 说明  
> 目标对象：Alicia-D 力控示教臂（D 端）及配套 Alicia-M（M 端）

## 1. 文档目的与范围

本文整理力控示教臂相对于上一版公开 SDK 和通讯协议新增或发生语义扩展的内容，供以下工作使用：

1. 固件与 SDK 冻结审查；
2. 客户 SDK API 文档编写；
3. [Alicia-D 系列官网文档](https://docs.sparklingrobo.com/docs/alicia-d-series)更新；
4. D/M 配套固件兼容性检查。

官网现有[上下位机通讯协议](https://docs.sparklingrobo.com/docs/alicia-d-series/protocol/doc_00_intro)已经公开 `0x01`、`0x03`、`0x04`、`0x05`、`0x06` 和 `0xFE` 指令。此次不改变帧头、帧尾、波特率和校验算法，而是在原 `0x05`、`0x06` 指令族下增加功能码。

本文将协议分为两层：

- **客户公开协议**：上位机通过 D 端用户串口调用，可由 Python SDK 封装并写入官网。
- **D-M 内部协议**：仅供配套 D/M 固件遥操使用，不属于客户稳定 API，不建议写入官网公开协议页。

## 2. 变更总览

| 类别 | 新增或扩展项 | 协议 | SDK API | 建议公开 |
|---|---|---|---|---|
| 控制模式 | 查询当前已应用模式 | `0x06/0x24` | `get_control_mode()` | 是 |
| 控制模式 | 设置位置/电流模式 | `0x05/0x01` | `set_control_mode()` | 是 |
| 遥操 | 进入/退出遥操 | 复用模式接口 | `get_teleoperation_state()`、`set_teleoperation_enabled()` | 是 |
| 力反馈 | 设置力反馈请求 | `0x06/0x20` | `set_force_feedback_enabled()` | 是 |
| 力反馈 | 查询请求、实际生效与抑制原因 | `0x06/0x20` | `get_force_feedback_state()` | 是 |
| 六轴诊断 | 六轴远端力矩与电流只读快照 | `0x06/0x24` | 当前由模式查询内部使用 | 可选高级接口 |
| 扭矩控制 | HLS 舵机上的实现适配 | 沿用 `0x05/0x00` | 沿用 `torque_control()` | 说明行为变化 |
| 机械模型 | 力控示教臂本地 URDF | 无串口变化 | `create_robot(variant="alicia_duo")` | 是 |
| 低速控制 | 速度寄存器保留单计数分辨率 | 沿用 `0x06/0x03` | `speed_deg_s` 最小约 `0.09 deg/s` | 是 |

## 3. 不变的基础帧格式

用户串口继续使用 `1,000,000 baud`，帧格式如下：

| 偏移 | 字段 | 长度 | 说明 |
|---:|---|---:|---|
| 0 | 帧头 | 1 | 固定 `0xAA` |
| 1 | 指令 ID | 1 | 例如 `0x05`、`0x06` |
| 2 | 功能码 | 1 | 指令下的子功能 |
| 3 | 数据长度 | 1 | DATA 字节数 |
| 4..N | DATA | 可变 | 各功能载荷 |
| N+1 | 校验 | 1 | 对“指令 ID 至 DATA 末尾”计算 CRC32，取低 8 bit |
| N+2 | 帧尾 | 1 | 固定 `0xFF` |

多字节整数除非另有说明均使用小端序。

## 4. 新增公共控制模式协议

### 4.1 模式定义

公共 SDK 只开放以下两种模式，不暴露固件内部的 `STANDARD/SYNC` 枚举：

| 协议值 | SDK 名称 | 舵机工作模式 | 主要用途 |
|---:|---|---|---|
| `0x00` | `position` | 位置模式 | 原 SDK 位置保持、关节控制和轨迹控制 |
| `0x01` | `current` | 电流模式 | D-M 遥操与力反馈 |

力控示教臂上电默认进入 `position`，扭矩默认关闭。**模式切换与扭矩开关是两个独立动作**：切回 `position` 不代表自动锁定，用户仍可手动调整；锁定由实体按键或 `torque_control("on")` 完成。

### 4.2 设置模式：`0x05/0x01`

请求帧：

```text
AA 05 01 01 MODE CRC FF
```

| DATA 偏移 | 字段 | 说明 |
|---:|---|---|
| 0 | `MODE` | `0x00=position`，`0x01=current` |

示例：

```text
切换 position：AA 05 01 01 00 58 FF
切换 current ：AA 05 01 01 01 CE FF
```

响应帧固定为 9 字节：

```text
AA 05 01 03 VERSION REQUESTED_MODE RESULT CRC FF
```

| DATA 偏移 | 字段 | 说明 |
|---:|---|---|
| 0 | `VERSION` | 当前为 `0x01` |
| 1 | `REQUESTED_MODE` | 原样返回请求模式 |
| 2 | `RESULT` | `0=请求已接受`，`1=模式值无效`，`2=设备不支持或请求未入队` |

ACK 仅说明 D 端状态机接受了请求，不表示舵机已经完成物理模式切换。SDK 收到 ACK 后还会轮询 `0x06/0x24`，只有读到目标模式才返回 `True`。

固件内部按安全顺序执行：关闭扭矩、写入安全目标、切换工作模式、恢复所需配置，并根据当前扭矩请求决定是否重新使能。客户不得直接写舵机工作模式寄存器。

### 4.3 查询模式与六轴电流诊断：`0x06/0x24`

请求帧：

```text
AA 06 24 01 FE A6 FF
```

响应总长 58 字节，DATA 长度为 52：

| DATA 偏移 | 长度 | 字段 | 类型/单位 |
|---:|---:|---|---|
| 0 | 1 | payload version | 当前 `0x01` |
| 1 | 1 | applied mode | `0=position`，`1=current` |
| 2 | 1 | blocked mask | bit1=J2，bit2=J3 |
| 3 | 1 | feedback valid mask | bit0..bit5 对应 J1..J6 |
| 4 | 48 | axes | 六轴，每轴 8 字节 |

每轴 8 字节均为 little-endian `int16`：

| 轴内偏移 | 长度 | 字段 | 单位 |
|---:|---:|---|---|
| 0 | 2 | 远端残余力矩目标 | `0.001 N*m` |
| 2 | 2 | 请求电流 | `0.001 A` |
| 4 | 2 | 实际输出电流 | `0.001 A` |
| 6 | 2 | 舵机测量电流 | `0.001 A` |

该接口只读，不会切换模式、写寄存器或改变扭矩状态。官网基础 API 可只说明“查询当前模式”；完整六轴诊断字段可放在高级诊断章节。

## 5. 新增遥操与力反馈协议

### 5.1 状态关系

本版明确区分三个概念：

1. **遥操模式**：D 端处于 `current`；
2. **力反馈请求**：用户希望叠加来自 M 端的残余力矩；
3. **力反馈实际生效**：请求已开启，同时 D-M 链路有效、力矩样本新鲜且无硬件故障。

因此 `requested=True` 不保证 `effective=True`。客户端应读取抑制原因，不应只根据设置命令的返回值判断力反馈已经作用于机械臂。

### 5.2 设置或查询：`0x06/0x20`

请求帧：

```text
AA 06 20 01 ACTION CRC FF
```

| `ACTION` | 功能 | 完整示例 |
|---:|---|---|
| `0x00` | 关闭力反馈请求 | `AA 06 20 01 00 61 FF` |
| `0x01` | 开启力反馈请求 | `AA 06 20 01 01 F7 FF` |
| `0xFE` | 只读查询，不改变状态 | `AA 06 20 01 FE 7A FF` |

无论设置还是查询，D 端均返回当前状态。当前响应 DATA 版本为 `0x02`，长度为 10 字节：

```text
AA 06 20 0A
02 REQUESTED EFFECTIVE INHIBIT_MASK SYNC_ACTIVE TORQUE_ENABLED
TORQUE_REQUESTED TRANSITION GRIP_ENABLED_RAW REQUESTED_MODE
CRC FF
```

| DATA 偏移 | 字段 | 说明 |
|---:|---|---|
| 0 | `VERSION` | 当前 `0x02` |
| 1 | `REQUESTED` | 力反馈请求是否开启 |
| 2 | `EFFECTIVE` | 力反馈是否实际生效 |
| 3 | `INHIBIT_MASK` | 抑制原因位掩码 |
| 4 | `SYNC_ACTIVE` | 是否处于 D-M 遥操模式 |
| 5 | `TORQUE_ENABLED` | D 端控制器记录的扭矩实际使能状态 |
| 6 | `TORQUE_REQUESTED` | 当前扭矩请求状态 |
| 7 | `TRANSITION` | 固件内部模式切换阶段，只建议用于诊断 |
| 8 | `GRIP_ENABLED_RAW` | 握把/按键原始使能状态，只建议用于诊断 |
| 9 | `REQUESTED_MODE` | 请求模式，`0=position`，`1=current` |

`INHIBIT_MASK` 当前定义：

| bit | 值 | 含义 |
|---:|---:|---|
| 0 | `0x01` | 未进入遥操 |
| 1 | `0x02` | 预留；当前固件不置位 |
| 2 | `0x04` | D-M 链路超时或远端力矩样本超过 30 ms |
| 3 | `0x08` | 硬件故障 |
| 4 | `0x10` | 操作或协议不支持 |
| 5..7 | - | 预留 |

### 5.3 退出遥操的规定行为

`set_teleoperation_enabled(False)` 执行以下逻辑：

1. 关闭力反馈请求；
2. 切回 `position`；
3. 等待并确认模式已应用；
4. 保持扭矩关闭，使机械臂仍可手动调整；
5. 后续由实体锁定键或独立扭矩命令决定是否进入位置保持。

这条规则用于避免退出力反馈后机械臂意外锁住，也避免把“模式恢复”与“位置锁定”混成一个接口。

## 6. 新增 Python SDK API

以下方法位于 `SynriaRobotAPI`。

### 6.1 `get_control_mode`

```python
get_control_mode(timeout: float = 1.0) -> Optional[str]
```

返回固件已应用的 `"position"`、`"current"`，通信超时返回 `None`。

### 6.2 `set_control_mode`

```python
set_control_mode(mode: str, timeout: float = 2.0) -> bool
```

只接受 `"position"` 或 `"current"`。方法同时校验设置 ACK 和模式回读，只有目标模式已经应用才返回 `True`。

### 6.3 `get_teleoperation_state`

```python
get_teleoperation_state(timeout: float = 1.0) -> dict
```

返回：

```python
{
    "enabled": True,
    "active": True,
    "mode": "current",
}
```

当前实现中，`enabled/active` 表示已经进入电流遥操模式，不代表力反馈一定有效。

### 6.4 `set_teleoperation_enabled`

```python
set_teleoperation_enabled(enabled: bool, timeout: float = 2.0) -> bool
```

- `True`：切换到 `current`，但不自动开启力反馈；
- `False`：先关闭力反馈，再切回 `position`，且不自动打开扭矩。

### 6.5 `get_force_feedback_state`

```python
get_force_feedback_state(timeout: float = 1.0) -> Optional[dict]
```

主要稳定字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `version` | `int` | 状态 payload 版本 |
| `requested` | `bool` | 力反馈请求 |
| `effective` | `bool` | 力反馈实际生效 |
| `inhibit_mask` | `int` | 抑制原因位掩码 |
| `inhibit_reasons` | `list[str]` | SDK 解析后的原因列表 |
| `inhibit_reason` | `str` | 便于日志显示的原因字符串 |
| `sync_active` | `bool` | 遥操模式是否生效 |
| `torque_enabled` | `bool` | 扭矩实际使能状态 |
| `torque_requested` | `bool` | 扭矩请求状态 |
| `requested_mode` | `str` | `position/current` |

`transition` 和 `grip_enabled_raw` 属于诊断字段，不建议作为客户业务逻辑的长期依赖。

### 6.6 `set_force_feedback_enabled`

```python
set_force_feedback_enabled(enabled: bool, timeout: float = 2.0) -> bool
```

该方法幂等设置力反馈请求并轮询状态，确认 `requested` 与目标值一致后返回。它不会直接写舵机电流，也不会代替遥操模式切换。

### 6.7 推荐调用顺序

```python
robot = alicia_d_sdk.create_robot(port="COM11")

# 进入遥操，再显式请求力反馈。
assert robot.set_teleoperation_enabled(True)
assert robot.set_force_feedback_enabled(True)

state = robot.get_force_feedback_state()
if not state or not state["effective"]:
    reason = state["inhibit_reason"] if state else "通信超时"
    raise RuntimeError(f"力反馈未生效：{reason}")

# 收尾：关闭力反馈并回到可手动调整的位置模式。
assert robot.set_teleoperation_enabled(False)
```

## 7. 沿用接口的行为变化

### 7.1 扭矩开关 `0x05/0x00`

协议编号与 SDK 方法不变：

```python
robot.torque_control("on")
robot.torque_control("off")
```

对 HLS 力控示教臂，命令现在进入固件控制状态机，由状态机安全地下发六轴扭矩开关；不再建议客户直接依据底层寄存器写入结果判断模式。

位置模式下：

- `on`：在当前姿态进入位置保持；
- `off`：释放位置保持，可手动拖动。

电流遥操模式下，扭矩状态还受遥操、力反馈状态与硬件保护共同约束。因此客户应通过公开状态接口判断实际状态。

### 7.2 关节速度分辨率

`0x06/0x03` 数据结构不变。SDK 原先将关节速度向 50 个寄存器计数取整，软件最小速度约为 `4.39 deg/s`；本版保留单计数分辨率，最小约为：

```text
360 / 4096 = 0.087890625 deg/s
```

因此 `speed_deg_s=1` 可以按约 1 deg/s 下发，不再被放大到约 4.39 deg/s。

## 8. 新增示例程序

| Demo | 文件 | 作用 |
|---:|---|---|
| 13 | `examples/13_demo_control_mode.py` | 安全验证 `position/current` 设置、ACK 与模式回读 |
| 14 | `examples/14_demo_force_feedback_control.py` | 验证进入遥操、开启力反馈、读取实际生效/抑制原因、退出遥操并恢复位置模式 |

Demo14 是接口验收程序，不是遥操数据转发器。D 与 M 之间的实时位置和力矩通信仍通过直接 485 链路完成，上位机只负责发出模式/功能请求和读取状态。

## 9. 力控示教臂模型接口变化

SDK 新增内置模型：

```text
alicia_d_sdk/models/Alicia_duo/urdf/Alicia-duo.urdf
```

默认调用：

```python
robot = alicia_d_sdk.create_robot(port="COM11")
# 等价于 variant="alicia_duo"
```

主要变化：

- 使用力控示教臂实际结构、零位和关节限制；
- J2 轴方向和范围与实体装配一致；
- J3 轴方向和范围与实体装配一致；
- 增加固定 `tool0`，供正逆运动学统一选择末端；
- 旧 `leader`、`leader_ur`、`gripper_50mm` 等 variant 仍可显式选择。

URDF 影响正运动学、逆运动学、笛卡尔轨迹和限位检查，但不改变串口中的六轴位置原始值格式。

## 10. D-M 内部协议附录（不对客户公开）

D-M 实时力矩响应帧固定 24 字节，当前版本 `0x01`：

| 偏移 | 长度 | 字段 | 说明 |
|---:|---:|---|---|
| 0 | 1 | header | `0xAB` |
| 1 | 1 | type | `0x54` |
| 2 | 1 | version | `0x01` |
| 3 | 1 | sequence | 低 6 bit 有效 |
| 4 | 1 | valid mask | bit0..bit5 对应 J1..J6 |
| 5 | 1 | flags | 状态位 |
| 6 | 12 | residual torque | 六个 little-endian `int16`，单位 `0.01 N*m` |
| 18 | 2 | sample age | little-endian `uint16`，单位 ms |
| 20 | 2 | reserved | 必须为 0 |
| 22 | 1 | CRC | 覆盖前 22 字节 |
| 23 | 1 | tail | `0xFF` |

`flags`：

| bit | 含义 |
|---:|---|
| 0 | 重力计算有效 |
| 1 | M 端同步会话有效 |
| 2 | J2 阻塞/保护状态 |
| 3 | 预留，必须为 0；原 J5 试验位已删除 |
| 4 | J3 阻塞状态 |
| 5..7 | 预留 |

D 端只接受 CRC 正确、序号滞后不超过 4、未重复且样本年龄不超过 30 ms 的响应。该协议与 M 端阻塞识别、重力补偿和热保护实现绑定，客户 SDK 不应构造或解析此帧。

## 11. 不应写入客户文档的试验接口

以下接口属于台架调试、已删除方案或未冻结能力，不应加入官网和公开 SDK：

| 协议/能力 | 处理建议 |
|---|---|
| `0x03/0x01` 单轴调零 | 不公开，继续使用原整臂调零 `0x03/0x00` |
| `0x06/0x23` ID2 台架诊断 | 不公开 |
| `0x06/0x25` J5 物理寄存器诊断 | 从正式 SDK 移除或改为内部工具 |
| `0x06/0x26` 人工阻塞注入 | 不公开 |
| 临时 `0x27` 按键/锁定监视 | 不公开 |
| D 端本地重力补偿模型 | 未完成，不作为正式能力 |
| J5 阻塞标志 | 已从正式协议规划中删除 |
| PV 机械阻塞识别与参数 | 未采用，不作为正式能力 |
| 原始电流写入和保护阈值写入 | 不向客户开放 |

## 12. 兼容性与升级要求

1. 新 SDK 连接旧固件时，`0x05/0x01`、`0x06/0x20`、`0x06/0x24` 可能无响应；调用方必须把超时视为“不支持”，不能假定设置成功。
2. 旧 SDK 连接新固件时，原位置读取、温度、速度、扭矩、调零及 `0x06/0x03` 位置控制协议保持兼容。
3. `position/current` 只在 HLS 力控示教臂上开放；非 HLS 或型号识别失败时固件应拒绝进入电流模式。
4. D/M 固件必须配套发布。只升级单端可能导致遥操可进入但力反馈因链路协议不匹配而被抑制。
5. 模式设置 ACK 与模式实际完成必须分开处理，SDK 不得收到 ACK 后立即假设模式已切换。
6. 退出遥操后默认扭矩关闭，这是力控示教臂的安全交互约定，与旧版“进入位置模式即锁定”不同。

## 13. 冻结前待确认项

以下内容在发布前需要做最后一次协议审查：

1. **力反馈状态 DATA[5] 命名**：固件实际发送 `torque_enabled`。SDK 当前还保留了同值别名 `mechanical_lock`，正式版应删除该别名，避免客户误解为机械锁状态。
2. **`0x06/0x24` 公开层级**：建议官网基础章节只公开模式值和反馈有效掩码，六轴力矩/电流字段放入“高级诊断”。
3. **诊断字段稳定性**：`transition`、`grip_enabled_raw` 应明确标记为诊断字段，不承诺长期枚举值不变。
4. **版本号**：SDK 源码当前处于 `6.1.0rc5` 候选状态，正式发布时需统一 `pyproject.toml`、包内 `__version__`、固件版本和官网升级表。
5. **固件能力识别**：当前没有独立 `get_capabilities()`。正式 SDK 可根据版本或协议查询超时判断能力，但官网不能暗示旧固件支持新接口。

## 14. 官网更新建议

### 14.1 通讯协议页

在现有[通讯协议页](https://docs.sparklingrobo.com/docs/alicia-d-series/protocol/doc_00_intro)增加：

1. `0x05/0x01` 设置控制模式；
2. `0x06/0x20` 力反馈设置与状态查询；
3. `0x06/0x24` 控制模式与六轴电流诊断；
4. “模式切换不等于扭矩开关”的醒目说明；
5. 旧固件无响应时的兼容处理。

### 14.2 示教臂 SDK 页

在[示教臂文档](https://docs.sparklingrobo.com/docs/alicia-d-series/leader/doc_00_intro)增加：

1. 六个新 SDK 方法的签名、返回值和示例；
2. Demo13、Demo14 的用途与安全前置条件；
3. 遥操、力反馈请求、力反馈实际生效三者的区别；
4. 退出遥操回到 `position + torque off` 的行为；
5. `alicia_duo` 模型及旧 variant 的兼容说明。

### 14.3 产品版本页

正式发布后更新固件/SDK版本对应关系，并注明：

- 力控示教臂需要配套 D/M 固件；
- 新控制模式和力反馈 API 的最低固件版本；
- 新 SDK 的最低 Python 版本与安装命令；
- URDF 模型名称和适用结构版本。

## 15. 建议的发布验收

1. Demo01：位置模式下扭矩开启/关闭和位置保持；
2. Demo03：六轴状态读取及新 URDF 加载；
3. Demo05：六轴位置运动和 1 deg/s 低速控制；
4. Demo06：新模型正运动学；
5. Demo13：`position -> current -> position`，每次均确认回读；
6. Demo14：遥操开启、力反馈请求、实际生效、抑制原因和安全退出；
7. D-M 直连：断线、超时、恢复和错误配套固件测试；
8. 回归旧协议：`0x01`、`0x03`、`0x04`、`0x05/0x00`、`0x06/0x00..0x03`、`0xFE`；
9. 确认 `0x06/0x25` 等内部诊断不出现在正式 SDK 和官网；
10. 统一固件、SDK、URDF 和官网版本号后再创建发布标签。

