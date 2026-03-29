# Scripts 使用指南

## 📁 文件结构

```
AutoPhone/
├── scripts/                 # 所有执行工具
│   ├── single_task.py      # 单任务执行
│   ├── batch_processor.py  # Excel 批量处理
│   ├── connect_wifi_device.py  # WiFi 设备连接
│   └── install_usb_keyboard.py  # USB 安装 ADB 键盘
├── config.json             # 配置文件
├── phone_agent/            # 核心库（包含 API）
└── references/             # 文档和参考资料
```

---

## 🛠️ 工具列表

### 1. single_task.py - 单任务执行

**用途：** 执行单个手机操作任务

```bash
# 基础用法
python scripts/single_task.py "打开微信"

# 保存截图
python scripts/single_task.py "查看时间" --save-screenshot

# 显示详细过程
python scripts/single_task.py "发送消息给张三" --verbose
```

---

### 2. batch_processor.py - Excel 批量处理

**用途：** 批量读取 Excel 问题并执行，在原 Excel 中添加答案列

```bash
# 基础用法
python scripts/batch_processor.py --input 问题.xlsx

# 指定输出文件
python scripts/batch_processor.py --input 问题.xlsx --output 答案.xlsx

# 自定义问题列
python scripts/batch_processor.py --input 数据.xlsx --column 题目

# 自定义提问模板
python scripts/batch_processor.py --input 问题.xlsx --template "请详细解答：{content}"

# 显示详细过程
python scripts/batch_processor.py --input 问题.xlsx --verbose
```

**Excel 格式要求：**
- 包含"问题"列（或自定义列名）
- 自动在最后一列添加"答案"列

---

### 3. connect_wifi_device.py - WiFi 设备连接

**用途：** 连接和管理 WiFi 设备

```bash
# 连接 WiFi 设备（IP 包含端口）
python scripts/connect_wifi_device.py --ip 192.168.1.3:40333

# 连接 WiFi 设备（分开指定 IP 和端口）
python scripts/connect_wifi_device.py --ip 192.168.1.3 --port 40333

# 查看已连接的设备
python scripts/connect_wifi_device.py --list

# 断开 WiFi 设备
python scripts/connect_wifi_device.py --disconnect --ip 192.168.1.3:40333
```

---

### 4. install_usb_keyboard.py - USB 安装 ADB 键盘

**用途：** 通过 USB 为设备自动安装 ADB 键盘输入法

```bash
# 自动检测并使用第一个 USB 设备
python scripts/install_usb_keyboard.py

# 指定设备
python scripts/install_usb_keyboard.py --device ABC123DEF456

# 只验证安装
python scripts/install_usb_keyboard.py --verify-only
```

**安装流程：**
1. 用 USB 线连接手机到电脑
2. 在手机上授权 USB 调试
3. 运行安装命令
4. 在手机上切换输入法为 "ADB Keyboard"

---

## 🚀 快速开始

### 场景 1: 第一次使用

```bash
# 1. 检查 ADB 设备
adb devices

# 2. 如果没有设备，连接 USB 设备
python scripts/install_usb_keyboard.py

# 3. 测试单任务
python scripts/single_task.py "打开微信"
```

### 场景 2: 批量处理问题

```bash
# 1. 准备 Excel 文件（包含"问题"列）
# 2. 运行批量处理
python scripts/batch_processor.py --input 智家通通收费标准.xlsx

# 3. 查看结果文件（自动生成 *_answers.xlsx）
```

### 场景 3: 使用 WiFi 设备

```bash
# 1. 获取设备 IP（手机设置→关于手机→状态信息）
# 2. 首次需要用 USB 启用无线调试
adb usb
adb tcpip 5555

# 3. 连接 WiFi
python scripts/connect_wifi_device.py --ip 192.168.1.3:40333

# 4. 验证
adb devices

# 5. 运行批量处理
python scripts/batch_processor.py --input 问题.xlsx
```

---

## 💡 常见问题

