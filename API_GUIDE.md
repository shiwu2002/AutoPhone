# Phone Agent API 使用指南

## 概述

`main.py` 现在提供了程序化 API，允许其他项目调用 Phone Agent 的功能。主要包括：

- **单个任务执行**：在手机上执行单个 AI 驱动的任务
- **批量任务执行**：从 Excel/TXT 文件批量读取并执行问题
- **灵活配置**：支持自定义模型和 Agent 配置

## 快速开始

### 1. 基础使用

```python
from main import PhoneAgentAPI

# 初始化 API（自动从 config.json 加载配置）
api = PhoneAgentAPI()

# 执行单个任务
result = api.run_task("打开微信")

if result.success:
    print(f"答案：{result.answer}")
else:
    print(f"失败：{result.error}")
```

### 2. 从 Excel 批量执行

```python
from main import PhoneAgentAPI

api = PhoneAgentAPI()

# 从 Excel 文件批量执行问题
batch_result = api.run_batch_from_file(
    file_path="questions.xlsx",
    task_template="请回答这个问题：{content}",
    embed_screenshot=True,      # 嵌入截图到 Excel
    compare_answer=False,        # 不对比标准答案
    max_questions=10            # 最多处理 10 个问题
)

print(f"成功：{batch_result.success_count}/{batch_result.total}")
```

### 3. 从列表批量执行

```python
from main import PhoneAgentAPI

api = PhoneAgentAPI()

questions = [
    "今天天气怎么样？",
    "北京到上海的高铁要多久？",
    "推荐几本好看的书",
]

batch_result = api.run_batch_from_list(
    questions=questions,
    task_template="请回答：{content}",
    embed_screenshot=False
)

for result in batch_result.results:
    if result.success:
        print(f"✅ {result.answer}")
    else:
        print(f"❌ {result.error}")
```

## API 参考

### PhoneAgentAPI

主接口类，提供所有 Phone Agent 功能的访问。

#### 初始化参数

```python
PhoneAgentAPI(
    model_config=None,      # ModelConfig 对象，None 则从 config.json 加载
    agent_config=None,      # AgentConfig 对象，None 则从 config.json 加载
    config_path="config.json"  # 配置文件路径
)
```

#### 方法

##### run_task

执行单个任务。

```python
run_task(
    task: str,              # 任务描述（自然语言）
    save_screenshot: bool,  # 是否保存截图
    verbose: bool          # 是否显示详细输出
) -> TaskResult
```

**返回**: `TaskResult` 对象，包含：
- `success`: 是否成功
- `answer`: 答案/结果
- `error`: 错误信息（如果失败）
- `steps`: 执行步数
- `screenshot_base64`: 截图的 base64 数据（如果保存）

##### run_batch_from_file

从 Excel/TXT 文件批量执行。

```python
run_batch_from_file(
    file_path: str,         # 输入文件路径
    task_template: str,     # 任务模板，使用 {content} 占位
    output_path: str,       # 输出文件路径（可选）
    column: str,           # Excel 列名（可选）
    embed_screenshot: bool, # 嵌入截图到 Excel
    compare_answer: bool,   # 对比标准答案
    max_questions: int,    # 最大问题数（0=全部）
    verbose: bool          # 详细输出
) -> BatchTaskResult
```

**返回**: `BatchTaskResult` 对象，包含：
- `total`: 总问题数
- `success_count`: 成功数
- `failed_count`: 失败数
- `results`: 详细结果列表（TaskResult 列表）
- `output_file`: 输出文件路径

##### run_batch_from_list

从字符串列表批量执行。

```python
run_batch_from_list(
    questions: List[str],   # 问题列表
    task_template: str,     # 任务模板，使用 {content} 占位
    output_path: str,       # 输出 Excel 路径（可选）
    embed_screenshot: bool, # 嵌入截图
    max_questions: int,    # 最大问题数（0=全部）
    verbose: bool          # 详细输出
) -> BatchTaskResult
```

