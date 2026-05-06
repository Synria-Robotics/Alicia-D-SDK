# Logger Level Filtering

The Alicia-D-SDK logger now supports log level filtering, allowing users to control which level of logs are printed to the console.

## Feature Overview

By setting the minimum log level, you can control which log messages are displayed on the console. All logs are still written to log files, but only logs at or above the specified level will be displayed on the console.

## Log Level Definition

Log levels are arranged from low to high importance:

| Level | Value | Description |
|-------|-------|-------------|
| DEBUG | 0 | Debug information, most detailed log level |
| INFO | 1 | General information, default level |
| MODULE | 2 | Module-related information |
| WARNING | 3 | Warning information |
| ERROR | 4 | Error information |
| SUCCESS | 5 | Success information, highest level |

## Usage

### 1. Specify Level When Creating Logger

```python
from alicia_d_sdk.utils.beauty_logger import BeautyLogger, LogLevel

# Only show WARNING level and above
logger = BeautyLogger(
    log_dir="logs", 
    log_name="app.log", 
    min_level=LogLevel.WARNING
)

# Show all levels of logs (DEBUG level)
logger = BeautyLogger(
    log_dir="logs", 
    log_name="app.log", 
    min_level=LogLevel.DEBUG
)

# Only show ERROR level logs
logger = BeautyLogger(
    log_dir="logs", 
    log_name="app.log", 
    min_level=LogLevel.ERROR
)
```

### 2. Dynamically Change Log Level

```python
# Create logger
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

### 3. Practical Usage Example

```python
from alicia_d_sdk.utils.beauty_logger import BeautyLogger, LogLevel

# Development environment: show all logs
if development_mode:
    logger = BeautyLogger("logs", "dev.log", min_level=LogLevel.DEBUG)
else:
    # Production environment: only show warnings and errors
    logger = BeautyLogger("logs", "prod.log", min_level=LogLevel.WARNING)

# Log messages at different levels
logger.debug("Detailed debug information")
logger.info("Application running normally")
logger.warning("Warning that needs attention")
logger.error("Error occurred")

# Adjust level at runtime as needed
if verbose_mode:
    logger.set_min_level(LogLevel.DEBUG)
```

## Notes

1. **Log File Completeness**: Regardless of the level set, all logs are written to log files, only console display is filtered.

2. **Default Level**: If `min_level` parameter is not specified, `LogLevel.INFO` is used by default.

3. **Level Validation**: The `set_min_level()` method validates that the level value is valid, invalid levels will raise `ValueError`.

4. **Backward Compatibility**: Existing code requires no modification, new feature is fully backward compatible.

## Error Handling

```python
try:
    logger.set_min_level(999)  # Invalid level
except ValueError as e:
    print(f"Invalid log level: {e}")
```

## Best Practices

1. **Development Phase**: Use `LogLevel.DEBUG` to get detailed information
2. **Testing Phase**: Use `LogLevel.INFO` to view main flow
3. **Production Environment**: Use `LogLevel.WARNING` or `LogLevel.ERROR` to reduce noise
4. **Debugging Issues**: Temporarily set to `LogLevel.DEBUG` to get more information

## Complete Example

See the `examples/logger_level_demo.py` file for complete demonstration code.

