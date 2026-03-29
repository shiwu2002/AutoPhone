#!/usr/bin/env python3
"""
单任务执行工具

用法：
    python single_task.py "打开微信"
    python single_task.py "查看时间" --save-screenshot
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from main import PhoneAgentAPI


def run_single_task(
    task: str,
    save_screenshot: bool = False,
    verbose: bool = False
):
    """
    在手机上执行单个任务。
    
    参数:
        task: 任务描述
        save_screenshot: 是否保存截图
        verbose: 是否显示详细输出
    """
    print(f"🚀 执行任务：{task}")
    print("-" * 60)
    
    api = PhoneAgentAPI()
    
    result = api.run_task(
        task=task,
        save_screenshot=save_screenshot,
        verbose=verbose
    )
    
    print("\n" + "=" * 60)
    if result.success:
        print(f"✅ 任务成功")
        print(f"答案：{result.answer}")
        print(f"步数：{result.steps}")
        if result.screenshot_base64:
            print(f"截图：已保存")
    else:
        print(f"❌ 任务失败")
        print(f"错误：{result.error}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="单任务执行",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 基础使用
    python single_task.py "打开微信"
    
    # 保存截图
    python single_task.py "查看时间" --save-screenshot
    
    # 显示详细过程
    python single_task.py "发送消息给张三" --verbose
        """
    )
    
    parser.add_argument("task", type=str, help="任务描述（用引号包裹）")
    parser.add_argument("--save-screenshot", action="store_true", help="保存截图")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细输出")
    
    args = parser.parse_args()
    
    run_single_task(
        task=args.task,
        save_screenshot=args.save_screenshot,
        verbose=args.verbose
    )


if __name__ == "__main__":
    main()
