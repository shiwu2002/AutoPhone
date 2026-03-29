---
name: phone-agent

description: 基于视觉语言模型的手机自动化智能体，支持单任务执行、Excel 批量处理、多设备并行。适用于 Android 设备控制、批量答题、数据标注等场景。触发关键词：手机自动化、ADB、批量处理、Excel 问答。

license: Apache-2.0

compatibility: 适用于 Claude Code 或 OpenCode

---

# Phone Agent - 手机自动化智能体技能包

## 核心目标

提供完整的手机自动化解决方案，通过自然语言指令控制 Android 设备执行各种任务，支持单任务执行和多设备批量并行处理。

## 执行指令

### 1. 环境准备

**检查依赖**：
```bash
# 检查 ADB 是否安装
adb version

# 检查 Python 依赖
python -c "from phone_agent.api import PhoneAgentAPI; print('✅ OK')"
```

**连接设备**：
- USB 方式：用 USB 线连接手机，在手机上授权 USB 调试
- WiFi 方式：`python scripts/connect_wifi_device.py --ip 192.168.1.3:40333`

**验证连接**：
```bash
adb devices
```

### 2. 单任务执行

**命令格式**：
```bash
python scripts/single_task.py "任务描述" [选项]
```

**示例**：
```bash
# 基础用法
python scripts/single_task.py "打开微信"

# 保存截图
python scripts/single_task.py "查看时间" --save-screenshot

# 显示详细过程
python scripts/single_task.py "发送消息给张三" --verbose
```

**输出格式**：
```
🚀 执行任务：打开微信
------------------------------------------------------------

============================================================
✅ 任务成功
答案：已打开微信应用
步数：3
============================================================
```

### 3. Excel 批量处理

**命令格式**：
```bash
python scripts/batch_processor.py --input <Excel 文件> [选项]
```

**Excel 格式要求**：
- 必须包含"问题"列（或使用 `--column` 指定列名）
- 支持 `.xlsx` 和 `.xls` 格式
- 自动在最后一列添加"答案"列

**示例**：
```bash
# 基础用法
python scripts/batch_processor.py --input 问题.xlsx

# 指定输出文件
python scripts/batch_processor.py --input 问题.xlsx --output 答案.xlsx

# 自定义问题列
python scripts/batch_processor.py --input 数据.xlsx --column 题目

# 自定义提问模板
python scripts/batch_processor.py --input 问题.xlsx \
  --template "请详细解答：{content}"
```

**输入 Excel 示例**：
| 问题 |
|------|
| 1+1=? |
| 2+2=? |
| 水的化学式是什么？ |

**输出 Excel 示例**：
| 问题 | **答案** |
|------|---------|
| 1+1=? | 2 |
| 2+2=? | 4 |
| 水的化学式是什么？ | H₂O |

### 4. 多设备并行配置

**编辑 config.json**：
```json
{
  "device": {
    "devices": [
      {"type": "usb", "id": "ABC123DEF456"},
      {
        "type": "wifi",
        "ip": "192.168.1.3",
        "port": 5555
      }
    ]
  }
}
```

**性能参考**：
- 10 个问题，1 台设备：~100 秒
- 10 个问题，2 台设备：~50 秒（2x 加速）
- 10 个问题，3 台设备：~35 秒（3x 加速）

### 5. WiFi 设备连接

**命令格式**：
```bash
python scripts/connect_wifi_device.py --ip <IP 地址> [选项]
```

**示例**：
```bash
# IP 包含端口
python scripts/connect_wifi_device.py --ip 192.168.1.3:40333

# 查看已连接的设备
python scripts/connect_wifi_device.py --list

# 断开设备
python scripts/connect_wifi_device.py --disconnect --ip 192.168.1.3:40333
```

**首次连接步骤**：
1. USB 连接并启用无线调试：`adb usb && adb tcpip 5555`
2. 拔掉 USB 线
3. 运行连接命令
4. 验证：`adb devices`

### 6. 安装 ADB 键盘

**命令格式**：
```bash
python scripts/install_usb_keyboard.py [选项]
```

**示例**：
```bash
# 自动检测并使用第一个设备
python scripts/install_usb_keyboard.py

# 指定设备
python scripts/install_usb_keyboard.py --device ABC123DEF456

# 只验证安装
python scripts/install_usb_keyboard.py --verify-only
```

**安装后操作**：提醒用户在输入法中启用 'ADBKeyboard'

