"""CLI 模块 - 命令行界面

包含所有 CLI 相关的功能：
- 参数解析
- 系统检查
- 设备命令处理
- 配置向导
- 批量模式
"""

from cli.parser import parse_args
from cli.checks import check_system_requirements, check_model_api
from cli.commands import handle_device_commands, run_batch_mode
from cli.wizard import run_config_wizard
from cli.config_loader import load_config
from cli.timing import apply_timing_config

__all__ = [
    # Parser
    'parse_args',
    # Checks
    'check_system_requirements',
    'check_model_api',
    # Commands
    'handle_device_commands',
    'run_batch_mode',
    # Wizard
    'run_config_wizard',
    # Config
    'load_config',
    # Timing
    'apply_timing_config',
]
