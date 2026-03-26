# PhoneAgent Skills API 文档

## 概述

PhoneAgent Skills 是一个基于技能书（SkillBook）和子技能（SubSkill）的自动化系统。它允许你通过配置化的方式定义和执行各种手机自动化任务。

## 架构

```
SkillBook（技能书）
├── SubSkill 1（子技能）- 提示词模板 + 输入输出配置
├── SubSkill 2（子技能）- 提示词模板 + 输入输出配置
└── SubSkill 3（子技能）- ...
```

## 技能书列表

### 1. PhoneAgent 工具集 (phoneagent_tools) 🤖

PhoneAgent 核心功能技能集，包含 ADB 连接、模型配置、任务执行等功能。

#### 子技能列表：

| ID | 名称 | 描述 |
|----|------|------|
| `adb_connect` | ADB 设备连接 | 连接 ADB 设备，支持 USB 和无线连接 |
| `adb_disconnect` | ADB 设备断开 | 断开 ADB 设备连接 |
| `model_config` | 模型配置管理 | 配置和管理 AI 模型参数 |
| `execute_task` | 执行手机任务 | 在手机上执行自动化任务 |
| `query_history` | 查询历史记录 | 查询任务执行历史记录 |
| `get_stats` | 获取统计信息 | 获取任务执行的统计信息 |
| `clear_history` | 清空历史记录 | 清空所有任务历史记录 |
| `excel_preview` | Excel 文件预览 | 预览 Excel 文件内容和列信息 |
| `excel_batch` | Excel 批量任务 | 批量执行 Excel 中的任务 |

### 2. 联通客服 (liantong_service) 📞

中国联通 APP 相关操作技能。

#### 子技能列表：

| ID | 名称 | 描述 |
|----|------|------|
| `query_ai_cs` | AI 客服问答 | 通过联通 APP 的 AI 客服进行咨询问答 |

### 3. 手机通用操作 (mobile_operations) 📱

手机通用操作技能，如打开 APP、输入文字、滑动等。

#### 子技能列表：

| ID | 名称 | 描述 |
|----|------|------|
| `open_app` | 打开应用 | 打开指定的手机应用 |
| `input_text` | 输入文字 | 在当前焦点的输入框中输入文字 |
| `tap_coordinate` | 点击坐标 | 点击屏幕上的指定坐标 |

### 4. Excel 管理 (excel_management) 📊

Excel 文件操作和数据管理技能。

#### 子技能列表：

| ID | 名称 | 描述 |
|----|------|------|
| `read_excel` | 读取 Excel | 读取 Excel 文件内容 |
| `write_excel` | 写入 Excel | 将数据写入 Excel 文件 |

---

## HTTP API 端点

### 获取技能书列表

**GET** `/skills/books`

响应示例：
```json
{
  "success": true,
  "count": 4,
  "books": [
    {
      "id": "phoneagent_tools",
      "name": "PhoneAgent 工具集",
      "description": "PhoneAgent 核心功能技能集...",
      "icon": "🤖",
      "version": "1.0.0",
      "sub_skills": [
        {
          "id": "adb_connect",
          "name": "ADB 设备连接",
          "description": "连接 ADB 设备..."
        }
      ]
    }
  ]
}
```

### 获取技能书详情

**GET** `/skills/book/<book_id>`

响应示例：
```json
{
  "success": true,
  "book": {
    "id": "liantong_service",
    "name": "联通客服",
    "sub_skills": [
      {
        "id": "query_ai_cs",
        "name": "AI 客服问答",
        "prompt_template": "你的任务是通过联通 APP 的 AI 客服来回答问题...\n\n问题：{question}",
        "input_params": [
          {
            "name": "question",
            "type": "str",
            "description": "要提问的问题",
            "required": true
          }
        ],
        "output_config": {
          "field": "answer",
          "type": "text",
          "description": "AI 客服的回复内容"
        }
      }
    ]
  }
}
```

### 执行子技能

**POST** `/skills/execute`

请求体：
```json
{
  "book_id": "liantong_service",
  "sub_skill_id": "query_ai_cs",
  "params": {
    "question": "联通智家是什么？"
  }
}
```

响应示例：
```json
{
  "success": true,
  "answer": "联通智家是中国联通推出的智能家居服务...",
  "message": "执行成功"
}
```

### 构建技能提示词（调试用）

**POST** `/skills/build_prompt`

请求体：
```json
{
  "book_id": "liantong_service",
  "sub_skill_id": "query_ai_cs",
  "params": {
    "question": "联通智家是什么？"
  }
}
```

响应示例：
```json
{
  "success": true,
  "prompt": "你的任务是通过联通 APP 的 AI 客服来回答问题。\n\n问题：联通智家是什么？\n\n流程：..."
}
```