**基础用法**：
```python
from phone_agent.api import PhoneAgentAPI

# 初始化
api = PhoneAgentAPI()

# 单个任务
result = api.run_task("打开微信")
if result.success:
    print(f"答案：{result.answer}")
else:
    print(f"错误：{result.error}")

# 批量任务
questions = ["问题 1", "问题 2", "问题 3"]
batch_result = api.run_batch_parallel(
    questions=questions,
    task_template="请回答：{content}"
)

print(f"成功：{batch_result.success_count}/{batch_result.total}")
print(f"耗时：{batch_result.total_time:.2f}秒")
```

### 7. 故障排查

**问题：没有可用设备**
```bash
# 解决方法
adb devices  # 检查连接
adb kill-server
adb start-server  # 重启 ADB
python scripts/connect_wifi_device.py --ip 192.168.1.3:40333  # 重新连接
```

**问题：WiFi 连接失败**
- 检查手机和电脑是否在同一网络
- 关闭防火墙
- 使用 5GHz WiFi 频段

**问题：Excel 格式错误**
- 确认文件扩展名为 `.xlsx` 或 `.xls`
- 确认包含"问题"列
- 确认问题列有非空内容

## 示例

### 示例 1: 批量答题

**输入文件（考题.xlsx）**：
| 问题 |
|------|
| 水的化学式是什么？ |
| 光合作用的原理？ |
| 量子力学是什么？ |

**执行命令**：
```bash
python scripts/batch_processor.py --input 考题.xlsx
```

**输出文件（考题_answers.xlsx）**：
| 问题 | **答案** |
|------|---------|
| 水的化学式是什么？ | H₂O |
| 光合作用的原理？ | 光合作用是植物利用光能将二氧化碳和水转化为有机物的过程... |
| 量子力学是什么？ | 量子力学是研究微观粒子运动规律的物理学分支... |

### 示例 2: 数据标注

**输入文件（评论数据.xlsx）**：
| 评论内容 |
|----------|
| 这个产品很好用，非常满意 |
| 质量一般，不太推荐 |
| 物流很快，但包装有破损 |

**执行命令**：
```bash
python scripts/batch_processor.py \
  --input 评论数据.xlsx \
  --column 评论内容 \
  --template "请判断情感倾向（正面/负面/中性）：{content}"
```

**输出文件**：
| 评论内容 | **答案** |
|----------|---------|
| 这个产品很好用，非常满意 | 正面 |
| 质量一般，不太推荐 | 负面 |
| 物流很快，但包装有破损 | 中性 |

### 示例 3: 多设备加速

**配置 3 台设备**：
```json
{
  "device": {
    "devices": [
      {"type": "usb", "id": "设备 1"},
      {"type": "wifi", "ip": "192.168.1.3", "port": 5555},
      {"type": "wifi", "ip": "192.168.1.4", "port": 5555}
    ]
  }
}
```

**执行 100 道题**：
```bash
python scripts/batch_processor.py --input 100 题.xlsx --verbose
```

**预期输出**：
```
📖 读取文件：100 题.xlsx
📝 问题列：问题
💾 输出文件：100 题_answers.xlsx
------------------------------------------------------------
✅ 找到 100 个问题
------------------------------------------------------------
🚀 开始批量执行...
发现 3 个设备：[设备 1, 192.168.1.3:5555, 192.168.1.4:5555]

============================================================
✅ 执行完成
   总计：100
   成功：98
   失败：2
   耗时：350.45 秒
============================================================
```

## 可用资源

### 脚本工具

- `scripts/single_task.py` - 单任务执行工具
- `scripts/batch_processor.py` - Excel 批量处理工具
- `scripts/connect_wifi_device.py` - WiFi 设备连接工具
- `scripts/install_usb_keyboard.py` - USB 安装 ADB 键盘工具

### 核心库

- `phone_agent/api.py` - 程序化接口（PhoneAgentAPI）
- `phone_agent/agent.py` - Agent 核心逻辑
- `phone_agent/parallel_executor.py` - 多设备并行执行器
- `phone_agent/device_factory.py` - 设备工厂

### 配置文件

- `config.json` - 全局配置（设备、模型、Agent 设置）

### 参考文档

- `references/SCRIPTS_README.md` - Scripts 工具详细说明
- `references/EXCEL_BATCH_README.md` - Excel 批量处理指南
- `references/DEVICE_CONFIG_GUIDE.md` - 设备配置指南
- `references/CHANGELOG.md` - 更新日志
