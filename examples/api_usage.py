#!/usr/bin/env python3
"""
Phone Agent API 使用示例

演示如何通过程序化接口调用 Phone Agent 功能。
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def example_single_task():
    """示例 1: 执行单个任务"""
    from main import PhoneAgentAPI
    
    print("=" * 60)
    print("示例 1: 执行单个任务")
    print("=" * 60)
    
    # 初始化 API（自动从 config.json 加载配置）
    api = PhoneAgentAPI()
    
    # 执行任务
    result = api.run_task(
        task="打开微信",
        save_screenshot=False,
        verbose=True
    )
    
    # 查看结果
    if result.success:
        print(f"✅ 任务成功完成")
        print(f"答案：{result.answer}")
        print(f"步数：{result.steps}")
    else:
        print(f"❌ 任务失败：{result.error}")


def example_batch_from_excel():
    """示例 2: 从 Excel 文件批量执行"""
    from main import PhoneAgentAPI
    
    print("\n" + "=" * 60)
    print("示例 2: 从 Excel 文件批量执行")
    print("=" * 60)
    
    api = PhoneAgentAPI()
    
    # 从 Excel 文件批量执行问题
    batch_result = api.run_batch_from_file(
        file_path="questions.xlsx",  # Excel 文件路径
        task_template="请回答这个问题：{content}",
        output_path="results.xlsx",  # 输出文件路径（可选）
        column="问题",  # 指定列名（可选）
        embed_screenshot=True,  # 嵌入截图到 Excel
        compare_answer=False,  # 不对比标准答案
        max_questions=10,  # 最多处理 10 个问题（0=全部）
        verbose=True
    )
    
    # 查看统计信息
    print(f"\n📊 批量执行统计:")
    print(f"总问题数：{batch_result.total}")
    print(f"成功：{batch_result.success_count}")
    print(f"失败：{batch_result.failed_count}")
    print(f"输出文件：{batch_result.output_file}")
    
    # 查看详细结果
    for i, result in enumerate(batch_result.results[:3], 1):  # 只显示前 3 个
        if result.success:
            print(f"\n问题{i}: {result.answer[:50]}...")
        else:
            print(f"\n问题{i}失败：{result.error}")


def example_batch_from_list():
    """示例 3: 从列表批量执行"""
    from main import PhoneAgentAPI
    
    print("\n" + "=" * 60)
    print("示例 3: 从列表批量执行")
    print("=" * 60)
    
    api = PhoneAgentAPI()
    
    # 问题列表
    questions = [
        "今天天气怎么样？",
        "北京到上海的高铁要多久？",
        "推荐几本好看的书",
    ]
    
    # 从列表批量执行
    batch_result = api.run_batch_from_list(
        questions=questions,
        task_template="请回答：{content}",
        embed_screenshot=False,
        verbose=True
    )
    
    # 查看结果
    print(f"\n📊 执行统计:")
    print(f"总问题数：{batch_result.total}")
    print(f"成功：{batch_result.success_count}")
    
    for i, result in enumerate(batch_result.results, 1):
        status = "✅" if result.success else "❌"
        print(f"{status} 问题{i}: {result.answer[:50] if result.answer else result.error}")


def example_custom_config():
    """示例 4: 使用自定义配置"""
    from main import PhoneAgentAPI, ModelConfig, AgentConfig
    
    print("\n" + "=" * 60)
    print("示例 4: 使用自定义配置")
    print("=" * 60)
    
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
    
    # 使用自定义配置初始化
    api = PhoneAgentAPI(
        model_config=model_config,
        agent_config=agent_config,
        config_path="config.json"  # 作为后备配置
    )
    
    # 执行任务
    result = api.run_task(
        task="查看当前时间",
        verbose=False
    )
    
    print(f"\n结果：{result.answer}")


def example_with_progress_callback():
    """示例 5: 带进度回调的批量执行"""
    from main import PhoneAgentAPI
    import tqdm
    
    print("\n" + "=" * 60)
    print("示例 5: 带进度显示的批量执行")
    print("=" * 60)
    
    api = PhoneAgentAPI()
    
    # 使用 tqdm 显示进度条
    try:
        batch_result = api.run_batch_from_file(
            file_path="questions.xlsx",
            task_template="请回答：{content}",
            verbose=False
        )
        
        # 使用 tqdm 显示进度
        with tqdm.tqdm(total=batch_result.total, desc="处理进度") as pbar:
            for i, result in enumerate(batch_result.results):
                if result.success:
                    pbar.set_postfix_str(f"成功：{result.answer[:30]}...")
                else:
                    pbar.set_postfix_str(f"失败：{result.error}")
                pbar.update(1)
                
    except ImportError:
        print("tqdm 未安装，使用普通模式")
        batch_result = api.run_batch_from_file(
            file_path="questions.xlsx",
            task_template="请回答：{content}",
            verbose=True
        )


def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("Phone Agent API 使用示例")
    print("=" * 60)
    
    # 选择要运行的示例
    examples = {
        "1": ("单个任务", example_single_task),
        "2": ("Excel 批量", example_batch_from_excel),
        "3": ("列表批量", example_batch_from_list),
        "4": ("自定义配置", example_custom_config),
        "5": ("进度回调", example_with_progress_callback),
    }
    
    print("\n可用示例:")
    for key, (name, _) in examples.items():
        print(f"  {key}. {name}")
    
    choice = input("\n请选择要运行的示例 (1-5, 默认=1): ").strip() or "1"
    
    if choice in examples:
        examples[choice][1]()
    else:
        print("无效选择")


if __name__ == "__main__":
    main()