### Q1: 提示"没有可用设备"怎么办？

**解决方法：**
```bash
# 1. 检查 USB 连接
adb devices

# 2. 如果是 WiFi 设备，确保已连接
python scripts/connect_wifi_device.py --ip 192.168.1.3:40333

# 3. 重启 ADB 服务器
adb kill-server
adb start-server
```

### Q2: 如何安装依赖？

```bash
pip install pandas openpyxl
```

### Q3: Excel 文件格式有什么要求？

- 必须包含"问题"列（或自定义列名）
- 支持 `.xlsx` 和 `.xls` 格式
- 自动在最后一列添加"答案"列

### Q4: 多个设备如何指定？

编辑 `config.json`:
```json
{
  "device": {
    "devices": [
      {"type": "usb", "id": "设备 1 序列号"},
      {"type": "wifi", "ip": "192.168.1.3", "port": 40333}
    ]
  }
}
```

---

## 📊 性能参考

### batch_processor.py（多设备并行）

| 问题数 | 设备数 | 预计耗时 |
|--------|--------|----------|
| 10 | 1 | ~100 秒 |
| 10 | 2 | ~50 秒 (2x 加速) |
| 10 | 3 | ~35 秒 (3x 加速) |
| 100 | 3 | ~350 秒 |

*注：实际时间取决于问题复杂度和模型响应速度*

---

## 🔧 配置说明

### config.json 设备配置

**自动检测 USB 设备（默认）：**
```json
{
  "device": {
    "devices": [
      {"type": "usb", "id": null}
    ]
  }
}
```

**指定 WiFi 设备：**
```json
{
  "device": {
    "devices": [
      {
        "type": "wifi",
        "ip": "192.168.1.3",
        "port": 40333
      }
    ]
  }
}
```

**混合使用多个设备：**
```json
{
  "device": {
    "devices": [
      {"type": "usb", "id": "ABC123DEF456"},
      {
        "type": "wifi",
        "ip": "192.168.1.3",
        "port": 40333
      }
    ]
  }
}
```

---

## 📝 完整示例流程

### 示例：批量问答

**步骤 1: 准备 Excel**
创建 `智家通通收费标准.xlsx`，包含"问题"列：
| 问题 |
|------|
| 智家通通的收费标准是什么？ |
| 如何办理智家通通套餐？ |
| 智家通通支持哪些功能？ |

**步骤 2: 连接设备**
```bash
# USB 方式
adb devices

# 或 WiFi 方式
python scripts/connect_wifi_device.py --ip 192.168.1.3:40333
```

**步骤 3: 运行批量处理**
```bash
python scripts/batch_processor.py --input 智家通通收费标准.xlsx
```

**步骤 4: 查看结果**
自动生成 `智家通通收费标准_answers.xlsx`：
| 问题 | **答案** |
|------|---------|
| 智家通通的收费标准是什么？ | 智家通通是中国移动推出的... |
| 如何办理智家通通套餐？ | 可以通过以下方式办理... |
| 智家通通支持哪些功能？ | 支持视频通话、屏幕共享... |

---

## 🎯 最佳实践

### 1. 开发测试流程
```bash
# 先用单任务测试命令
python scripts/single_task.py "打开微信"

# 确认无误后批量处理
python scripts/batch_processor.py --input 问题.xlsx
```

### 2. 多设备加速
- 连接多个设备（USB + WiFi 混合）
- 配置 `config.json` 添加多个设备
- 批量处理自动并行执行

### 3. 错误处理
- 失败的问题会记录错误信息
- 可以单独提取失败的问题重试
- 查看详细日志定位问题

---

## 📞 需要帮助？

运行诊断命令：
```bash
# 检查 ADB
adb version

# 检查设备
adb devices

# 查看工具帮助
python scripts/single_task.py --help
python scripts/batch_processor.py --help
python scripts/connect_wifi_device.py --help
python scripts/install_usb_keyboard.py --help
```

---

**就这么简单！四个工具满足所有需求！** 🎉
