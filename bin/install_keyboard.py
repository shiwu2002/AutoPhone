#!/usr/bin/env python3
"""ADB Keyboard 安装工具

用于自动安装 ADBKeyboard.apk 到连接的 Android 设备。
"""

import subprocess
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def check_adb_installed() -> bool:
    """检查 ADB 是否已安装。"""
    try:
        result = subprocess.run(
            ["adb", "version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version_line = result.stdout.strip().split("\n")[0]
            print(f"[OK] ADB 已安装：{version_line}")
            return True
        else:
            print("[ERR] ADB 未安装或无法运行")
            return False
    except FileNotFoundError:
        print("[ERR] ADB 未安装或不在 PATH 中")
        return False
    except Exception as e:
        print(f"[ERR] 检查 ADB 时出错：{e}")
        return False


def check_device_connected() -> tuple[bool, str]:
    """检查是否有设备连接。

    Returns:
        (是否连接，设备 ID)
    """
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=5
        )

        devices = []
        for line in result.stdout.strip().split("\n")[1:]:  # 跳过标题行
            if line.strip() and "\tdevice" in line:
                device_id = line.split("\t")[0].strip()
                devices.append(device_id)

        if not devices:
            print("✗ 没有检测到连接的设备")
            return False, ""

        device_id = devices[0]
        print(f"✓ 已连接设备：{device_id}")

        if len(devices) > 1:
            print(f"  注意：检测到 {len(devices)} 台设备，将使用第一台 ({device_id})")

        return True, device_id
    except Exception as e:
        print(f"✗ 检查设备时出错：{e}")
        return False, ""


def check_apk_exists() -> tuple[bool, Path]:
    """检查 ADBKeyboard.apk 文件是否存在。

    Returns:
        (是否存在，文件路径)
    """
    # 首先在当前脚本所在目录查找
    script_dir = Path(__file__).parent
    apk_path = script_dir / "ADBKeyboard.apk"

    if apk_path.exists():
        print(f"✓ APK 文件存在：{apk_path}")
        return True, apk_path

    # 然后在当前工作目录查找
    cwd_apk = Path.cwd() / "ADBKeyboard.apk"
    if cwd_apk.exists():
        print(f"✓ APK 文件存在：{cwd_apk}")
        return True, cwd_apk

    print("✗ 未找到 ADBKeyboard.apk 文件")
    print(f"  请在以下目录查找该文件:")
    print(f"    - {script_dir}")
    print(f"    - {Path.cwd()}")
    return False, None


def install_apk(apk_path: Path, device_id: str | None = None) -> bool:
    """安装 APK 到设备。

    Args:
        apk_path: APK 文件路径
        device_id: 设备 ID（可选）

    Returns:
        安装成功返回 True
    """
    cmd = ["adb"]

    if device_id:
        cmd.extend(["-s", device_id])

    cmd.extend(["install", "-r", str(apk_path)])

    print(f"\n正在安装 ADBKeyboard.apk...")
    print(f"命令：{' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        output = result.stdout + result.stderr

        if "Success" in output or "success" in output:
            print("✓ APK 安装成功!")
            return True
        elif "INSTALL_SUCCESS" in output:
            print("✓ APK 安装成功!")
            return True
        elif "INSTALL_FAILED_ALREADY_EXISTS" in output:
            print("⚠ APK 已存在，尝试覆盖安装...")
            # 尝试带 -r 参数重新安装（保留数据）
            cmd.insert(len(cmd) - 1, "-r")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if "Success" in result.stdout or "Success" in result.stderr:
                print("✓ APK 覆盖安装成功!")
                return True
            print("✗ 覆盖安装失败")
            print(result.stderr)
            return False
        else:
            print("✗ APK 安装失败")
            if result.stderr:
                print(f"错误信息：{result.stderr}")
            if result.stdout:
                print(f"输出：{result.stdout}")
            return False

    except subprocess.TimeoutExpired:
        print("✗ 安装超时（60 秒）")
        return False
    except Exception as e:
        print(f"✗ 安装过程中出错：{e}")
        return False


def enable_keyboard(device_id: str | None = None) -> None:
    """提示用户启用键盘。"""
    print("\n" + "=" * 50)
    print("最后一步：在设备上启用 ADB Keyboard")
    print("=" * 50)
    print("\n请在设备上执行以下操作:")
    print("1. 打开 设置 > 系统 > 语言和输入法")
    print("2. 点击 虚拟键盘 或 屏幕键盘")
    print("3. 勾选 ADBKeyboard 使其生效")
    print("\n或使用 ADB 命令启用:")

    cmd = ["adb"]
    if device_id:
        cmd.extend(["-s", device_id])
    cmd.extend(["shell", "ime", "enable", "com.android.adbkeyboard/.AdbIME"])

    print(f"   {' '.join(cmd)}")

    # 尝试自动启用
    print("\n正在尝试自动启用...")
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        # 设置为默认输入法
        cmd[-2] = "set"
        subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        # 验证是否启用成功
        cmd[-2] = "list"
        cmd.append("-s")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if "com.android.adbkeyboard/.AdbIME" in result.stdout:
            print("✓ ADB Keyboard 已成功启用并设置为默认输入法")
        else:
            print("⚠ 自动启用可能未成功，请手动在设备上启用")
    except Exception as e:
        print(f"⚠ 自动启用失败，请手动在设备上启用：{e}")


def print_download_info() -> None:
    """打印下载信息。"""
    print("\n如需下载 ADBKeyboard.apk，请访问:")
    print("  https://github.com/senzhk/ADBKeyBoard")
    print("\n或直接下载:")
    print("  https://github.com/senzhk/ADBKeyBoard/blob/master/ADBKeyboard.apk")


def main() -> int:
    """主函数。

    Returns:
        退出码（0=成功，1=失败）
    """
    print("=" * 50)
    print("ADB Keyboard 安装工具")
    print("=" * 50)
    print()

    # 1. 检查 ADB 是否已安装
    print("[1/4] 检查 ADB 安装状态...")
    if not check_adb_installed():
        print("\n请先安装 ADB:")
        print("  - macOS: brew install android-platform-tools")
        print("  - Linux: sudo apt install android-tools-adb")
        print("  - Windows: 从以下地址下载并添加到 PATH:")
        print("    https://developer.android.com/studio/releases/platform-tools")
        return 1
    print()

    # 2. 检查是否有设备连接
    print("[2/4] 检查连接的设备...")
    connected, device_id = check_device_connected()
    if not connected:
        print("\n请连接 Android 设备:")
        print("  1. 在设备上启用 USB 调试")
        print("  2. 通过 USB 连接设备")
        print("  3. 在设备上授权此电脑")
        print("\n或使用无线连接:")
        print("  python main.py --connect <设备 IP>:5555")
        return 1
    print()

    # 3. 检查 APK 文件是否存在
    print("[3/4] 检查 APK 文件...")
    apk_exists, apk_path = check_apk_exists()
    if not apk_exists:
        print_download_info()
        return 1
    print()

    # 4. 安装 APK
    print("[4/4] 安装 APK...")
    if not install_apk(apk_path, device_id):
        print("\n安装失败，请检查:")
        print("  1. 设备是否正确连接")
        print("  2. USB 调试是否已启用")
        print("  3. APK 文件是否完整")
        return 1
    print()

    # 5. 启用键盘
    enable_keyboard(device_id)

    print("\n" + "=" * 50)
    print("安装完成!")
    print("=" * 50)

    return 0


if __name__ == "__main__":
    sys.exit(main())
