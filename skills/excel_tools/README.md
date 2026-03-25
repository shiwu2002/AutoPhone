# Excel 工具 Skill

从 Excel 读取问题和写入答案的独立技能包。

## 使用方法

### 方式 1: 直接调用

```python
from skills.excel_tools import get_excel_question, write_excel_answer, execute_excel_batch

# 读取问题
result = get_excel_question(file="questions.xlsx")
print(f"问题：{result['question']}, 行号：{result['row']}")

# 写入答案
result = write_excel_answer(file="questions.xlsx", row=2, answer="这是答案")

# 批量执行
result = execute_excel_batch(file="questions.xlsx", max_questions=10)
print(f"共 {result['total']} 个问题")
```

### 方式 2: 通过主 Agent 调用

```python
from phone_agent import MasterAgent

agent = MasterAgent()

# 读取问题
result = agent.call_skill("get_excel_question", file="questions.xlsx")

# 写入答案
result = agent.call_skill("write_excel_answer", file="questions.xlsx", row=2, answer="答案")
```

## 函数列表

### get_excel_question

从 Excel 读取问题。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| file | str | 是 | - | Excel 文件路径 |
| row | int | 否 | None | 行号（不指定则自动获取待处理的行） |
| question_column | str | 否 | "问题" | 问题列名 |
| answer_column | str | 否 | "答案" | 答案列名 |

### write_excel_answer

将答案写入 Excel。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| file | str | 是 | - | Excel 文件路径 |
| row | int | 是 | - | 行号 |
| answer | str | 是 | - | 答案内容 |
| answer_column | str | 否 | "答案" | 答案列名 |

### execute_excel_batch

批量执行 Excel 中的任务。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| file | str | 是 | - | Excel 文件路径 |
| question_column | str | 否 | "问题" | 问题列名 |
| max_questions | int | 否 | 0 | 最大问题数（0 表示全部） |
| answer_column | str | 否 | "答案" | 答案列名 |

## 钩子事件

此 Skill 会触发以下钩子事件：

- `on_skill_start`: Skill 开始执行时
- `on_skill_complete`: Skill 执行完成时
- `on_skill_error`: Skill 执行失败时
