# 多设备并行执行指南

## 概述

Phone Agent 现在支持多设备并行执行功能。当有多个 ADB 设备连接时，可以自动将批量任务分配到多个设备上并发执行，显著提升执行效率。

## 核心特性

### 1. 自动设备检测
- 自动发现已连接的所有 ADB 设备
- 智能分配任务到各个设备
- 负载均衡，确保各设备任务数均匀

### 2. 并行执行
- 使用线程池实现真正的并发执行
- 每个设备独立运行 PhoneAgent 实例
- 互不干扰，上下文隔离

### 3. 结果合并
- 自动合并所有设备的执行结果
- 保持原始问题顺序
- 提供详细的分设备统计

### 4. 灵活配置
- 可自定义最大工作线程数
- 支持截图保存
- 支持详细输出模式

## 快速开始

### 基础示例

```python
from main import PhoneAgentAPI

# 初始化 API
api = PhoneAgentAPI()

# 准备问题列表
questions = [
    "问题 1",
    "问题 2",
    "问题 3",
    "问题 4"
]

# 并行执行
result = api.run_batch_parallel(
    questions=questions,
    task_template="请回答：{content}",
    verbose=False
)

# 查看结果
print(f"总问题数：{result.total}")
print(f"成功：{result.success_count}")
print(f"失败：{result.failed_count}")
print(f"总耗时：{result.total_time:.2f}秒")
```

### 查看设备信息

```python
from phone_agent.device_factory import get_device_factory

# 获取设备列表
devices = get_device_factory().list_devices()

print(f"可用设备数：{len(devices)}")
for device in devices:
    print(f"  - {device.device_id}")
```

## API 参考

### PhoneAgentAPI.run_batch_parallel

```python
def run_batch_parallel(
    questions: List[str],           # 问题列表
    task_template: str,             # 任务模板，使用 {content} 占位
    embed_screenshot: bool = False, # 是否保存截图
    verbose: bool = False,          # 是否显示详细输出
    max_workers: Optional[int] = None  # 最大工作线程数
) -> ParallelBatchResult
```

#### 参数说明

- `questions`: 要执行的问题列表
- `task_template`: 任务模板字符串，`{content}` 会被实际问题替换
- `embed_screenshot`: 是否保存每个问题的截图
- `verbose`: 是否显示详细执行过程
- `max_workers`: 限制最大并发线程数（默认等于设备数）

#### 返回结果

`ParallelBatchResult` 包含：

- `total`: 总问题数
- `success_count`: 成功数
- `failed_count`: 失败数
- `device_results`: 各设备的详细结果（列表）
- `results`: 合并后的结果（按原问题顺序）
- `total_time`: 总耗时（秒）

### DeviceResult 结构

每个设备的结果包含：

```python
{
    "device_id": "设备 ID",
    "results": [...],              # 该设备执行的所有结果
    "success_count": 8,            # 成功数
    "failed_count": 2,             # 失败数
    "start_time": "开始时间",
    "end_time": "结束时间",
    "error": ""                    # 设备级错误（如果有）
}
```

## 工作原理

### 1. 设备检测

```python
devices = get_device_factory().list_devices()
# 假设有 3 个设备：["device1", "device2", "device3"]
```

### 2. 任务分配

假设有 10 个问题，3 个设备：

```python
# 设备 1: 4 个问题 (索引 0-3)
# 设备 2: 3 个问题 (索引 4-6)
# 设备 3: 3 个问题 (索引 7-9)
```

分配策略：
- 前 `remainder` 个设备多分配一个问题
- 确保负载均衡

### 3. 并行执行

```python
# 为每个设备创建独立的 PhoneAgent 实例
# 在线程池中并发执行
with ThreadPoolExecutor(max_workers=num_devices) as executor:
    futures = [executor.submit(run_device_task, task) for task in device_tasks]
```

### 4. 结果合并

```python
# 收集所有设备的结果
all_results = []
for device_result in device_results:
    all_results.extend(device_result.results)

# 按原始索引排序
merged_results = sorted(all_results, key=lambda x: x['global_index'])
```

## 使用场景

### 1. 批量问题处理

最适合大量独立问题的场景：

```python
questions = ["问题 1", "问题 2", ..., "问题 100"]

result = api.run_batch_parallel(
    questions=questions,
    task_template="请回答：{content}"
)

# 3 个设备理论上可以快 3 倍
print(f"加速比：{len(devices)}x")
```

### 2. 多应用测试

在不同设备上同时测试不同应用：

```python
tasks = [
    "打开微信",
    "打开支付宝",
    "打开抖音",
    "打开浏览器"
]

result = api.run_batch_parallel(
    questions=tasks,
    task_template="请{content}"
)
```

### 3. 数据收集

并行收集多个来源的数据：

```python
questions = [
    "查看天气",
    "查看新闻",
    "查看股票",
    "查看体育比分"
]

result = api.run_batch_parallel(
    questions=questions,
    task_template="请{content}"
)
```

## 性能优化

### 1. 设备数量

设备越多，并行效果越好：

```
1 个设备：100 个问题 × 10 秒 = 1000 秒
2 个设备：100 个问题 × 10 秒 ≈ 500 秒 (2x 加速)
4 个设备：100 个问题 × 10 秒 ≈ 250 秒 (4x 加速)
```

