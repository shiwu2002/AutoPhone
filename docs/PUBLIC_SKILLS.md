# PhoneAgent Skills 公开 API 文档

## 概述

PhoneAgent Skills 系统提供两个公开的技能书供用户使用：

1. **问答技能 (qa_skills)** - 面向用户的问答功能
2. **智能体配置 (agent_config)** - 配置问答智能体所需信息

> 注意：PhoneAgent 内部技能（如 adb_connect, tap, input_text 等）不暴露给用户，仅供内部使用。

---

## 1. 问答技能 (qa_skills) 💬

面向用户的问答功能技能，支持通过手机 APP 进行问答。

### 子技能列表

| ID | 名称 | 占位符 | 输出字段 | 描述 |
|----|------|--------|----------|------|
| `liantong_qa` | 联通客服问答 | `{question}` | `answer` | 通过联通 APP 的 AI 客服进行咨询问答 |
| `excel_qa_batch` | Excel 批量问答 | `{file_path}`, `{task_template}`, `{output_file}`, `{column}` | `batch_result` | 从 Excel 读取问题列表，批量执行问答并保存结果 |
| `compare_answer` | 答案对比 | `{ai_answer}`, `{standard_answer}` | `comparison_result` | 对比 AI 答案和标准答案的相似度 |

### 使用示例

#### Python 方式

```python
from mainAgent.skill_engine import get_manager

manager = get_manager()

# 联通客服问答
result = manager.execute('qa_skills', 'liantong_qa',
                         question='联通智家是什么？')
print(f"答案：{result['answer']}")

# Excel 批量问答
result = manager.execute('qa_skills', 'excel_qa_batch',
                         file_path='questions.xlsx',
                         task_template='打开中国联通，回答问题：{question}',
                         output_file='answers.xlsx')
print(f"成功：{result['statistics']['success']}/{result['statistics']['total']}")

# 答案对比
result = manager.execute('qa_skills', 'compare_answer',
                         ai_answer='联通智家是智能家居服务',
                         standard_answer='联通智家是智能家居服务')
print(f"相似度：{result['similarity']}, 正确：{result['is_correct']}")
```

#### HTTP API 方式

```bash
# 联通客服问答
curl -X POST http://localhost:5001/skills/execute \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": "qa_skills",
    "sub_skill_id": "liantong_qa",
    "params": {
      "question": "联通智家是什么？"
    }
  }'

# Excel 批量问答
curl -X POST http://localhost:5001/skills/execute \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": "qa_skills",
    "sub_skill_id": "excel_qa_batch",
    "params": {
      "file_path": "/path/to/questions.xlsx",
      "task_template": "打开中国联通，回答问题：{question}",
      "output_file": "/path/to/answers.xlsx"
    }
  }'

# 答案对比
curl -X POST http://localhost:5001/skills/execute \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": "qa_skills",
    "sub_skill_id": "compare_answer",
    "params": {
      "ai_answer": "联通智家是智能家居服务",
      "standard_answer": "联通智家是智能家居服务"
    }
  }'
```

---

## 2. 智能体配置 (agent_config) ⚙️

配置问答智能体所需的 ADB 连接、模型参数等信息。

### 子技能列表

| ID | 名称 | 占位符 | 输出字段 | 描述 |
|----|------|--------|----------|------|
| `set_device` | 配置设备连接 | `{device_address}`, `{connection_type}` | `device_config` | 配置 ADB 设备连接信息 |
| `set_model` | 配置模型 | `{provider}`, `{model_name}`, `{base_url}`, `{api_key}` | `model_config` | 配置问答智能体使用的 AI 模型 |
| `set_params` | 配置参数 | `{max_steps}`, `{lang}`, `{verbose}` | `params_config` | 配置问答智能体的执行参数 |
| `get_config` | 获取配置 | 无 | `current_config` | 获取当前智能体的配置信息 |

### 使用示例

#### Python 方式

```python
from mainAgent.skill_engine import get_manager

manager = get_manager()

# 获取当前配置
result = manager.execute('agent_config', 'get_config')
print(f"当前配置：{result['config']}")

# 配置设备连接（无线）
result = manager.execute('agent_config', 'set_device',
                         device_address='192.168.1.100:5555',
                         connection_type='wireless')

# 配置模型（使用本地 Ollama）
result = manager.execute('agent_config', 'set_model',
                         provider='local',
                         model_name='qwen3.5:4b',
                         base_url='http://localhost:11434/v1')

# 配置执行参数
result = manager.execute('agent_config', 'set_params',
                         max_steps=50,
                         lang='cn',
                         verbose=True)
```

