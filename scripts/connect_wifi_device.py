#!/usr/bin/env python3
"""
WiFi 设备连接工具

用法：
    python connect_wifi_device.py --ip 192.168.1.100
    python connect_wifi_device.py --ip 192.168.1.100 --port 5555
    python connect_wifi_device.py --disconnect --ip 192.168.1.100
"""

import argparse
import subprocess
import sys


def run_command(command):
    """执行 ADB 命令并返回输出"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)


def connect_wifi_device(ip: str, port: int = 5555):
    """
    连接 WiFi 设备
    
    参数:
        ip: 设备 IP 地址（可以包含端口，如 192.168.1.3:40333）
        port: ADB 端口（默认 5555，如果 ip 中已包含端口则忽略）
    """
    # 检查 IP 是否已包含端口
    if ':' in ip and not ip.endswith(':'):
        # IP 已包含端口
        device_address = ip
        print(f"ℹ️  检测到 IP 已包含端口：{device_address}")
    else:
        # IP 未包含端口，使用默认或指定的端口
        device_address = f"{ip}:{port}"
    
    print(f"🔌 正在连接 WiFi 设备：{device_address}")
    print("-" * 60)
    
    # 步骤 1: 检查 ADB 是否可用
    print("1️⃣ 检查 ADB 状态...")
    code, stdout, stderr = run_command("adb version")
    if code != 0:
        print(f"❌ ADB 未安装或不可用")
        print(f"   错误：{stderr}")
        return False
    print(f"✅ ADB 正常")
    
    # 步骤 2: 尝试连接
    print(f"\n2️⃣ 连接到 {device_address}...")
    code, stdout, stderr = run_command(f"adb connect {device_address}")
    
    output = stdout + stderr
    print(output)
    
    if "connected" in output or "already connected" in output.lower():
        print(f"✅ 连接成功！")
        
        # 步骤 3: 验证连接
        print("\n3️⃣ 验证连接...")
        code, stdout, stderr = run_command("adb devices")
        
        print("已连接的设备:")
        for line in stdout.split('\n'):
            if device_address in line and 'device' in line:
                print(f"  ✅ {line.strip()}")
                return True
        
        print(f"⚠️  设备已连接但未在列表中显示，请稍后检查")
        return True
    else:
        print(f"❌ 连接失败")
        if stderr:
            print(f"   错误：{stderr}")
        return False


def disconnect_wifi_device(ip: str, port: int = 5555):
    """
    断开 WiFi 设备
    
    参数:
        ip: 设备 IP 地址
        port: ADB 端口（默认 5555）
    """
    device_address = f"{ip}:{port}"
    
    print(f"🔌 正在断开 WiFi 设备：{device_address}")
    print("-" * 60)
    
    code, stdout, stderr = run_command(f"adb disconnect {device_address}")
    
    print(stdout + stderr)
    
    if "disconnected" in stdout.lower() or "no such device" in stdout.lower():
        print(f"✅ 已断开连接")
        return True
    else:
        print(f"⚠️  设备可能已经断开或未连接")
        return False


def list_devices():
    """列出所有已连接的设备"""
    print("📱 已连接的 ADB 设备:")
    print("-" * 60)
    
    code, stdout, stderr = run_command("adb devices")
    
    if code != 0:
        print(f"❌ 无法获取设备列表")
        return
    
    lines = stdout.strip().split('\n')
    if len(lines) <= 1:
        print("没有已连接的设备")
        return
    
    for line in lines[1:]:
        if line.strip():
            parts = line.split()
            if len(parts) >= 2:
                device_id = parts[0]
                status = parts[1]
                
                if 'wifi' in device_id or ':' in device_id:
                    print(f"  📶 WiFi: {device_id} ({status})")
                else:
                    print(f"  🔌 USB:   {device_id} ({status})")


def main():
    parser = argparse.ArgumentParser(
        description="WiFi 设备连接工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 连接 WiFi 设备（默认端口 5555）
    python connect_wifi_device.py --ip 192.168.1.100
    
    # 指定端口
    python connect_wifi_device.py --ip 192.168.1.100 --port 5555
    
    # 断开连接
    python connect_wifi_device.py --disconnect --ip 192.168.1.100
    
    # 查看已连接的设备
    python connect_wifi_device.py --list
        """
    )
    
    parser.add_argument("--ip", "-i", type=str, help="设备 IP 地址")
    parser.add_argument("--port", "-p", type=int, default=5555, help="ADB 端口（默认：5555）")
    parser.add_argument("--disconnect", "-d", action="store_true", help="断开连接")
    parser.add_argument("--list", "-l", action="store_true", help="列出已连接的设备")
    
    args = parser.parse_args()
    
    if args.list:
        list_devices()
    elif args.disconnect:
        if not args.ip:
            print("❌ 错误：--disconnect 需要指定 --ip")
            sys.exit(1)
        success = disconnect_wifi_device(args.ip, args.port)
        sys.exit(0 if success else 1)
    elif args.ip:
        success = connect_wifi_device(args.ip, args.port)
        sys.exit(0 if success else 1)
    else:
        print("❌ 错误：请指定 --ip 或使用 --list 查看设备")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
