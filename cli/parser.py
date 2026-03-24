"""CLI 参数解析模块"""

import argparse
import os
from pathlib import Path

from .config_loader import load_config


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    config = load_config()

    model_config = config.get('model', {})
    agent_config = config.get('agent', {})
    device_config = config.get('device', {})

    parser = argparse.ArgumentParser(
        description="Phone Agent - AI-powered phone automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # 启动程序
    python main.py

    # 使用交互式配置向导设置模型提供商
    python main.py --config

    # 指定模型端点
    python main.py --base-url http://localhost:8000/v1

    # 使用 API 密钥进行身份验证
    python main.py --apikey sk-xxxxx

    # 使用特定设备运行
    python main.py --device-id emulator-5554

    # 连接到远程设备
    python main.py --connect 192.168.1.100:5555

    # 列出已连接的设备
    python main.py --list-devices

    # 启用 USB 设备上的 TCP/IP
    python main.py --enable-tcpip

    # 列出支持的应用
    python main.py --list-apps

    # 安装 ADB Keyboard
    python main.py --install-keyboard
        """,
    )

    # Model options
    env_base_url = os.getenv("PHONE_AGENT_BASE_URL")
    env_model = os.getenv("PHONE_AGENT_MODEL")
    env_api_key = os.getenv("PHONE_AGENT_API_KEY")

    is_local = model_config.get('type', 'remote') == 'local'
    provider = model_config.get('provider', 'anthropic')

    # Get provider-specific config - support both new format (model.providers.{provider}) and old format (model.{provider})
    provider_config = model_config.get('providers', {}).get(provider, {}) or model_config.get(provider, {})

    parser.add_argument(
        "--base-url",
        type=str,
        default=model_config.get('base_url', provider_config.get('base_url', "http://localhost:8000/v1")) if is_local or not env_base_url else env_base_url,
        help="Model API base URL",
    )

    parser.add_argument(
        "--model",
        type=str,
        default=model_config.get('model_name', provider_config.get('model', "autoglm-phone-9b")) if is_local or not env_model else env_model,
        help="Model name",
    )

    parser.add_argument(
        "--apikey",
        type=str,
        default=model_config.get('api_key', provider_config.get('api_key', "ollama")) if is_local or not env_api_key else env_api_key,
        help="API key for model authentication",
    )

    parser.add_argument(
        "--max-steps",
        type=int,
        default=int(os.getenv("PHONE_AGENT_MAX_STEPS", agent_config.get('max_steps', 100))),
        help="Maximum steps per task",
    )

    # Device options
    parser.add_argument(
        "--device-id",
        "-d",
        type=str,
        default=os.getenv("PHONE_AGENT_DEVICE_ID", agent_config.get('device_id')),
        help="ADB device ID",
    )

    parser.add_argument(
        "--connect",
        "-c",
        type=str,
        metavar="ADDRESS",
        help="Connect to remote device (e.g., 192.168.1.100:5555)",
    )

    parser.add_argument(
        "--disconnect",
        type=str,
        nargs="?",
        const="all",
        metavar="ADDRESS",
        help="Disconnect from remote device (or 'all' to disconnect all)",
    )

    parser.add_argument(
        "--list-devices", action="store_true", help="List connected devices and exit"
    )

    parser.add_argument(
        "--enable-tcpip",
        type=int,
        nargs="?",
        const=5555,
        metavar="PORT",
        help="Enable TCP/IP debugging on USB device (default port: 5555)",
    )

    # Other options
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress verbose output"
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output (show detailed execution logs)"
    )

    parser.add_argument(
        "--list-apps", action="store_true", help="List supported apps and exit"
    )

    parser.add_argument(
        "--install-keyboard", action="store_true",
        help="Install ADBKeyboard.apk to connected device and exit"
    )

    parser.add_argument(
        "--lang",
        type=str,
        choices=["cn", "en"],
        default=os.getenv("PHONE_AGENT_LANG", agent_config.get('lang', "cn")),
        help="Language for system prompt (cn or en, default: cn)",
    )

    parser.add_argument(
        "--device-type",
        type=str,
        choices=["adb"],
        default=device_config.get('type', "adb"),
        help="Device type: adb for Android (default: adb)",
    )

    parser.add_argument(
        "--config", action="store_true", help="Interactive configuration wizard for model provider setup"
    )

    # Batch mode options
    parser.add_argument(
        "--batch",
        type=str,
        metavar="FILE",
        help="Run in batch mode with questions from file (Excel or TXT)",
    )
    parser.add_argument(
        "--batch-output",
        type=str,
        default="batch_results.xlsx",
        help="Output file for batch results (default: batch_results.xlsx)",
    )
    parser.add_argument(
        "--question-column",
        type=str,
        default="问题",
        help="Column name for questions in Excel (default: 问题)",
    )
    parser.add_argument(
        "--max-questions",
        type=int,
        default=0,
        help="Maximum number of questions to process (0=all)",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip questions that already have answers in the input file",
    )

    # Timing options
    parser.add_argument(
        "--keyboard-switch-delay", type=float, default=None,
        help="Delay after switching to ADB keyboard (seconds)"
    )
    parser.add_argument(
        "--text-clear-delay", type=float, default=None,
        help="Delay after clearing text (seconds)"
    )
    parser.add_argument(
        "--text-input-delay", type=float, default=None,
        help="Delay after typing text (seconds)"
    )
    parser.add_argument(
        "--keyboard-restore-delay", type=float, default=None,
        help="Delay after restoring original keyboard (seconds)"
    )
    parser.add_argument(
        "--tap-delay", type=float, default=None,
        help="Default delay after tap (seconds)"
    )
    parser.add_argument(
        "--double-tap-delay", type=float, default=None,
        help="Default delay after double tap (seconds)"
    )
    parser.add_argument(
        "--double-tap-interval", type=float, default=None,
        help="Interval between two taps in double tap (seconds)"
    )
    parser.add_argument(
        "--long-press-delay", type=float, default=None,
        help="Default delay after long press (seconds)"
    )
    parser.add_argument(
        "--swipe-delay", type=float, default=None,
        help="Default delay after swipe (seconds)"
    )
    parser.add_argument(
        "--back-delay", type=float, default=None,
        help="Default delay after back button (seconds)"
    )
    parser.add_argument(
        "--home-delay", type=float, default=None,
        help="Default delay after home button (seconds)"
    )
    parser.add_argument(
        "--launch-delay", type=float, default=None,
        help="Default delay after launching app (seconds)"
    )
    parser.add_argument(
        "--adb-restart-delay", type=float, default=None,
        help="Wait time after enabling TCP/IP mode (seconds)"
    )
    parser.add_argument(
        "--server-restart-delay", type=float, default=None,
        help="Wait time between killing and starting ADB server (seconds)"
    )

    parser.add_argument(
        "task",
        nargs="?",
        type=str,
        help="Task to execute (interactive mode if not provided)",
    )

    return parser.parse_args()
