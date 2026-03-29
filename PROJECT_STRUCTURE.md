# Phone Agent - 项目结构说明

## 目录结构

```
AutoPhone/
├── main.py                  # 主入口文件（提供 CLI 和 Programmatic API）
├── server.py                # Web 服务器
├── config.json              # 配置文件
├── requirements.txt         # Python 依赖
├── README.md               # 项目说明
├── API_GUIDE.md            # API 使用指南
│
├── phone_agent/            # 核心包
│   ├── __init__.py
│   ├── agent.py            # PhoneAgent 主类
│   ├── batch_runner.py     # 批量执行器
│   ├── device_factory.py   # 设备工厂
│   │
│   ├── actions/            # 动作处理
│   │   ├── handler.py
│   │   └── sets/
│   │
│   ├── adb/                # ADB 相关
│   │   ├── connection.py
│   │   ├── device.py
│   │   ├── input.py
│   │   └── screenshot.py
│   │
│   ├── config/             # 配置管理
│   │   ├── apps.py
│   │   ├── env.py
│   │   ├── i18n.py
│   │   ├── prompts.py
│   │   └── timing.py
│   │
│   ├── history/            # 历史记录
│   │   └── manager.py
│   │
│   ├── model/              # 模型客户端
│   │   └── client.py
│   │
│   └── utils/              # 工具函数
│       ├── logger.py
│       └── resolution.py
│
├── bin/                    # 辅助工具
│   ├── excel_task.py       # Excel 批量任务
│   └── install_keyboard.py # 安装键盘
│
├── examples/               # 示例代码
│   ├── api_usage.py        # API 使用示例
│   ├── web_server.py       # Web 服务集成示例
│   └── integration_*.py    # 其他集成示例
│
├── tests/                  # 测试代码
│   ├── test_api.py         # API 测试
│   └── test_*.py           # 其他测试
│
└── templates/              # 模板文件
    ├── index.html
    └── excel-batch.js
```

## 主要模块说明

### 1. main.py - 主入口

**功能**：
- 提供 CLI 命令行界面
- 提供 Programmatic API 供其他项目调用
- 支持单个任务执行和批量任务执行

**主要类**：
- `PhoneAgentAPI` - 主接口类
- `TaskResult` - 单个任务结果
- `BatchTaskResult` - 批量任务结果

**使用方式**：
```python
from main import PhoneAgentAPI

api = PhoneAgentAPI()
result = api.run_task("打开微信")
```

### 2. phone_agent.agent - Agent 核心

**功能**：
- AI 驱动的自动化代理
- 基于 VLM 分析屏幕内容
- 决策和执行操作

**主要类**：
- `PhoneAgent` - 主 Agent 类
- `AgentConfig` - Agent 配置

### 3. phone_agent.batch_runner - 批量执行器

**功能**：
- 从 Excel/TXT 读取问题
- 批量执行并保存结果
- 支持进度保存和断点续跑

**主要类**：
- `BatchQuestionRunner` - 批量执行器
- `BatchConfig` - 批量配置
- `BatchResult` - 批量结果

### 4. bin/excel_task.py - Excel 任务工具

**功能**：
- 读取 Excel/TXT 文件
- 批量执行问题
- 支持答案对比和截图嵌入

**CLI 使用**：
```bash
python bin/excel_task.py --file questions.xlsx --task "请回答：{content}" --mode batch
```

## 导入路径

### 推荐导入方式

```python
# 从 main.py 导入 API
from main import PhoneAgentAPI, ModelConfig, AgentConfig

# 从 phone_agent 包导入核心类
from phone_agent import PhoneAgent
from phone_agent.agent import AgentConfig
from phone_agent.model import ModelConfig

# 从子模块导入工具类
from phone_agent.device_factory import get_device_factory
from phone_agent.utils.logger import setup_logger
```

### 避免的导入方式

```python
# ❌ 不要直接导入内部实现细节
from phone_agent.actions.handler import parse_action

# ✅ 应该通过公共 API 使用
from main import PhoneAgentAPI
```

## 配置管理

### config.json 结构

