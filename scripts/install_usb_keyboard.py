#!/usr/bin/env python3
"""
USB 设备 ADB 键盘安装工具

用法：
    python install_usb_keyboard.py
    python install_usb_keyboard.py --device ABC123DEF456
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(command, timeout=30):
    """执行 ADB 命令并返回输出"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "命令执行超时"
    except Exception as e:
        return -1, "", str(e)


def check_adb_installed():
    """检查 ADB 是否已安装"""
    print("🔍 检查 ADB 状态...")
    code, stdout, stderr = run_command("adb version")
    
    if code != 0:
        print(f"❌ ADB 未安装或不可用")
        print(f"   请确保已安装 ADB 并添加到 PATH")
        return False
    
    version_line = stdout.strip().split('\n')[0]
    print(f"✅ ADB 已安装：{version_line}")
    return True


def find_device(device_id=None):
    """查找指定的设备或第一个可用设备"""
    print("\n📱 查找设备...")
    
    code, stdout, stderr = run_command("adb devices")
    
    if code != 0:
        print(f"❌ 无法获取设备列表")
        return None
    
    lines = stdout.strip().split('\n')
    devices = []
    
    for line in lines[1:]:  # 跳过标题行
        if line.strip() and '\tdevice' in line:
            dev_id = line.split('\t')[0]
            devices.append(dev_id)
    
    if not devices:
        print(f"❌ 没有已连接的设备")
        print(f"\n💡 提示:")
        print(f"   1. 用 USB 线连接手机到电脑")
        print(f"   2. 在手机上授权 USB 调试")
        print(f"   3. 运行 'adb devices' 验证")
        return None
    
    # 如果指定了设备 ID
    if device_id:
        if device_id in devices:
            print(f"✅ 找到指定设备：{device_id}")
            return device_id
        else:
            print(f"❌ 未找到指定设备：{device_id}")
            print(f"   可用设备：{', '.join(devices)}")
            return None
    
    # 使用第一个设备
    selected = devices[0]
    print(f"✅ 使用第一个设备：{selected}")
    
    if len(devices) > 1:
        print(f"ℹ️  发现 {len(devices)} 个设备，使用第一个")
        print(f"   如需指定设备，使用 --device 参数")
    
    return selected


def install_keyboard_apk(device_id):
    """安装 ADBKeyboard.apk 到设备"""
    print("\n⌨️  安装 ADB 键盘...")
    
    # 查找 APK 文件
    apk_paths = [
        Path(__file__).parent / "ADBKeyboard.apk",
        Path(__file__).parent.parent / "ADBKeyboard.apk",
        Path("ADBKeyboard.apk")
    ]
    
    apk_path = None
    for path in apk_paths:
        if path.exists():
            apk_path = path
            break
    
    if not apk_path:
        print(f"❌ 找不到 ADBKeyboard.apk 文件")
        print(f"   请确保该文件在项目根目录")
        return False
    
    print(f"📦 APK 文件：{apk_path}")
    
    # 安装 APK
    print(f"\n🚀 开始安装到设备 {device_id}...")
    code, stdout, stderr = run_command(
        f'adb -s {device_id} install "{apk_path}"',
        timeout=60
    )
    
    output = stdout + stderr
    print(output)
    
    if "Success" in output or "success" in output.lower():
        print(f"\n✅ 安装成功！")
        return True
    else:
        print(f"\n❌ 安装失败")
        if "already exists" in output.lower():
            print(f"ℹ️  键盘可能已经安装，可以在手机设置中切换输入法")
        return False


def verify_installation(device_id):
    """验证键盘是否已安装"""
    print("\n🔍 验证安装...")
    
    code, stdout, stderr = run_command(
        f'adb -s {device_id} shell pm list packages | grep com.android.adbkeyboard',
        timeout=10
    )
    
    if "com.android.adbkeyboard" in stdout:
        print(f"✅ ADB 键盘已安装")
        print(f"\n💡 使用方法:")
        print(f"   1. 在手机上打开任意输入框")
        print(f"   2. 点击输入法选择按钮")
        print(f"   3. 选择 'ADB Keyboard'")
        print(f"   4. 现在可以自动输入文本了")
        return True
    else:
        print(f"⚠️  未检测到 ADB 键盘")
        print(f"   可能需要手动在手机上切换输入法")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="USB 设备 ADB 键盘安装工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 自动检测并使用第一个 USB 设备
    python install_usb_keyboard.py
    
    # 指定设备
    python install_usb_keyboard.py --device ABC123DEF456
    
    # 只验证安装
    python install_usb_keyboard.py --verify-only
        """
    )
    
    parser.add_argument("--device", "-d", type=str, help="指定设备 ID（默认使用第一个）")
    parser.add_argument("--verify-only", action="store_true", help="只验证安装，不执行安装")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("USB 设备 ADB 键盘安装工具")
    print("=" * 60)
    
    # 检查 ADB
    if not check_adb_installed():
        sys.exit(1)
    
    # 查找设备
    device_id = find_device(args.device)
    if not device_id:
        sys.exit(1)
    
    # 如果只验证
    if args.verify_only:
        success = verify_installation(device_id)
        sys.exit(0 if success else 1)
    
    # 安装键盘
    success = install_keyboard_apk(device_id)
    
    # 验证安装
    if success:
        verify_installation(device_id)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
