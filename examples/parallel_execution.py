#!/usr/bin/env python3
"""
多设备并行执行示例

演示如何使用 Phone Agent 的多设备并行执行功能。
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def example_single_device():
    """示例 1: 单设备执行"""
    from main import PhoneAgentAPI
    
    print("=" * 60)
    print("示例 1: 单设备执行")
    print("=" * 60)
    
    api = PhoneAgentAPI()
    
    # 获取设备列表
    from phone_agent.device_factory import get_device_factory
    devices = get_device_factory().list_devices()
    
    print(f"\n可用设备数：{len(devices)}")
    for device in devices:
        print(f"  - {device.device_id}")
    
    if len(devices) == 0:
        print("\n❌ 没有可用设备")
        return
    
    # 执行单个任务
    result = api.run_task("查看时间", verbose=False)
    
    print(f"\n结果：{result.answer}")
    print(f"步数：{result.steps}")
    print(f"成功：{result.success}")


def example_parallel_execution():
    """示例 2: 多设备并行执行"""
    from main import PhoneAgentAPI
    
    print("\n" + "=" * 60)
    print("示例 2: 多设备并行执行")
    print("=" * 60)
    
    api = PhoneAgentAPI()
    
    # 获取设备列表
    from phone_agent.device_factory import get_device_factory
    devices = get_device_factory().list_devices()
    
    print(f"\n可用设备数：{len(devices)}")
    if len(devices) < 2:
        print("⚠️  需要至少 2 个设备才能演示并行执行")
        return
    
    for device in devices:
        print(f"  - {device.device_id}")
    
    # 准备问题列表
    questions = [
        "今天天气怎么样？",
        "北京到上海的高铁要多久？",
        "推荐几本好看的书",
        "如何学习 Python？",
        "世界上最大的海洋是哪个？",
        "人类首次登月是哪一年？",
        "光速是多少？",
        "水的沸点是多少度？"
    ]
    
    print(f"\n开始并行执行 {len(questions)} 个问题...")
    
    # 并行执行
    batch_result = api.run_batch_parallel(
        questions=questions,
        task_template="请回答：{content}",
        embed_screenshot=False,
        verbose=False
    )
    
    # 输出统计
    print(f"\n📊 执行统计:")
    print(f"  总问题数：{batch_result.total}")
    print(f"  成功：{batch_result.success_count}")
    print(f"  失败：{batch_result.failed_count}")
    print(f"  总耗时：{batch_result.total_time:.2f}秒")
    
    # 输出各设备的执行情况
    print(f"\n📱 各设备执行情况:")
    for dr in batch_result.device_results:
        print(f"  设备 {dr['device_id']}:")
        print(f"    成功：{dr['success_count']}")
        print(f"    失败：{dr['failed_count']}")
        print(f"    耗时：{float(dr.get('total_time', 0)):.2f}秒")
    
    # 输出详细结果（前 3 个）
    print(f"\n✅ 详细结果 (前 3 个):")
    for i, r in enumerate(batch_result.results[:3], 1):
        status = "✅" if r.success else "❌"
        answer_preview = r.answer[:50] if r.answer else "无结果"
        print(f"  {i}. {status} {answer_preview}...")


def example_custom_workers():
    """示例 3: 自定义工作线程数"""
    from main import PhoneAgentAPI
    
    print("\n" + "=" * 60)
    print("示例 3: 自定义最大工作线程数")
    print("=" * 60)
    
    api = PhoneAgentAPI()
    
    devices = get_device_factory().list_devices()
    
    if len(devices) < 2:
        print("⚠️  需要至少 2 个设备")
        return
    
    questions = ["问题"] * 10  # 10 个相同的问题
    
    # 限制最多使用 2 个工作线程
    print(f"\n使用 {len(devices)} 个设备，限制最多 2 个工作线程")
    
    batch_result = api.run_batch_parallel(
        questions=questions,
        task_template="请回答：{content}",
        verbose=False,
        max_workers=2  # 限制工作线程数
    )
    
    print(f"\n总耗时：{batch_result.total_time:.2f}秒")


def example_with_screenshots():
    """示例 4: 并行执行并保存截图"""
    from main import PhoneAgentAPI
    
    print("\n" + "=" * 60)
    print("示例 4: 并行执行并保存截图")
    print("=" * 60)
    
    api = PhoneAgentAPI()
    
    devices = get_device_factory().list_devices()
    
    if len(devices) < 2:
        print("⚠️  需要至少 2 个设备")
        return
    
    questions = [
        "打开微信",
        "查看时间",
    ]
    
    print(f"\n并行执行 {len(questions)} 个任务并保存截图...")
    
    batch_result = api.run_batch_parallel(
        questions=questions,
        task_template="请{content}",
        embed_screenshot=True,  # 保存截图
        verbose=False
    )
    
    print(f"\n成功：{batch_result.success_count}/{batch_result.total}")
    
    # 检查是否有截图
    for i, r in enumerate(batch_result.results):
        if r.screenshot_base64:
            print(f"  任务{i+1}: ✅ 已保存截图")
        else:
            print(f"  任务{i+1}: ❌ 未保存截图")


def compare_serial_vs_parallel():
    """示例 5: 对比串行和并行性能"""
    from main import PhoneAgentAPI
    import time
    
    print("\n" + "=" * 60)
    print("示例 5: 串行 vs 并行 性能对比")
    print("=" * 60)
    
    api = PhoneAgentAPI()
    
    devices = get_device_factory().list_devices()
    
    if len(devices) < 2:
        print("⚠️  需要至少 2 个设备")
        return
    
    # 准备测试问题
    questions = ["查看时间"] * 4  # 4 个简单问题
    
    print(f"\n测试：{len(questions)} 个问题，{len(devices)} 个设备")
    
    # 这里只演示并行执行
    start_time = time.time()
    
    batch_result = api.run_batch_parallel(
        questions=questions,
        task_template="请{content}",
        verbose=False
    )
    
    parallel_time = time.time() - start_time
    
    print(f"\n并行执行:")
    print(f"  总耗时：{parallel_time:.2f}秒")
    print(f"  平均每问题：{parallel_time/len(questions):.2f}秒")
    print(f"  加速比：理论上约为设备数的倍数 ({len(devices)}x)")


def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("Phone Agent 多设备并行执行示例")
    print("=" * 60)
    
    examples = {
        "1": ("单设备执行", example_single_device),
        "2": ("多设备并行", example_parallel_execution),
        "3": ("自定义线程", example_custom_workers),
        "4": ("保存截图", example_with_screenshots),
        "5": ("性能对比", compare_serial_vs_parallel),
    }
    
    print("\n可用示例:")
    for key, (name, _) in examples.items():
        print(f"  {key}. {name}")
    
    choice = input("\n请选择要运行的示例 (1-5, 默认=2): ").strip() or "2"
    
    if choice in examples:
        examples[choice][1]()
    else:
        print("无效选择")


if __name__ == "__main__":
    main()
