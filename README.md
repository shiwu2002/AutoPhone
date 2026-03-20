# PhoneAgent - AI 驱动的手机自动化代理

让手机操作更简单！通过自然语言描述任务，AI 自动帮您完成。

## 🎯 它能做什么？

- **发消息**："打开微信给张三发消息：晚上好"
- **点外卖**："帮我点一杯咖啡，要拿铁"
- **刷社交媒体**："打开抖音，看看最近的热门视频"
- **购物**："在淘宝上搜索运动鞋"
- **批量任务**：从 Excel 读取问题列表，自动执行并导出结果
- **更多**：支持各种手机操作

## ⚡ 5 分钟快速上手

## 🏗️ 技术架构

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

### 模块划分

| 模块 | 职责 | 关键文件 |
|------|------|----------|
| **CLI 接口** | 命令行交互、参数解析 | `main.py` |
| **HTTP Server** | RESTful API、跨域支持 | `server.py` |
| **Agent Core** | 任务编排、上下文管理 | `phone_agent/agent.py` |
| **Model Client** | LLM API 调用、消息构建 | `phone_agent/model/client.py` |
| **Action Handler** | 动作解析与执行 | `phone_agent/actions/handler.py` |
| **Device Layer** | ADB 命令封装、设备管理 | `phone_agent/adb/` |
| **Configuration** | 系统提示词、国际化、时序配置 | `phone_agent/config/` |

### 数据流

```
用户任务 → 截图 + 屏幕信息 → VLM 分析 → 动作决策 → ADB 执行 → 结果反馈
                ↑                                              │
                └────────────── 循环直到完成 ──────────────────┘
```

## 🚀 快速开始

### 第一步：检查环境

**需要的东西：**
1. Python 3.10+ （检查：`python3 --version`）
2. ADB 工具 （检查：`adb version`）
3. Android 手机或模拟器
4. 稳定的网络（用于访问 AI 模型）

**如果没有 ADB？**
```bash
# macOS
brew install android-platform-tools

# Linux
sudo apt install android-tools-adb

# Windows
# 下载：https://developer.android.com/studio/releases/platform-tools
```

### 第二步：安装项目

```bash
# 1. 下载项目
git clone https://github.com/yourusername/AutoPhone.git
cd AutoPhone

# 2. 安装依赖（包括 Excel 支持）
pip3 install -r requirements.txt
```

### 第三步：连接手机

**有线连接（推荐新手）：**
```bash
# 1. 手机开启 USB 调试
# 设置 > 关于手机 > 连续点击"版本号"7 次 > 返回设置 > 开发者选项 > USB 调试

# 2. 连接电脑
adb devices

# 看到设备 ID 表示成功
```

**无线连接（可选）：**
```bash
adb connect 192.168.1.100:5555  # 替换为您设备的 IP
```

### 第四步：配置 AI 模型

#### 方式一：使用远程 API（推荐新手）

编辑 `config.json` 文件：
```json
{
  "model": {
    "type": "remote",
    "base_url": "https://api-inference.modelscope.cn/v1",
    "model_name": "ZhipuAI/AutoGLM-Phone-9B",
    "api_key": "您的 API 密钥"
  }
}
```

**获取 API 密钥：**
- 使用 ModelScope：https://modelscope.cn/

#### 方式二：使用本地模型（Ollama）

1. **安装 Ollama**

```bash
# macOS
brew install ollama

# Windows
# 下载：https://ollama.com/download

# Linux
curl -fsSL https://ollama.com/install.sh | sh
```

2. **启动 Ollama 服务**

```bash
ollama serve
```

3. **拉取视觉语言模型**

```bash
# 推荐模型：qwen3.5（支持视觉理解，内置思考能力）
ollama pull qwen3.5:4b
```

4. **使用配置向导（推荐）**

运行以下命令进入交互式配置：
```bash
python main.py --config
```

配置向导将引导您完成：
- 选择模型类型（本地 Ollama / 远程 API）
- 选择或输入模型名称
- 启用思考功能（本地模型专属，显示推理过程）
- 设置最大执行步数（0=无限）
- 选择界面语言
- 配置自动连接设备
- **配置坐标优化参数**（针对小参数模型）

5. **手动配置 config.json（可选）**

```json
{
  "model": {
    "type": "local",
    "base_url": "http://localhost:11434/v1",
    "model_name": "qwen3.5:4b",
    "api_key": "ollama",
    "use_thinking": true
  },
  "agent": {
    "max_steps": 0,
    "verbose": true,
    "lang": "cn",
    "device_id": null
  },
  "device": {
    "type": "adb",
    "auto_connect": true
  },
  "coordinate_optimization": {
    "enabled": true,
    "click_offset_x": 8,
    "click_offset_y": 8,
    "use_region_click": true,
    "min_click_region": 30
  }
}
```

**配置说明：**

