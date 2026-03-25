# Skills 目录结构说明

## 目录结构

```
AutoPhone/
├── skills/                     # 独立技能包（项目根目录）
│   ├── __init__.py             # 包初始化，导出所有 Skill
│   ├── liantong_ai_query/      # 联通客服问答 Skill
│   │   ├── __init__.py
│   │   ├── skill.py            # 主要执行逻辑
│   │   └── README.md           # 使用说明
│   └── excel_tools/            # Excel 工具 Skill
│       ├── __init__.py
│       ├── skill.py            # 主要执行逻辑
│       └── README.md           # 使用说明
│
├── mainAgent/                  # 主 Agent 任务编排系统
│   ├── __init__.py
│   ├── agent.py                # MasterAgent 类
│   ├── main.py                 # 命令行入口
│   ├── skills.py               # Skill 注册表（使用根目录 skills）
│   └── utils/
│       └── logger.py
│
├── phone_agent/                # 子 Agent 核心（手机操作）
│   ├── agent.py                # PhoneAgent 类
│   ├── hooks.py                # 全局钩子系统
│   └── ...
│
└── hooks_setup.py              # 全局钩子注册示例
```

## 设计原则

### 1. 每个 Skill 独立封装
- 每个 Skill 是一个独立的文件夹
- 包含完整的执行逻辑、配置和文档
- 可以独立测试和部署

### 2. 钩子监控整个系统
- 钩子是全局的 (`phone_agent.hooks`)
- 监控主 Agent、Skill、手机操作的所有关键事件
- 可以在一个地方注册，全局生效

### 3. 职责分离
- **主 Agent**: 任务编排、Skill 调用、Excel 操作、结果汇报
- **Skill**: 执行具体的手机操作流程
- **PhoneAgent**: 底层手机操作（被 Skill 调用）

## 使用方法

### 方式 1: 直接调用 Skill

```python
from skills.liantong_ai_query import execute

result = execute(question="联通安全管家有哪些功能？")
print(result["answer"])
```

### 方式 2: 通过主 Agent 调用

```python
from mainAgent.agent import MasterAgent

agent = MasterAgent()
result = agent.call_skill("liantong_ai_query", question="问题内容")
```

### 方式 3: 注册全局钩子监控

```python
# 在启动时导入 hooks_setup.py
from hooks_setup import setup_global_hooks

setup_global_hooks()

# 现在所有关键事件都会被记录
```

## 可用 Skills

| Skill ID | 文件夹 | 说明 |
|----------|--------|------|
| `liantong_ai_query` | `skills/liantong_ai_query/` | 联通 AI 客服问答 |
| `get_excel_question` | `skills/excel_tools/` | 从 Excel 读取问题 |
| `write_excel_answer` | `skills/excel_tools/` | 将答案写入 Excel |
| `execute_excel_batch` | `skills/excel_tools/` | Excel 批量执行 |

## 添加新 Skill

### 步骤 1: 创建文件夹

```bash
mkdir skills/your_skill_name
```

### 步骤 2: 创建文件结构

```
skills/your_skill_name/
├── __init__.py
├── skill.py      # 主要执行逻辑
└── README.md     # 使用说明
```

### 步骤 3: 编写 skill.py

```python
"""你的 Skill - 说明。"""

from phone_agent.hooks import trigger_hook
from phone_agent.utils.logger import setup_logger

logger = setup_logger(__name__)

SKILL_METADATA = {
    "id": "your_skill_id",
    "name": "你的 Skill 名称",
    "description": "说明",
}

def execute(param1: str, param2: str = "default") -> dict:
    """执行 Skill。"""
    logger.info(f"[{SKILL_METADATA['id']}] 开始执行")

    # 触发开始钩子
    trigger_hook("on_skill_start", skill_id=SKILL_METADATA["id"])

    try:
        # 你的执行逻辑
        result = do_something()

        # 触发完成钩子
        trigger_hook("on_skill_complete", skill_id=SKILL_METADATA["id"], result=result)

        return {"success": True, "result": result}

    except Exception as e:
        # 触发错误钩子
        trigger_hook("on_skill_error", skill_id=SKILL_METADATA["id"], error=str(e))

        return {"success": False, "error": str(e)}
```

### 步骤 4: 更新 skills/__init__.py

```python
from skills.your_skill_name.skill import execute as your_skill_id

__all__ = [
    # ... 现有的
    'your_skill_id',
]
```

### 步骤 5: 更新 mainAgent/skills.py

在 `_register_builtin_skills()` 方法中添加：

```python
from skills.your_skill_name.skill import execute as your_skill_id_execute

self._skills["your_skill_id"] = SkillMetadata(...)
self._handlers["your_skill_id"] = your_skill_id_execute
```

## 钩子系统

### 支持的钩子事件

| 事件 | 触发时机 | 参数 |
|------|----------|------|
| `on_task_start` | 任务开始（主 Agent） | `task` |
| `on_task_end` | 任务结束（主 Agent） | `task`, `result` |
| `on_master_dispatch` | 主 Agent 分发任务 | `task` |
| `on_master_route` | 主 Agent 路由任务 | `task`, `route` |
| `on_skill_start` | Skill 开始执行 | `skill_id`, `**kwargs` |
| `on_skill_complete` | Skill 执行完成 | `skill_id`, `result` |
| `on_skill_error` | Skill 执行失败 | `skill_id`, `error` |
| `on_app_changed` | 应用切换 | `old_app`, `new_app` |
| `on_wait` | 执行 Wait 动作 | `duration` |

### 注册钩子

```python
from phone_agent import register_hook

register_hook("on_skill_start", lambda skill_id, **kwargs: print(f"开始：{skill_id}"))
```

### 触发钩子

```python
from phone_agent import trigger_hook

trigger_hook("on_skill_start", skill_id="liantong_ai_query", question="问题")
```

## 迁移指南

如果你之前使用了旧的技能文件（`mainAgent/skills_liantong.py` 等），请迁移到新的结构：

### 旧的调用方式（已废弃）
```python
from mainAgent.skills_liantong import liantong_ai_query
```

### 新的调用方式
```python
from skills.liantong_ai_query import execute
# 或
from mainAgent.agent import MasterAgent
agent = MasterAgent()
agent.call_skill("liantong_ai_query", question="...")
```
