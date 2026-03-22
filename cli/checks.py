"""系统检查模块 - 检查 ADB、设备和键盘等"""

import argparse
import logging
import shutil
from typing import Optional

from openai import OpenAI

from phone_agent.adb.cmd_executor import CommandExecutor
from phone_agent.device_factory import DeviceType
from phone_agent.utils.logger import setup_logger

logger = setup_logger(__name__, level=logging.INFO)


def check_system_requirements(
    device_type: DeviceType = DeviceType.ADB,
    args: Optional[argparse.Namespace] = None,
) -> bool:
    """
    在运行代理之前检查系统要求。

    检查项：
    1. ADB 工具已安装
    2. 至少连接了一台设备
    3. 设备上安装了 ADB 键盘

    Args:
        device_type: 设备工具类型（ADB）。
        args: 命令行参数（用于获取 device_id）。

    Returns:
        如果所有检查通过返回 True，否则返回 False。
    """
    import argparse  # Late import to avoid circular dependency

    logger.info("Checking system requirements...")
    logger.info("-" * 50)

    all_passed = True

    # Determine tool name and command
    tool_name = "ADB"
    tool_cmd = "adb"

    # Check 1: Tool installed
    logger.info(f"1. Checking {tool_name} installation...")
    if shutil.which(tool_cmd) is None:
        logger.critical("❌ FAILED")
        logger.error(f"   Error: {tool_name} is not installed or not in PATH.")
        logger.error(f"   Solution: Install {tool_name}:")
        if device_type == DeviceType.ADB:
            print("     - macOS: brew install android-platform-tools")
            print("     - Linux: sudo apt install android-tools-adb")
            print(
                "     - Windows: Download from https://developer.android.com/studio/releases/platform-tools"
            )
        all_passed = False
    else:
        # Double check by running version command
        try:
            version_cmd = [tool_cmd, "version"]
            result = CommandExecutor.run_silent(version_cmd, timeout=10)
            if result.returncode == 0:
                version_line = result.stdout.strip().split("\n")[0]
                print(f"✅ OK ({version_line if version_line else 'installed'})")
            else:
                print("❌ FAILED")
                print(f"   Error: {tool_name} command failed to run.")
                all_passed = False
        except Exception as e:
            print("❌ FAILED")
            print(f"   Error: {tool_name} command not found.")
            all_passed = False

    # If ADB is not installed, skip remaining checks
    if not all_passed:
        print("-" * 50)
        print("❌ System check failed. Please fix the issues above.")
        return False

    # Check 2: Device connected
    logger.info("2. Checking connected devices...")
    devices = []
    try:
        result = CommandExecutor.run_silent(["adb", "devices"], timeout=10)
        lines = result.stdout.strip().split("\n")
        # Filter out header and empty lines, look for 'device' status
        devices = [
            line for line in lines[1:] if line.strip() and "\tdevice" in line
        ]
        if not devices:
            print("❌ FAILED")
            print("   Error: No devices connected.")
            print("   Solution:")
            print("     1. Enable USB debugging on your Android device")
            print("     2. Connect via USB and authorize the connection")
            print(
                "     3. Or connect remotely: python main.py --connect <ip>:<port>"
            )
            all_passed = False
        else:
            device_ids = [d.strip() for d in devices]
            print(
                f"✅ OK ({len(devices)} device(s): {', '.join(device_ids[:2])}{'...' if len(device_ids) > 2 else ''})"
            )
    except Exception as e:
        print("❌ FAILED")
        print(f"   Error: {e}")
        all_passed = False

    # If no device connected, skip ADB Keyboard check
    if not all_passed:
        print("-" * 50)
        print("❌ System check failed. Please fix the issues above.")
        return False

    # Check 3: ADB Keyboard installed
    if device_type == DeviceType.ADB:
        logger.info("3. Checking ADB Keyboard...")
        try:
            adb_cmd = ["adb"]

            # Determine which device to use
            target_device = None
            if args and args.device_id:
                target_device = args.device_id
            elif len(devices) >= 1:
                target_device = devices[0].split("\t")[0].strip()

            if target_device:
                adb_cmd.extend(["-s", target_device])

            adb_cmd.extend(["shell", "ime", "list", "-s"])
            result = CommandExecutor.run_silent(adb_cmd, timeout=10)
            ime_list = result.stdout.strip()

            if "com.android.adbkeyboard/.AdbIME" in ime_list:
                print("✅ OK")
            else:
                print("❌ FAILED")
                print("   Error: ADB Keyboard is not installed on the device.")
                print("   Solution:")
                print("     Use the built-in install command:")
                print("       python bin/install_keyboard.py")
                print("     Or: python main.py --install-keyboard")
                print()
                print("     Manual install:")
                print("       1. Download ADB Keyboard APK from:")
                print("          https://github.com/senzhk/ADBKeyBoard/blob/master/ADBKeyboard.apk")
                print("       2. Install it on your device: adb install ADBKeyboard.apk")
                print("       3. Enable it in Settings > System > Languages & Input > Virtual Keyboard"
                )
                all_passed = False
        except Exception as e:
            print("❌ FAILED")
            print(f"   Error: {e}")
            all_passed = False

    print("-" * 50)

    if all_passed:
        print("✅ All system checks passed!\n")
    else:
        print("❌ System check failed. Please fix the issues above.")

    return all_passed


def check_model_api(base_url: str, model_name: str, api_key: str = "EMPTY") -> bool:
    """
    检查模型 API 是否可访问。

    Args:
        base_url: API 基础 URL
        model_name: 要检查的模型名称
        api_key: 认证用的 API 密钥

    Returns:
        如果所有检查通过返回 True，否则返回 False。
    """
    print("🔍 Checking model API...")
    print("-" * 50)

    all_passed = True

    print(f"1. Checking API connectivity ({base_url})...", end=" ")
    try:
        client = OpenAI(base_url=base_url, api_key=api_key, timeout=30.0)

        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5,
            temperature=0.0,
            stream=False,
        )

        if response.choices and len(response.choices) > 0:
            print("✅ OK")
        else:
            print("❌ FAILED")
            print("   Error: Received empty response from API")
            all_passed = False

    except Exception as e:
        print("❌ FAILED")
        error_msg = str(e)

        if "Connection refused" in error_msg or "Connection error" in error_msg:
            print(f"   Error: Cannot connect to {base_url}")
            print("   Solution:")
            print("     1. Check if the model server is running")
            print("     2. Verify the base URL is correct")
            print(f"     3. Try: curl {base_url}/chat/completions")
        elif "timed out" in error_msg.lower() or "timeout" in error_msg.lower():
            print(f"   Error: Connection to {base_url} timed out")
            print("   Solution:")
            print("     1. Check your network connection")
            print("     2. Verify the server is responding")
        elif (
            "Name or service not known" in error_msg
            or "nodename nor servname" in error_msg
        ):
            print(f"   Error: Cannot resolve hostname")
            print("   Solution:")
            print("     1. Check the URL is correct")
            print("     2. Verify DNS settings")
        else:
            print(f"   Error: {error_msg}")

        all_passed = False

    print("-" * 50)

    if all_passed:
        print("✅ Model API checks passed!\n")
    else:
        print("❌ Model API check failed. Please fix the issues above.")

    return all_passed
