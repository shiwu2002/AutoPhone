# AutoPhone

AutoPhone 是一个基于 AI 的手机自动化代理系统，旨在通过自然语言指令实现对 Android 设备的智能操作。该项目为计算机科学与技术专业的毕业设计项目，利用大模型理解用户意图并驱动 ADB 完成真实设备上的任务。

## 特性

- **自然语言控制**: 支持中文描述任务，如"打开微信给张三发消息"。
- **多模式运行**: 支持 CLI 模式和 HTTP API 模式。
- **设备管理**: 支持连接有线和 WiFi 设备。
- **动作执行**: 启动应用、点击控件、滑动屏幕、输入文本等。
- **上下文感知**: 截图 + 屏幕信息分析 → VLM 决策 → 执行 → 循环反馈。

## 快速开始

### 一键安装

如果您已经克隆了项目：

```bash
./install.sh
```

或者从网络直接安装（无需事先下载项目）：

```bash
curl -fsSL https://raw.githubusercontent.com/shiwu2002/AutoPhone/main/install_from_network.sh -o install_autophone.sh
chmod +x install_autophone.sh
./install_autophone.sh
```

### 使用示例

```bash
# 查看帮助
autophone --help

# 执行单个任务
autophone run "打开微信"

# 批量处理 Excel 文件
autophone batch -i 问题.xlsx -o 答案.xlsx

# 列出已连接的设备
autophone wifi list

# 连接 WiFi 设备
autophone wifi connect --ip 192.168.1.100

# 安装 ADB 键盘
autophone keyboard install

# 管理配置
autophone config get model.provider
autophone config set model.provider openai
```

### 更新

要更新到最新版本，只需重新运行安装脚本：

```bash
./install.sh  # 如果在项目目录中
# 或
./install_from_network.sh  # 从网络安装
```

## 系统要求

- Python 3.11 或更高版本
- ADB (Android Debug Bridge)
- 一台已启用 USB 调试的 Android 设备

## 技术架构

```
┌─────────────────┐
│   用户界面层     │
│  CLI / HTTP API │
└────────┬────────┘
         │
┌────────▼────────┐
│   代理核心层     │
│  PhoneAgent     │
│  AgentConfig    │
└────────┬────────┘
         │
┌────────▼────────┐
│   动作处理层     │
│  ActionHandler  │
└────────┬────────┘
         │
┌────────▼────────┐
│   设备抽象层     │
│ DeviceFactory   │
│ ADB Wrapper     │
└────────┬────────┘
         │
┌────────▼────────┐
│   物理设备层     │
│  Android Device │
└─────────────────┘
```

## 开发

如果您想参与开发：

1. 克隆项目
2. 创建虚拟环境
3. 安装依赖

```bash
git clone https://github.com/shiwu2002/AutoPhone.git
cd AutoPhone
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
pip install -e .
```

## 许可证

MIT