#### HTTP API 方式

```bash
# 获取当前配置
curl http://localhost:5001/skills/execute \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": "agent_config",
    "sub_skill_id": "get_config"
  }'

# 配置设备连接
curl -X POST http://localhost:5001/skills/execute \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": "agent_config",
    "sub_skill_id": "set_device",
    "params": {
      "device_address": "192.168.1.100:5555",
      "connection_type": "wireless"
    }
  }'

# 配置模型
curl -X POST http://localhost:5001/skills/execute \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": "agent_config",
    "sub_skill_id": "set_model",
    "params": {
      "provider": "local",
      "model_name": "qwen3.5:4b",
      "base_url": "http://localhost:11434/v1"
    }
  }'

# 配置参数
curl -X POST http://localhost:5001/skills/execute \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": "agent_config",
    "sub_skill_id": "set_params",
    "params": {
      "max_steps": 50,
      "lang": "cn",
      "verbose": true
    }
  }'
```

---

## HTTP API 端点

### 获取公开技能书列表

**GET** `/skills/books`

返回所有公开的技能书列表（qa_skills 和 agent_config）。

### 获取技能书详情

**GET** `/skills/book/<book_id>`

返回指定技能书的详细信息，包括所有子技能的提示词模板和参数配置。

### 执行子技能

**POST** `/skills/execute`

请求体：
```json
{
  "book_id": "qa_skills",
  "sub_skill_id": "liantong_qa",
  "params": {
    "question": "联通智家是什么？"
  }
}
```

### 构建技能提示词（调试用）

**POST** `/skills/build_prompt`

用于测试和调试，返回替换占位符后的完整提示词。

---

## 完整工作流示例

### 1. 配置智能体

```bash
# 1.1 配置模型
curl -X POST http://localhost:5001/skills/execute \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": "agent_config",
    "sub_skill_id": "set_model",
    "params": {
      "provider": "local",
      "model_name": "qwen3.5:4b"
    }
  }'

# 1.2 配置设备（如果需要无线连接）
curl -X POST http://localhost:5001/skills/execute \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": "agent_config",
    "sub_skill_id": "set_device",
    "params": {
      "device_address": "192.168.1.100:5555",
      "connection_type": "wireless"
    }
  }'

# 1.3 配置参数
curl -X POST http://localhost:5001/skills/execute \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": "agent_config",
    "sub_skill_id": "set_params",
    "params": {
      "max_steps": 50,
      "verbose": true
    }
  }'
```

### 2. 执行问答

```bash
# 2.1 单个问题问答
curl -X POST http://localhost:5001/skills/execute \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": "qa_skills",
    "sub_skill_id": "liantong_qa",
    "params": {
      "question": "联通安全管家有哪些功能？"
    }
  }'

# 2.2 批量问答
curl -X POST http://localhost:5001/skills/execute \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": "qa_skills",
    "sub_skill_id": "excel_qa_batch",
    "params": {
      "file_path": "/path/to/questions.xlsx",
      "task_template": "打开中国联通，回答问题：{question}",
      "output_file": "/path/to/answers.xlsx"
    }
  }'

# 2.3 对比答案
curl -X POST http://localhost:5001/skills/execute \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": "qa_skills",
    "sub_skill_id": "compare_answer",
    "params": {
      "ai_answer": "联通安全管家提供骚扰电话拦截、垃圾短信过滤等服务",
      "standard_answer": "联通安全管家提供骚扰拦截、垃圾短信过滤、防诈骗等服务"
    }
  }'
```

---

## 内部技能（不暴露）

以下技能仅供 PhoneAgent 内部使用，不通过公开 API 暴露：

- `adb_connect` - ADB 设备连接
- `adb_disconnect` - ADB 设备断开
- `tap` - 点击坐标
- `input_text` - 输入文字
- `open_app` - 打开应用
- `swipe` - 滑动屏幕

这些技能由 PhoneAgent 内部自动调用，用户无需关心。