### 数据类

#### TaskResult

单个任务的执行结果。

```python
@dataclass
class TaskResult:
    success: bool
    answer: str
    error: Optional[str] = None
    steps: int = 0
    screenshot_base64: Optional[str] = None
```

#### BatchTaskResult

批量任务的执行结果。

```python
@dataclass
class BatchTaskResult:
    total: int
    success_count: int
    failed_count: int
    results: List[TaskResult]
    output_file: Optional[str] = None
```

## 高级用法

### 自定义配置

```python
from main import PhoneAgentAPI, ModelConfig, AgentConfig

# 自定义模型配置
model_config = ModelConfig(
    base_url="http://localhost:11434/v1",
    model_name="qwen3.5:4b",
    api_key="ollama",
    lang="cn",
    use_thinking=False
)

# 自定义 Agent 配置
agent_config = AgentConfig(
    max_steps=30,
    verbose=True,
    lang="cn"
)

# 使用自定义配置
api = PhoneAgentAPI(
    model_config=model_config,
    agent_config=agent_config
)
```

### 集成到其他项目

#### Web 服务集成

```python
from flask import Flask, request, jsonify
from main import PhoneAgentAPI

app = Flask(__name__)
api = PhoneAgentAPI()

@app.route('/run_task', methods=['POST'])
def run_task():
    data = request.json
    task = data.get('task')
    
    result = api.run_task(task)
    
    return jsonify({
        'success': result.success,
        'answer': result.answer,
        'error': result.error
    })

if __name__ == '__main__':
    app.run()
```

#### 异步批处理

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from main import PhoneAgentAPI

api = PhoneAgentAPI()
executor = ThreadPoolExecutor(max_workers=3)

def run_async_batch(questions):
    futures = []
    for q in questions:
        future = executor.submit(api.run_task, q)
        futures.append(future)
    
    results = []
    for future in futures:
        results.append(future.result())
    
    return results
```

### 进度跟踪

```python
from main import PhoneAgentAPI
import tqdm

api = PhoneAgentAPI()

batch_result = api.run_batch_from_file(
    file_path="questions.xlsx",
    task_template="请回答：{content}"
)

# 使用 tqdm 显示进度
with tqdm.tqdm(total=batch_result.total, desc="处理进度") as pbar:
    for result in batch_result.results:
        if result.success:
            pbar.set_postfix_str(f"成功：{result.answer[:30]}...")
        else:
            pbar.set_postfix_str(f"失败：{result.error}")
        pbar.update(1)
```

## 错误处理

```python
from main import PhoneAgentAPI, BatchTaskResult

api = PhoneAgentAPI()

try:
    result = api.run_task("打开微信")
    if result.success:
        print(f"成功：{result.answer}")
    else:
        print(f"失败：{result.error}")
except Exception as e:
    print(f"异常：{e}")
```

对于批量任务，检查每个结果的状态：

```python
batch_result = api.run_batch_from_file(...)

for i, result in enumerate(batch_result.results):
    if result.success:
        print(f"问题{i+1}成功：{result.answer}")
    else:
        print(f"问题{i+1}失败：{result.error}")
```

## 最佳实践

1. **复用 API 实例**：创建一次 `PhoneAgentAPI` 实例，重复使用
2. **合理设置 max_steps**：根据任务复杂度调整步数限制
3. **使用 verbose 模式调试**：开发时开启详细输出便于调试
4. **批量任务保存进度**：长时间运行的批量任务建议定期保存进度
5. **截图嵌入谨慎使用**：嵌入截图会增加 Excel 文件大小

## 示例代码

完整示例请参考：
- `examples/api_usage.py` - API 使用示例集合
- `templates/excel-batch.js` - Excel 批量处理 Web 界面

## 注意事项

1. 确保 ADB 连接正常
2. 确保 config.json 配置正确
3. 批量执行前建议先用单个任务测试
4. Excel 文件需要安装 pandas 和 openpyxl