---

## Python 使用示例

### 1. 列出所有技能书

```python
from mainAgent.skill_engine import get_manager

manager = get_manager()
books = manager.list_books()

for book_id in books:
    book = manager.get_book(book_id)
    print(f"{book.icon} {book.name}: {len(book.sub_skills)} 个子技能")
```

### 2. 构建带占位符的提示词

```python
# 构建提示词，{question} 占位符会被替换为实际值
prompt = manager.build_prompt(
    'liantong_service',
    'query_ai_cs',
    question='联通智家是什么？'
)
print(prompt)
# 输出：你的任务是通过联通 APP 的 AI 客服来回答问题。
#       问题：联通智家是什么？
#       流程：...
```

### 3. 执行子技能

```python
# 执行技能并获取 JSON 结果
result = manager.execute(
    'phoneagent_tools',
    'query_history',
    limit=5,
    success_filter='all'
)
print(result)
# 输出：{"success": true, "count": 5, "records": [...]}
```

### 4. 使用 HTTP API 执行技能

```bash
# 执行联通客服问答
curl -X POST http://localhost:5001/skills/execute \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": "liantong_service",
    "sub_skill_id": "query_ai_cs",
    "params": {
      "question": "联通智家是什么？"
    }
  }'
```

### 5. 完整工作流示例

```python
from mainAgent.skill_engine import get_manager

manager = get_manager()

# 1. 连接设备
result = manager.execute(
    'phoneagent_tools',
    'adb_connect',
    connection_request='连接设备'
)

# 2. 执行任务
result = manager.execute(
    'phoneagent_tools',
    'execute_task',
    task='打开抖音搜索猫咪视频',
    model_provider='local',
    model_name='qwen3.5:4b',
    max_steps=30
)

# 3. 查询历史记录
result = manager.execute(
    'phoneagent_tools',
    'query_history',
    limit=1
)

# 4. 获取统计信息
result = manager.execute(
    'phoneagent_tools',
    'get_stats'
)
print(f"总任务数：{result['statistics']['total_tasks']}")
print(f"成功率：{result['statistics']['success_rate']}%")
```

---

## 占位符说明

在技能提示词模板中，可以使用 `{参数名}` 形式的占位符。执行时，这些占位符会被替换为实际传入的参数值。

### 示例

```json
{
  "prompt_template": "你的任务是打开应用。\n\n应用名称：{app_name}",
  "input_params": [
    {
      "name": "app_name",
      "type": "str",
      "description": "应用名称",
      "required": true
    }
  ]
}
```

执行时：
```python
prompt = manager.build_prompt(
    'mobile_operations',
    'open_app',
    app_name='微信'
)
# 结果："你的任务是打开应用。\n\n应用名称：微信"
```

---

## JSON 输入输出规范

### 输入参数

每个子技能可以定义多个输入参数：

```json
{
  "input_params": [
    {
      "name": "task",
      "type": "str",
      "description": "任务描述",
      "required": true
    },
    {
      "name": "max_steps",
      "type": "int",
      "description": "最大执行步数",
      "required": false,
      "default": 100
    }
  ]
}
```

### 输出配置

每个子技能可以定义输出配置：

```json
{
  "output_config": {
    "field": "answer",
    "type": "text",
    "description": "AI 客服的回复内容"
  }
}
```

### 返回格式

技能执行结果始终以 JSON 格式返回：

```json
{
  "success": true,
  "answer": "联通智家是...",
  "message": "执行成功"
}
```

失败时：
```json
{
  "success": false,
  "error": "错误原因"
}
```

---

## 配置文件

技能书配置保存在 `skill_books.json` 文件中。

### 添加新的技能书

1. 编辑 `skill_books.json`
2. 在 `books` 数组中添加新的技能书定义
3. 定义子技能及其提示词模板、输入输出参数

### 添加新的子技能

```json
{
  "id": "my_new_skill",
  "name": "我的新技能",
  "description": "技能描述",
  "prompt_template": "你的任务是...\n\n参数：{param1}",
  "input_params": [
    {
      "name": "param1",
      "type": "str",
      "description": "参数 1",
      "required": true
    }
  ],
  "output_config": {
    "field": "result",
    "type": "json",
    "description": "执行结果"
  },
  "timeout": 60,
  "max_steps": 10
}
```

---

## 故障排查

### 技能引擎无法加载

确保 `skill_books.json` 文件存在且格式正确。

```bash
python -c "from mainAgent.skill_engine import get_manager; print(get_manager().list_books())"
```

### 占位符未替换

检查参数名是否与 `input_params` 中定义的名称一致。

### JSON 格式错误

确保提示词模板中的 JSON 字符串使用转义引号：`\"` 而不是 `"`。
