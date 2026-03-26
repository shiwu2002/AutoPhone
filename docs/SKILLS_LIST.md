# PhoneAgent Skills 技能书列表

## 技能书概览

| ID | 名称 | 图标 | 子技能数 | 描述 |
|----|------|------|----------|------|
| `phoneagent_tools` | PhoneAgent 工具集 | 🤖 | 7 | ADB 连接、模型配置、任务执行等核心功能 |
| `liantong_service` | 联通客服 | 📞 | 1 | 中国联通 APP 相关操作 |
| `mobile_operations` | 手机通用操作 | 📱 | 3 | 打开 APP、输入文字、点击坐标 |
| `excel_tools` | Excel 工具集 | 📊 | 5 | Excel 文件处理和批量任务执行 |

---

## 1. PhoneAgent 工具集 (phoneagent_tools) 🤖

PhoneAgent 核心功能技能集，包含 ADB 连接、模型配置、任务执行等功能。

### 子技能列表

| ID | 名称 | 占位符 | 输出字段 | 描述 |
|----|------|--------|----------|------|
| `adb_connect` | ADB 设备连接 | `{connection_request}`, `{device_address}` | `device_info` | 连接 ADB 设备，支持 USB 和无线连接 |
| `adb_disconnect` | ADB 设备断开 | `{device_address}` | `disconnect_result` | 断开 ADB 设备连接 |
| `model_config` | 模型配置管理 | `{current_config}`, `{config_request}` | `config_result` | 配置和管理 AI 模型参数 |
| `execute_task` | 执行手机任务 | `{task}`, `{model_provider}`, `{model_name}`, `{device_id}`, `{max_steps}` | `task_result` | 在手机上执行自动化任务 |
| `query_history` | 查询历史记录 | `{limit}`, `{success_filter}`, `{keyword}` | `history_records` | 查询任务执行历史记录 |
| `get_stats` | 获取统计信息 | 无 | `statistics` | 获取任务执行的统计信息 |
| `clear_history` | 清空历史记录 | 无 | `clear_result` | 清空所有任务历史记录 |

### 使用示例

```python
# 连接设备
manager.execute('phoneagent_tools', 'adb_connect',
                connection_request='连接设备')

# 执行任务
manager.execute('phoneagent_tools', 'execute_task',
                task='打开抖音搜索猫咪视频',
                model_provider='local',
                model_name='qwen3.5:4b',
                max_steps=30)

# 查询历史
manager.execute('phoneagent_tools', 'query_history', limit=5)
```

---

## 2. 联通客服 (liantong_service) 📞

中国联通 APP 相关操作技能。

### 子技能列表

| ID | 名称 | 占位符 | 输出字段 | 描述 |
|----|------|--------|----------|------|
| `query_ai_cs` | AI 客服问答 | `{question}` | `answer` | 通过联通 APP 的 AI 客服进行咨询问答 |

### 使用示例

```python
# 提问联通客服
result = manager.execute('liantong_service', 'query_ai_cs',
                         question='联通智家是什么？')
print(result['answer'])
```

---

## 3. 手机通用操作 (mobile_operations) 📱

手机通用操作技能，如打开 APP、输入文字、滑动等。

### 子技能列表

| ID | 名称 | 占位符 | 输出字段 | 描述 |
|----|------|--------|----------|------|
| `open_app` | 打开应用 | `{app_name}` | `open_result` | 打开指定的手机应用 |
| `input_text` | 输入文字 | `{text}` | `input_result` | 在当前焦点的输入框中输入文字 |
| `tap_coordinate` | 点击坐标 | `{x}`, `{y}` | `tap_result` | 点击屏幕上的指定坐标 |

### 使用示例

```python
# 打开微信
manager.execute('mobile_operations', 'open_app', app_name='微信')

# 输入文字
manager.execute('mobile_operations', 'input_text', text='你好')

# 点击坐标
manager.execute('mobile_operations', 'tap_coordinate', x=100, y=200)
```

---

## 4. Excel 工具集 (excel_tools) 📊

Excel 文件处理和批量任务执行技能。

### 子技能列表

| ID | 名称 | 占位符 | 输出字段 | 描述 |
|----|------|--------|----------|------|
| `read_excel` | 读取 Excel | `{file_path}`, `{sheet_name}` | `excel_data` | 读取 Excel 文件内容 |
| `write_excel` | 写入 Excel | `{file_path}`, `{data}`, `{sheet_name}` | `write_result` | 将数据写入 Excel 文件 |
| `preview_excel` | Excel 文件预览 | `{file_path}`, `{question_column}` | `excel_preview` | 预览 Excel 文件内容 |
| `batch_execute` | Excel 批量任务 | `{file_path}`, `{task_template}`, `{output_file}`, `{embed_screenshot}`, `{column}` | `batch_result` | 批量执行 Excel 中的任务 |
| `compare_answers` | 答案对比 | `{ai_answer}`, `{standard_answer}` | `comparison_result` | 对比 AI 答案和标准答案的相似度 |

### 使用示例

```python
# 读取 Excel
result = manager.execute('excel_tools', 'read_excel',
                         file_path='data.xlsx')
print(f"列：{result['columns']}, 行数：{result['row_count']}")

# 预览 Excel（自动检测问题列）
result = manager.execute('excel_tools', 'preview_excel',
                         file_path='questions.xlsx')
print(f"问题列：{result['question_column']}, 共 {result['count']} 个问题")

# 批量执行任务
result = manager.execute('excel_tools', 'batch_execute',
                         file_path='questions.xlsx',
                         task_template='打开中国联通，回答问题：{question}',
                         output_file='answers.xlsx')
print(f"成功：{result['statistics']['success']}/{result['statistics']['total']}")

# 对比答案
result = manager.execute('excel_tools', 'compare_answers',
                         ai_answer='联通智家是智能家居服务',
                         standard_answer='联通智家是智能家居服务')
print(f"相似度：{result['similarity']}, 正确：{result['is_correct']}")
```

---

## HTTP API 使用示例

### 获取技能书列表

```bash
curl http://localhost:5001/skills/books
```

### 获取技能书详情

```bash
curl http://localhost:5001/skills/book/excel_tools
```

### 执行子技能

```bash
# 执行 Excel 预览
curl -X POST http://localhost:5001/skills/execute \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": "excel_tools",
    "sub_skill_id": "preview_excel",
    "params": {
      "file_path": "/path/to/questions.xlsx"
    }
  }'

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

# 执行手机任务
curl -X POST http://localhost:5001/skills/execute \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": "phoneagent_tools",
    "sub_skill_id": "execute_task",
    "params": {
      "task": "打开抖音搜索猫咪视频",
      "max_steps": 30
    }
  }'
```

---

## 占位符说明

在技能提示词模板中，使用 `{参数名}` 形式的占位符。执行时，这些占位符会被替换为实际传入的参数值。

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
