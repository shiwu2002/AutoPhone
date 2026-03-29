# 设备配置与连接指南

## 📋 config.json 设备配置

### 当前配置（自动检测 USB 设备）

```json
{
  "device": {
    "type": "adb",
    "auto_connect": true,
    "devices": [
      {
        "type": "usb",
        "id": null
      }
    ]
  }
}
```

---

## 🔧 配置多个设备

### 示例 1: 指定 USB 设备 ID

```json
{
  "device": {
    "devices": [
      {
        "type": "usb",
        "id": "ABC123DEF456"  // 填写具体设备序列号
      }
    ]
  }
}
```

**查看设备 ID 方法：**
```bash
adb devices
# 输出示例：
# List of devices attached
# ABC123DEF456    device
# ```

### 示例 2: 混合使用 USB 和 WiFi 设备

```json
{
  "device": {
    "devices": [
      {
        "type": "usb",
        "id": null  // 自动检测第一个 USB 设备
      },
      {
        "type": "wifi",
        "ip": "192.168.1.100",
        "port": 5555
      },
      {
        "type": "wifi",
        "ip": "192.168.1.101",
        "port": 5555
      }
    ]
  }
}
```

### 示例 3: 只使用 WiFi 设备

```json
{
  "device": {
    "devices": [
      {
        "type": "wifi",
        "ip": "192.168.1.100",
        "port": 5555
      }
    ]
  }
}
```

---

## 📶 WiFi 设备连接步骤

### 步骤 1: 获取设备 IP 地址

在手机上查看：
- **设置** → **关于手机** → **状态信息** → **IP 地址**
- 或：**设置** → **WLAN** → 点击当前网络

### 步骤 2: 启用手机的 ADB 调试

1. **开发者选项** → **USB 调试** → 开启
2. 如果是第一次连接，需要在手机上授权

### 步骤 3: 连接 WiFi ADB

#### 方法 1: 使用工具脚本（推荐）
```bash
python connect_wifi_device.py --ip 192.168.1.100
```

#### 方法 2: 手动命令
```bash
# 1. USB 连接并启用无线调试
adb usb
adb connect 192.168.1.100:5555

# 2. 拔掉 USB 线（可选）

# 3. 验证连接
adb devices
```

### 步骤 4: 更新配置文件

编辑 `config.json`：
```json
{
  "device": {
    "devices": [
      {
        "type": "wifi",
        "ip": "192.168.1.100",
        "port": 5555
      }
    ]
  }
}
```

---

## 🔍 查看可用设备

### 命令行查看
```bash
adb devices
```

**输出示例：**
```
List of devices attached
ABC123DEF456    device          # USB 设备
192.168.1.100:5555    device    # WiFi 设备
```

### Python 脚本查看
```bash
python -c "from phone_agent.device_factory import get_device_factory; print([d.device_id for d in get_device_factory().list_devices()])"
```

---

## ⚠️ 常见问题

### Q1: 提示"没有可用设备"

**解决方法：**
1. 检查 USB 连接
2. 运行 `adb devices` 确认设备已识别
3. 如果是 WiFi 设备，确保已连接：`adb connect IP:端口`

### Q2: WiFi 设备连接失败

**可能原因：**
- 手机和电脑不在同一网络
- 防火墙阻止连接
- ADB 版本过旧

**解决步骤：**
```bash
# 1. 重启 ADB 服务器
adb kill-server
adb start-server

# 2. 重新连接
adb connect 192.168.1.100:5555

# 3. 验证
adb devices
```

### Q3: 如何断开 WiFi 设备？

```bash
adb disconnect 192.168.1.100:5555
```

---

## 🚀 快速配置流程

### 场景 1: 只有 1 个 USB 设备
✅ **无需修改配置**，默认配置即可工作

### 场景 2: 有多个 USB 设备
```json
{
  "device": {
    "devices": [
      {"type": "usb", "id": "设备 1 序列号"},
      {"type": "usb", "id": "设备 2 序列号"}
    ]
  }
}
```

### 场景 3: 使用 WiFi 设备
```bash
# 1. 连接设备
python connect_wifi_device.py --ip 192.168.1.100

# 2. 验证连接
adb devices

# 3. 运行批量处理
python batch_processor.py --input 问题.xlsx
```

### 场景 4: 混合使用
```json
{
  "device": {
    "devices": [
      {"type": "usb", "id": "USB 设备序列号"},
      {"type": "wifi", "ip": "192.168.1.100", "port": 5555}
    ]
  }
}
```

---

## 💡 最佳实践

### 1. USB 优先
- 开发测试阶段：使用 USB（稳定、快速）
- 批量生产阶段：可混合使用 WiFi

### 2. 设备命名
给每个设备贴标签，便于识别：
```json
{
  "device": {
    "devices": [
      {"type": "usb", "id": "ABC123", "name": "测试机 1"},
      {"type": "wifi", "ip": "192.168.1.100", "name": "测试机 2"}
    ]
  }
}
```

### 3. 网络要求
- WiFi 设备需要稳定的网络环境
- 建议使用 5GHz WiFi（更快更稳定）
- 避免设备过多导致网络拥堵

---

## 📞 需要帮助？

运行诊断命令：
```bash
# 检查 ADB
adb version

# 检查设备
adb devices

# 连接 WiFi 设备
python connect_wifi_device.py --ip 192.168.1.100 --help
```
