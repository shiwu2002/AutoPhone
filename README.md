# AutoPhone CLI

AutoPhone 命令行工具（基于 Typer），提供类似 git/npm 的子命令交互，统一管理以下能力：
- 单任务运行（run）
- Excel 批量任务（batch）
- WiFi 设备连接/断开/列表（wifi）
- 安装/验证 ADB 键盘（keyboard）
- 版本信息（version）

此 CLI 已整合 `scripts/` 下现有脚本功能，参数与行为尽量保持一致：
- scripts/single_task.py → autophone run
- scripts/batch_processor.py → autophone batch
- scripts/connect_wifi_device.py → autophone wifi <list|connect|disconnect>
- scripts/install_usb_keyboard.py → autophone keyboard install

## 快速开始（推荐使用 uv 管理环境）

uv 是一个快速的 Python 包与环境管理工具。

1) 安装 uv（如未安装）
- macOS（Homebrew）：`brew install uv`
- 其他平台参考官方文档：https://docs.astral.sh/uv/

2) 在项目根目录同步依赖
- `uv sync`
  - 会根据 `pyproject.toml` 安装运行所需依赖（包含 Typer、pandas/openpyxl 等）

3) 使用 uv 运行 CLI（无需全局安装）
- 查看帮助：`uv run autophone --help`
- 单任务：`uv run autophone run "打开微信"`
- 批处理：`uv run autophone batch -i 问题.xlsx -o 答案.xlsx -t "请详细解答：{content}"`
- WiFi 连接：`uv run autophone wifi connect --ip 192.168.1.100 --port 5555`
- WiFi 断开：`uv run autophone wifi disconnect --ip 192.168.1.100`
- 列出设备：`uv run autophone wifi list`
- 安装键盘：`uv run autophone keyboard install --device ABC123DEF456`
- 模块形式（等价）：`uv run python -m phone_agent --help`

提示：
- 若仅运行 batch，需要 Excel 能力，请确保 `pandas` 与 `openpyxl` 正确安装（`uv sync` 已包含）。
- `keyboard install` 需要项目根目录存在 `ADBKeyboard.apk`。

## 使用 pip 的替代方案

1) 创建虚拟环境并激活
- macOS/Linux：`python3 -m venv .venv && source .venv/bin/activate`
- Windows：`py -m venv .venv && .venv\Scripts\activate`

2) 安装依赖
- 推荐：`pip install -e .`
  - 会读取 `pyproject.toml`，注册 `autophone` 命令
- 或按需安装：`pip install typer pandas openpyxl Pillow openai requests httpx ollama anthropic flask flask-cors`

3) 运行
- `autophone --help`
- `python -m phone_agent --help`

## 子命令用法

- 单任务运行
  - 命令：`autophone run "<任务描述>" [--save-screenshot] [-v]`
  - 示例：`autophone run "查看时间" --save-screenshot -v`

- Excel 批量处理
  - 命令：`autophone batch --input FILE [--output FILE] [--column 列名] [--template 模板] [-v]`
  - 示例：`autophone batch -i 问题.xlsx -o 答案.xlsx -t "请详细解答：{content}"`

- WiFi 设备
  - 列表：`autophone wifi list`
  - 连接：`autophone wifi connect --ip 192.168.1.100 [--port 5555]`
  - 断开：`autophone wifi disconnect --ip 192.168.1.100 [--port 5555]`

- 安装/验证 ADB 键盘
  - 命令：`autophone keyboard install [--device 设备ID] [--verify-only]`
  - 说明：需要项目根目录存在 `ADBKeyboard.apk`

- 版本
  - 命令：`autophone version`

## 目录与入口

- 入口模块：`phone_agent/cli.py`
- 模块运行：`python -m phone_agent`（由 `phone_agent/__main__.py` 转发到 Typer 应用）
- 打包入口：`pyproject.toml` 中 `project.scripts.autophone = "phone_agent.cli:main"`

## 常见问题

- 运行 `autophone batch` 提示缺少 pandas/openpyxl：
  - 使用 uv：`uv sync`
  - 或使用 pip：`pip install pandas openpyxl`
- `autophone keyboard install` 无法找到 `ADBKeyboard.apk`：
  - 请将 `ADBKeyboard.apk` 放在项目根目录
- 未安装 ADB 或未加入 PATH：
  - 安装 Android Platform Tools，并确保 `adb` 可以在终端直接运行（`adb version` 正常）

## 开发说明

- CLI 使用 Typer 实现子命令与参数解析，结构类似 git/npm。
- 新增子命令：在 `phone_agent/cli.py` 中添加函数并使用 `@app.command()` 或子 Typer。
- 若后续维护版本号，可在 `phone_agent/__init__.py` 中定义 `__version__`，CLI 会尝试读取显示。
