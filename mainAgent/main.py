#!/usr/bin/env python3
"""主 Agent (MasterAgent) 入口 - 负责任务编排和文档操作。

主 Agent 在电脑端接收指令，然后调用 Skill（子 Agent）执行手机操作，
最后处理结果并操作文档。

使用示例：
    python main.py --task "查询联通安全管家的功能"
    python main.py  # 进入交互式模式

运行方式：
    方式 1: cd e:\\Python\\AutoPhone && python -m mainAgent.main
    方式 2: cd e:\\Python\\AutoPhone\\mainAgent && python main.py
"""

import sys
import json
from pathlib import Path

# 添加父目录到路径，支持直接运行
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from mainAgent.agent import MasterAgent, MasterAgentConfig
from mainAgent.skills import list_skills


def print_banner():
    """打印启动横幅。"""
    print("=" * 60)
    print("MasterAgent - 主 Agent 任务编排系统")
    print("=" * 60)
    print("主 Agent 负责：任务编排 | Skill 调用 | 文档操作")
    print("子 Agent (Skill) 负责：手机操作 | 获取回复")
    print("=" * 60)


def print_skills():
    """打印可用的 Skill 列表。"""
    skills = list_skills()
    if skills:
        print("\n可用的 Skills:")
        for skill in skills:
            print(f"  - {skill['id']}: {skill['name']}")
            print(f"    描述：{skill['description']}")
            print(f"    示例：{skill['example']}")
            print()


def main():
    """主入口。"""
    import argparse

    parser = argparse.ArgumentParser(description="MasterAgent - 主 Agent 任务编排系统")
    parser.add_argument("--task", "-t", type=str, help="要执行的任务")
    parser.add_argument("--skill", "-s", type=str, help="直接调用 Skill")
    parser.add_argument("--skill-args", type=str, help="Skill 参数（JSON 格式）")
    parser.add_argument("--list-skills", action="store_true", help="列出所有 Skill")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--quiet", "-q", action="store_true", help="静默模式")

    args = parser.parse_args()

    # Create config
    verbose = args.verbose or (not args.quiet)
    config = MasterAgentConfig(verbose=verbose)

    # Create master agent
    agent = MasterAgent(config=config)

    # Print banner
    if verbose:
        print_banner()

    # Handle --list-skills
    if args.list_skills:
        print_skills()
        return

    # Handle --skill (direct skill call)
    if args.skill:
        skill_id = args.skill
        skill_args = {}
        if args.skill_args:
            try:
                skill_args = json.loads(args.skill_args)
            except json.JSONDecodeError as e:
                print(f"Error parsing skill args: {e}")
                sys.exit(1)

        print(f"\n调用 Skill: {skill_id}")
        print(f"参数：{skill_args}")
        print()

        result = agent.call_skill(skill_id, **skill_args)

        print("\n执行结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # Handle --task or interactive mode
    if args.task:
        print(f"\n任务：{args.task}\n")
        result = agent.execute_task(args.task)
        print(f"\n结果：{result}\n")
    else:
        # Interactive mode
        print("\n进入交互式模式。输入 'skills' 查看可用技能，输入 'quit' 退出。\n")

        while True:
            try:
                task = input("输入任务：").strip()

                if task.lower() in ("quit", "exit", "q"):
                    print("再见！")
                    break

                if not task:
                    continue

                # Handle special commands
                if task.lower() == "skills":
                    print_skills()
                    continue

                print()
                result = agent.execute_task(task)
                print(f"\n结果：{result}\n")

            except KeyboardInterrupt:
                print("\n\n中断。再见！")
                break
            except Exception as e:
                print(f"\n错误：{e}\n")


if __name__ == "__main__":
    main()