```json
{
  "model": {
    "provider": "local",
    "base_url": "http://localhost:11434/v1",
    "model_name": "qwen3.5:4b",
    "api_key": "ollama"
  },
  "agent": {
    "max_steps": 50,
    "verbose": true,
    "lang": "cn"
  },
  "timing": {
    "app_launch_delay": 2000,
    "input_delay": 500
  }
}
```

### 程序化配置

```python
from main import PhoneAgentAPI, ModelConfig, AgentConfig

# 方式 1: 使用配置文件
api = PhoneAgentAPI(config_path="config.json")

# 方式 2: 完全程序化配置
model_config = ModelConfig(
    base_url="http://localhost:11434/v1",
    model_name="qwen3.5:4b",
    api_key="ollama"
)

agent_config = AgentConfig(
    max_steps=30,
    verbose=True
)

api = PhoneAgentAPI(
    model_config=model_config,
    agent_config=agent_config
)
```

## 最佳实践

### 1. API 使用

```python
# ✅ 推荐：复用 API 实例
api = PhoneAgentAPI()
for task in tasks:
    result = api.run_task(task)

# ❌ 不推荐：重复创建实例
for task in tasks:
    api = PhoneAgentAPI()
    result = api.run_task(task)
```

### 2. 错误处理

```python
# ✅ 推荐：完整的错误处理
try:
    result = api.run_task(task)
    if result.success:
        print(f"成功：{result.answer}")
    else:
        print(f"失败：{result.error}")
except Exception as e:
    print(f"异常：{e}")
```

### 3. 批量任务

```python
# ✅ 推荐：先小批量测试
api = PhoneAgentAPI()

# 先测试 1 个问题
result = api.run_batch_from_file(
    file_path="questions.xlsx",
    max_questions=1
)

# 确认正常后再全量执行
if result.success_count > 0:
    result = api.run_batch_from_file(
        file_path="questions.xlsx",
        max_questions=0  # 全部执行
    )
```

### 4. 日志记录

```python
# ✅ 推荐：使用内置日志
from phone_agent.utils.logger import setup_logger

logger = setup_logger(__name__)
logger.info("任务开始")
```

## 扩展开发

### 添加新的 Action

1. 在 `phone_agent/actions/sets/` 目录下创建新模块
2. 实现 action 函数
3. 在 `handler.py` 中注册

### 添加新的设备类型

1. 在 `phone_agent/device_factory.py` 中添加新设备类型
2. 实现相应的设备接口
3. 更新 `DeviceType` 枚举

### 自定义模型提供商

1. 继承 `ModelClient` 类
2. 实现 `request` 方法
3. 在配置中添加新 provider

## 测试

### 运行测试

```bash
# 运行 API 测试
python tests/test_api.py

# 运行所有测试
pytest tests/
```

### 编写测试

```python
# tests/test_custom.py
import unittest
from main import PhoneAgentAPI

class TestPhoneAgent(unittest.TestCase):
    def test_single_task(self):
        api = PhoneAgentAPI()
        result = api.run_task("查看时间")
        self.assertTrue(result.success)

if __name__ == '__main__':
    unittest.main()
```

## 部署

### 开发环境

```bash
# 安装依赖
pip install -r requirements.txt

# 运行 CLI
python main.py --task "打开微信"

# 运行 Web 服务
python examples/web_server.py
```

### 生产环境

```bash
# 使用 gunicorn 运行 Web 服务
gunicorn -w 4 -b 0.0.0.0:5000 examples.web_server:app

# 或使用 uvicorn (ASGI)
uvicorn examples.web_server:app --host 0.0.0.0 --port 5000
```

## 常见问题

### Q: 如何在其他项目中集成？

A: 参考 `examples/api_usage.py`，主要步骤：
1. 安装依赖
2. 导入 `PhoneAgentAPI`
3. 初始化并调用方法

### Q: 如何自定义配置？

A: 两种方式：
1. 修改 `config.json`
2. 程序化创建 `ModelConfig` 和 `AgentConfig`

### Q: 批量执行中断后如何继续？

A: `BatchQuestionRunner` 支持断点续跑，会自动跳过已有答案的问题。

### Q: 如何调试？

A: 设置 `verbose=True` 查看详细执行过程。
