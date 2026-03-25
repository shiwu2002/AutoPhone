# MainAgent - 主 Agent 任务编排系统

主 Agent 负责接收用户指令，调用 Skill（子 Agent）执行手机操作，然后处理结果并操作文档。

## 主 Agent 职责边界

**主 Agent 负责：**
- ✅ 任务编排：分析任务类型，分发到相应的 Skill
- ✅ Skill 调用：调用已注册的 Skill 执行具体操作
- ✅ Excel 操作：读取问题、写入答案
- ✅ 结果汇报：汇总执行结果并返回

**主 Agent 不负责：**
- ❌ 直接执行手机操作（由 Skill/子 Agent 完成）
- ❌ 通用手机操作（需要专门的 Skill 支持）

## 项目结构

```
mainAgent/
├── __init__.py          # 包初始化
├── agent.py             # MasterAgent 类（任务编排核心）
├── main.py              # 命令行入口
├── skills.py            # Skill 注册表
├── skills_liantong.py   # 联通客服 Skill（子 Agent）
├── skills_excel.py      # Excel 操作 Skill
├── skill_loader.py      # Skill 加载器
├── utils/
│   ├── __init__.py
│   └── logger.py        # 日志工具
└── README.md
```

## 快速开始

### 运行方式

**方式 1: 直接运行**
```bash
cd e:\Python\AutoPhone\mainAgent
python main.py
```

**方式 2: 模块方式**
```bash
cd e:\Python\AutoPhone
python -m mainAgent.main
```

**方式 3: 在项目根目录**
```bash
cd e:\Python\AutoPhone
python mainAgent/main.py
```

### 单个问题查询
```bash
# 交互式模式
python main.py

# 直接执行
python main.py -t "查询联通安全管家的功能"

# 直接调用 Skill
python main.py -s liantong_ai_query --skill-args '{"question":"联通安全管家有哪些功能？"}'
```

### Excel 批量处理
```bash
python main.py -t "处理 questions.xlsx 中的所有问题"
```

### 在代码中使用
```python
from mainAgent.agent import MasterAgent

agent = MasterAgent()

# 单个查询
result = agent.execute_task("查询联通宽带资费")
print(result)

# 直接调用 Skill
result = agent.call_skill("liantong_ai_query", question="5G 套餐有哪些档位？")
print(result["answer"])
```

## 可用 Skills

| Skill ID | 名称 | 说明 |
|----------|------|------|
| `liantong_ai_query` | 联通 AI 客服问答 | 打开联通 APP→点击客服→发送问题→返回 AI 回复 |
| `get_excel_question` | 从 Excel 读取问题 | 获取下一道待处理的问题及行号 |
| `write_excel_answer` | 将答案写入 Excel | 将答案写入指定行 |
| `execute_excel_batch` | Excel 批量执行 | 获取所有待处理问题列表 |

**注意：** 主 Agent 仅支持联通客服相关的手机操作。如需支持其他应用的操作，需要添加专门的 Skill。

## 架构说明

```
┌─────────────────────────────────────────┐
│          主 Agent (MasterAgent)          │
│  - 负责任务编排                          │
│  - 操作 Excel 文档                        │
│  - 调用 Skill 执行手机操作                │
└─────────────────┬───────────────────────┘
                  │ 调用
                  ▼
┌─────────────────────────────────────────┐
│  Skill（封装完整的手机操作流程）          │
│  - liantong_ai_query: 联通 AI 客服问答    │
│  - get_excel_question: 从 Excel 读取问题  │
│  - write_excel_answer: 将答案写入 Excel   │
│  - mobile_app_operation: 通用手机操作    │
└─────────────────┬───────────────────────┘
                  │ 执行
                  ▼
          ┌───────────────┐
          │   手机设备    │
          │ (通过 ADB 控制) │
          └───────────────┘
```
