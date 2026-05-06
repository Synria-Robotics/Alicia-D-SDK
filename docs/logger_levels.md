# 日志级别过滤功能

Alicia-D-SDK 的日志器现在支持日志级别过滤功能，允许用户控制哪些级别的日志会被打印到控制台。

## 功能概述

通过设置最低日志级别，你可以控制哪些日志消息会显示在控制台上。所有日志仍然会被写入日志文件，但只有达到指定级别的日志才会在控制台显示。

## 日志级别定义

日志级别按重要性从低到高排列：

| 级别 | 数值 | 描述 |
|------|------|------|
| DEBUG | 0 | 调试信息，最详细的日志级别 |
| INFO | 1 | 一般信息，默认级别 |
| MODULE | 2 | 模块相关信息 |
| WARNING | 3 | 警告信息 |
| ERROR | 4 | 错误信息 |
| SUCCESS | 5 | 成功信息，最高级别 |

## 使用方法

### 1. 创建日志器时指定级别

```python
from alicia_d_sdk.utils.beauty_logger import BeautyLogger, LogLevel

# 只显示 WARNING 及以上级别的日志
logger = BeautyLogger(
    log_dir="logs", 
    log_name="app.log", 
    min_level=LogLevel.WARNING
)

# 显示所有级别的日志（DEBUG 级别）
logger = BeautyLogger(
    log_dir="logs", 
    log_name="app.log", 
    min_level=LogLevel.DEBUG
)

# 只显示 ERROR 级别的日志
logger = BeautyLogger(
    log_dir="logs", 
    log_name="app.log", 
    min_level=LogLevel.ERROR
)
```

### 2. 动态改变日志级别

```python
# 创建日志器
logger = BeautyLogger("logs", "app.log", min_level=LogLevel.INFO)

# Log some messages
logger.info("Application started")
logger.debug("This DEBUG message will not be displayed")

# Dynamically change to DEBUG level
logger.set_min_level(LogLevel.DEBUG)
logger.debug("Now this DEBUG message will be displayed")

# Change to only show errors
logger.set_min_level(LogLevel.ERROR)
logger.warning("This WARNING message will not be displayed")
logger.error("This ERROR message will be displayed")
```

### 3. 实际使用示例

```python
from alicia_d_sdk.utils.beauty_logger import BeautyLogger, LogLevel

# 开发环境：显示所有日志
if development_mode:
    logger = BeautyLogger("logs", "dev.log", min_level=LogLevel.DEBUG)
else:
    # 生产环境：只显示警告和错误
    logger = BeautyLogger("logs", "prod.log", min_level=LogLevel.WARNING)

# Log messages at different levels
logger.debug("Detailed debug information")
logger.info("Application running normally")
logger.warning("Warning that needs attention")
logger.error("An error occurred")

# 运行时根据需要调整级别
if verbose_mode:
    logger.set_min_level(LogLevel.DEBUG)
```

## 注意事项

1. **日志文件完整性**：无论设置什么级别，所有日志都会被写入日志文件，只是控制台显示会过滤。

2. **默认级别**：如果不指定 `min_level` 参数，默认使用 `LogLevel.INFO` 级别。

3. **级别验证**：`set_min_level()` 方法会验证级别值是否有效，无效级别会抛出 `ValueError`。

4. **向后兼容**：现有代码无需修改，新功能完全向后兼容。

## 错误处理

```python
try:
    logger.set_min_level(999)  # 无效级别
except ValueError as e:
    print(f"Invalid log level: {e}")
```

## 最佳实践

1. **开发阶段**：使用 `LogLevel.DEBUG` 获取详细信息
2. **测试阶段**：使用 `LogLevel.INFO` 查看主要流程
3. **生产环境**：使用 `LogLevel.WARNING` 或 `LogLevel.ERROR` 减少噪音
4. **调试问题**：临时设置为 `LogLevel.DEBUG` 获取更多信息

## 完整示例

查看 `examples/logger_level_demo.py` 文件获取完整的演示代码。
