# 多设备并行 - 快速参考

## 快速开始

### 1. 基础使用

```python
from main import PhoneAgentAPI

# 初始化 API
api = PhoneAgentAPI()

# 准备问题
questions = ["问题 1", "问题 2", "问题 3", "问题 4"]

# 并行执行
result = api.run_batch_parallel(
    questions=questions,
    task_template="请回答：{content}"
)

# 查看结果
print(f"成功：{result.success_count}/{result.total}")
print(f"耗时：{result.total_time:.2f}秒")
```

### 2. 检查设备

```python
from phone_agent.device_factory import get_device_factory

devices = get_device_factory().list_devices()
print(f"可用设备数：{len(devices)}")
```

### 3. 查看分设备统计

```python
for dr in result.device_results:
    print(f"设备 {dr['device_id']}: {dr['success_count']} 成功")
```

## API 参数速查

### run_batch_parallel()

```python
run_batch_parallel(
    questions: List[str],           # 问题列表（必需）
    task_template: str,             # 任务模板，使用 {content}（必需）
    embed_screenshot: bool = False, # 是否保存截图
    verbose: bool = False,          # 详细输出
    max_workers: Optional[int] = None  # 最大工作线程数
) -> ParallelBatchResult
```

## 返回结果类型

### ParallelBatchResult

```python
@dataclass
class ParallelBatchResult:
    total: int                      # 总问题数
    success_count: int              # 成功数
    failed_count: int               # 失败数
    device_results: List[dict]      # 各设备结果
    results: List[TaskResult]       # 合并后的结果
    total_time: float               # 总耗时（秒）
```

### DeviceResult (字典)

```python
{
    "device_id": "设备 ID",
    "results": [...],               # 该设备的执行结果
    "success_count": 8,             # 成功数
    "failed_count": 2,              # 失败数
    "start_time": "...",
    "end_time": "..."
}
```

## 常见用法

### 1. 简单并行

```python
api = PhoneAgentAPI()
result = api.run_batch_parallel(
    questions=["问题 1", "问题 2"],
    task_template="请回答：{content}"
)
```

### 2. 带截图

```python
result = api.run_batch_parallel(
    questions=["打开微信", "查看时间"],
    task_template="请{content}",
    embed_screenshot=True
)
```

### 3. 限制并发数

```python
result = api.run_batch_parallel(
    questions=["问题"] * 20,
    task_template="请回答：{content}",
    max_workers=2  # 限制最多 2 个并发
)
```

### 4. 查看详细过程

```python
result = api.run_batch_parallel(
    questions=["问题 1", "问题 2"],
    task_template="请回答：{content}",
    verbose=True  # 显示详细输出
)
```

## 性能对比

| 设备数 | 100 个问题 (每个 10 秒) | 加速比 |
|--------|---------------------|--------|
| 1      | ~1000 秒            | 1x     |
| 2      | ~500 秒             | ~2x    |
| 3      | ~333 秒             | ~3x    |
| 4      | ~250 秒             | ~4x    |

## 错误处理

```python
result = api.run_batch_parallel(...)

# 检查整体结果
if result.success_count == result.total:
    print("全部成功!")
else:
    print(f"部分失败：{result.failed_count}")

# 查看详细错误
for i, r in enumerate(result.results):
    if not r.success:
        print(f"任务{i+1}失败：{r.error}")
```

## 最佳实践

### ✅ 推荐

```python
# 1. 先检查设备
devices = get_device_factory().list_devices()
if len(devices) == 0:
    print("没有设备")
    return

# 2. 小批量测试
result = api.run_batch_parallel(
    questions=["测试问题"],
    task_template="请回答：{content}"
)

# 3. 大批量执行
result = api.run_batch_parallel(
    questions=["问题"] * 100,
    task_template="请回答：{content}"
)

# 4. 查看统计
print(f"成功率：{result.success_count/result.total*100:.1f}%")
```

### ❌ 避免

```python
# 1. 不检查设备就直接执行
# 2. 单设备还强行并行（会自动降级为串行）
# 3. 不处理失败的任务
```

## 示例代码

### 完整示例

```python
from main import PhoneAgentAPI
from phone_agent.device_factory import get_device_factory

def main():
    # 初始化
    api = PhoneAgentAPI()
    
    # 检查设备
    devices = get_device_factory().list_devices()
    print(f"可用设备：{len(devices)}")
    
    if len(devices) == 0:
        print("❌ 没有设备")
        return
    
    # 准备问题
    questions = [
        "今天天气怎么样？",
        "北京到上海的高铁要多久？",
        "推荐几本好看的书",
        "如何学习 Python？"
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
    print(f"失败：{result.failed_count}")
    print(f"耗时：{result.total_time:.2f}秒")
    
    # 分设备统计
    print(f"\n各设备执行情况:")
    for dr in result.device_results:
        print(f"  设备 {dr['device_id']}: {dr['success_count']} 成功")
    
    # 详细结果
    print(f"\n详细结果:")
    for i, r in enumerate(result.results, 1):
        status = "✅" if r.success else "❌"
        print(f"{i}. {status} {r.answer[:50] if r.answer else r.error}")

if __name__ == "__main__":
    main()
```

## CLI 使用

```bash
# 运行演示脚本
python main.py

# 运行并行示例
python examples/parallel_execution.py

# 选择示例 2 (多设备并行)
# 输入：2
```

## 故障排查

### 问题：没有检测到设备

```bash
# 检查 ADB 连接
adb devices

# 重启 ADB
adb kill-server
adb start-server
adb devices
```

### 问题：并行执行慢

可能原因：
- 设备性能差异大
- USB 带宽不足
- 网络延迟

解决方法：
- 使用性能相近的设备
- 使用 USB 3.0
- 限制 `max_workers`

### 问题：部分任务失败

```python
# 查看错误详情
for r in result.results:
    if not r.success:
        print(f"失败：{r.error}")

# 重试失败的任务
failed_questions = [
    q for r, q in zip(result.results, questions) 
    if not r.success
]

if failed_questions:
    retry_result = api.run_batch_parallel(
        questions=failed_questions,
        task_template="请回答：{content}"
    )
```

## 相关文档

- `MULTI_DEVICE_PARALLEL.md` - 详细使用指南
- `PARALLEL_FEATURE_SUMMARY.md` - 功能实现总结
- `examples/parallel_execution.py` - 完整示例代码
- `QUICK_REFERENCE.md` - 通用 API 参考