| 配置项 | 说明 | 推荐值 |
|--------|------|--------|
| `model.type` | 模型类型：`local` 本地 / `remote` 远程 | `local` |
| `model.base_url` | Ollama 服务地址 | `http://localhost:11434/v1` |
| `model.model_name` | 模型名称 | `qwen3.5:4b` |
| `model.use_thinking` | 启用思考过程显示（仅本地模型） | `true` |
| `agent.max_steps` | 单任务最大执行步数（0=无限） | `0` |
| `agent.verbose` | 显示详细执行日志 | `true` |
| `agent.lang` | 界面语言：`cn` 中文 / `en` 英文 | `cn` |
| `device.auto_connect` | 启动时自动连接设备 | `true` |
| `coordinate_optimization.enabled` | 启用坐标优化（小参数模型建议开启） | `true` |
| `coordinate_optimization.click_offset_x` | X 方向点击偏移（像素） | `8` |
| `coordinate_optimization.use_region_click` | 使用区域点击（提高容错率） | `true` |

### 第五步：运行！

#### 方式一：命令行交互（推荐新手）

```bash
python3 main.py
```

然后输入任务，例如：
```
Enter your task: 打开微信并给张三发消息
```

#### 方式二：直接执行任务

```bash
python3 main.py "打开抖音搜索猫咪视频"
```

#### 方式三：Web 界面（最直观）

```bash
python3 server.py
```

浏览器打开：**http://localhost:5000**

可以看到：
- 📊 任务执行面板
- 📈 统计信息
- 📜 历史记录

---

## 💡 高级功能

### 1. 批量任务（Excel/TXT）

从文件读取问题列表，批量执行并导出结果：

```bash
# 安装依赖（首次使用）
pip install pandas openpyxl

# 基本用法
python main.py --batch questions.xlsx --batch-output results.xlsx

# 测试前 3 个问题
python main.py --batch questions.xlsx --max-questions 3 --verbose

# 断点续跑（跳过已有答案）
python main.py --batch results.xlsx --skip-existing
```

**Excel 文件格式：**

| 问题 | 答案 | 截图路径 | 状态 |
|------|------|----------|------|
| 打开微信并查看最后一条消息 | | | |
| 在淘宝搜索 iPhone 15 | | | |

执行后自动填充答案、截图路径和状态。

### 2. Excel 任务执行器

读取 Excel 内容，让智能体在手机上执行相关任务：

```bash
# 读取 Excel，打开微信发送给某人
python excel_task.py --file 工作簿 2.xlsx --task "打开微信，给峰峰峰回路转发送文档里的所有问题"

# 指定列名
python excel_task.py --file questions.xlsx --column 问题 --task "打开微信，把所有问题发给张三"

# 先预览内容
python excel_task.py --file 工作簿 2.xlsx --preview
```

### 3. 坐标优化（小参数模型）

针对小参数模型（如 Qwen3.5-4B/8B）定位不准的问题：

```bash
# 运行测试查看优化效果
python test_coordinate_optimization.py
```

详细文档见：[COORDINATE_OPTIMIZATION.md](COORDINATE_OPTIMIZATION.md)

---

## 🔧 常用命令

| 命令 | 说明 |
|------|------|
| `python main.py` | 交互模式 |
| `python main.py "任务描述"` | 直接执行任务 |
| `python main.py --config` | 配置向导 |
| `python main.py --list-devices` | 查看设备 |
| `python main.py --list-apps` | 查看支持的应用 |
| `python main.py --batch 文件.xlsx` | 批量执行任务 |
| `python excel_task.py --file 文件.xlsx --task "任务"` | Excel 任务执行 |
| `python test_coordinate_optimization.py` | 测试坐标优化 |

---

## 📖 文档

| 文档 | 说明 |
|------|------|
| [BATCH_USAGE.md](BATCH_USAGE.md) | 批量任务使用指南 |
| [COORDINATE_OPTIMIZATION.md](COORDINATE_OPTIMIZATION.md) | 坐标优化说明 |

---

## 🔧 常见问题

**Q1: 找不到设备？**
```bash
# 解决：重启 ADB
adb kill-server
adb start-server
adb devices
```

**Q2: ADB 键盘无法输入？**
- 确保已安装：`adb install ADBKeyboard.apk`
- 在手机上启用：设置 > 语言输入法 > 虚拟键盘 > ADB Keyboard

**Q3: 连接 AI 模型失败？**
- 检查 `config.json` 中的 `api_key` 是否正确
- 确认网络正常
- 尝试更换模型地址

**Q4: 任务执行失败？**
- 检查手机屏幕是否解锁
- 确保目标应用已安装
- 查看详细错误信息

**Q5: 本地模型不显示思考过程？**
- 确保 `model.use_thinking` 设置为 `true`
- 确保使用 Ollama 本地模型而非远程 API
- 检查 `agent.verbose` 是否为 `true`

**Q6: 小参数模型点击位置不准？**
- 开启坐标优化：`coordinate_optimization.enabled = true`
- 增大偏移量：`click_offset_x = 10`, `click_offset_y = 10`
- 启用区域点击：`use_region_click = true`

**Q7: 批量任务报错 "pandas not installed"？**
```bash
pip install pandas openpyxl
```

---

## 📚 技术架构（可选阅读）

```
用户 → Web 界面/命令行 → AI 分析 → 执行操作 → 反馈结果
```

**核心模块：**
- `main.py` - 命令行入口
- `server.py` - Web 服务器
- `excel_task.py` - Excel 任务执行器
- `phone_agent/batch_runner.py` - 批量任务执行器
- `phone_agent/` - 核心逻辑包

---

## 🙏 致谢

感谢开源社区和所有贡献者！

**毕业设计项目** - 计算机科学与技术专业
*最后更新：2026 年 3 月*