### 2. 任务分配

确保任务数是设备数的倍数：

```python
# 好：任务均匀分配
questions = ["问题"] * 12  # 3 个设备，每个 4 个
result = api.run_batch_parallel(questions=questions, ...)

# 一般：也能正常工作
questions = ["问题"] * 10  # 3 个设备，分别 4+3+3 个
```

### 3. 工作线程限制

如果系统资源有限，可以限制并发数：

```python
# 有 4 个设备，但只使用 2 个工作线程
result = api.run_batch_parallel(
    questions=questions,
    max_workers=2  # 限制并发数
)
```

### 4. 截图优化

截图会增加 I/O 开销：

```python
# 不需要截图时禁用
result = api.run_batch_parallel(
    questions=questions,
    embed_screenshot=False  # 禁用截图
)
```

## 错误处理

### 单个任务失败

某个任务失败不会影响其他任务：

```python
result = api.run_batch_parallel(...)

for r in result.results:
    if r.success:
        print(f"✅ {r.answer}")
    else:
        print(f"❌ {r.error}")
```

### 设备故障

某个设备故障不影响其他设备：

```python
# 设备 2 故障
for dr in result.device_results:
    if dr['error']:
        print(f"设备 {dr['device_id']} 故障：{dr['error']}")
    else:
        print(f"设备 {dr['device_id']} 正常完成")
```

### 无可用设备

```python
devices = get_device_factory().list_devices()

if len(devices) == 0:
    print("❌ 没有可用设备")
    return

# 只有 1 个设备时自动降级为串行
if len(devices) == 1:
    print("⚠️  只有 1 个设备，使用串行模式")
```

## 完整示例

### 示例 1: 基础使用

```python
from main import PhoneAgentAPI

# 初始化
api = PhoneAgentAPI()

# 问题列表
questions = [
    "今天天气怎么样？",
    "北京到上海的高铁要多久？",
    "推荐几本好看的书"
]

# 并行执行
result = api.run_batch_parallel(
    questions=questions,
    task_template="请回答：{content}",
    verbose=False
)

# 输出结果
print(f"\n总计：{result.total}")
print(f"成功：{result.success_count}")
print(f"耗时：{result.total_time:.2f}秒")

for i, r in enumerate(result.results):
    status = "✅" if r.success else "❌"
    print(f"{i+1}. {status} {r.answer[:50]}...")
```

### 示例 2: 查看设备统计

```python
from main import PhoneAgentAPI

api = PhoneAgentAPI()
result = api.run_batch_parallel(
    questions=["问题"] * 10,
    task_template="请回答：{content}"
)

# 查看各设备执行情况
print("\n各设备执行情况:")
for dr in result.device_results:
    print(f"设备 {dr['device_id']}:")
    print(f"  成功：{dr['success_count']}")
    print(f"  失败：{dr['failed_count']}")
    print(f"  耗时：{float(dr.get('total_time', 0)):.2f}秒")
```

### 示例 3: 带截图的并行执行

```python
api = PhoneAgentAPI()

result = api.run_batch_parallel(
    questions=["打开微信", "查看时间"],
    task_template="请{content}",
    embed_screenshot=True
)

# 检查截图
for i, r in enumerate(result.results):
    if r.screenshot_base64:
        print(f"任务{i+1}: ✅ 已保存截图")
    else:
        print(f"任务{i+1}: ❌ 未保存截图")
```

## 注意事项

### 1. 设备独立性

- 每个设备必须能独立运行
- 确保设备都已正确连接和授权
- 建议设备分辨率和配置相似

### 2. 资源消耗

- 多线程会消耗更多 CPU 和内存
- 多个 ADB 连接会占用 USB 带宽
- 建议使用 USB 3.0 接口

### 3. 网络依赖

- 如果使用云端模型，注意网络带宽
- 多个设备同时请求可能触发限流
- 考虑使用本地模型减少延迟

### 4. 调试建议

- 先用少量问题测试
- 开启 `verbose=True` 查看详细过程
- 检查各设备的日志输出

## 故障排查

### 问题：设备未被检测到

```bash
# 检查 ADB 连接
adb devices

# 重启 ADB 服务器
adb kill-server
adb start-server
adb devices
```

### 问题：并行执行速度慢

可能原因：
1. 设备性能差异大（木桶效应）
2. 网络带宽限制
3. 模型服务响应慢

解决方法：
- 使用性能相近的设备
- 增加 `max_workers` 限制
- 使用本地模型服务

### 问题：部分任务失败

检查错误信息：

```python
for r in result.results:
    if not r.success:
        print(f"失败任务：{r.error}")
```

常见原因：
- 应用未安装
- 权限不足
- 网络超时

## 最佳实践

1. **任务分组**: 将相似任务分配到同一设备
2. **错误重试**: 对失败的任务可以单独重试
3. **进度保存**: 大批量任务定期保存进度
4. **资源监控**: 监控系统资源使用情况
5. **日志记录**: 保留详细的执行日志

## 相关文档

- `examples/parallel_execution.py` - 完整示例代码
- `API_GUIDE.md` - API 使用指南
- `QUICK_REFERENCE.md` - 快速参考
