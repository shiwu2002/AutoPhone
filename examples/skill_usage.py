#!/usr/bin/env python3
"""
PhoneAgent Skills 使用示例

展示如何使用 PhoneAgent Skills 系统执行各种任务。
"""

import sys
import json
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from mainAgent.skill_engine import get_manager


def example_list_skills():
    """示例 1：列出所有技能书"""
    print("=" * 60)
    print("示例 1：列出所有技能书")
    print("=" * 60)

    manager = get_manager()
    books = manager.list_books()

    for book_id in books:
        book = manager.get_book(book_id)
        print(f"\n{book.icon} {book.name} ({book.id})")
        print(f"   {book.description}")
        print(f"   版本：{book.version}")
        print(f"   子技能数量：{len(book.sub_skills)}")
        for sk in book.sub_skills:
            print(f"     - {sk.name} ({sk.id}): {sk.description}")


def example_build_prompt():
    """示例 2：构建带占位符的提示词"""
    print("\n" + "=" * 60)
    print("示例 2：构建带占位符的提示词")
    print("=" * 60)

    manager = get_manager()

    # 示例 2a：联通客服问答
    print("\n--- 联通客服问答 ---")
    prompt = manager.build_prompt(
        'liantong_service',
        'query_ai_cs',
        question='联通智家是什么？'
    )
    print(f"提示词:\n{prompt}")

    # 示例 2b：执行手机任务
    print("\n--- 执行手机任务 ---")
    prompt = manager.build_prompt(
        'phoneagent_tools',
        'execute_task',
        task='打开微信给张三发消息：晚上好',
        model_provider='local',
        model_name='qwen3.5:4b',
        max_steps=30
    )
    print(f"提示词:\n{prompt[:300]}...")


def example_execute_skill():
    """示例 3：执行子技能（需要实际环境和设备）"""
    print("\n" + "=" * 60)
    print("示例 3：执行子技能")
    print("=" * 60)

    manager = get_manager()

    # 示例 3a：查询历史记录（不需要设备）
    print("\n--- 查询历史记录 ---")
    try:
        result = manager.execute(
            'phoneagent_tools',
            'query_history',
            limit=5,
            success_filter='all'
        )
        print(f"执行结果：{json.dumps(result, ensure_ascii=False, indent=2)}")
    except Exception as e:
        print(f"执行失败：{e}")

    # 示例 3b：获取统计信息
    print("\n--- 获取统计信息 ---")
    try:
        result = manager.execute(
            'phoneagent_tools',
            'get_stats'
        )
        print(f"执行结果：{json.dumps(result, ensure_ascii=False, indent=2)}")
    except Exception as e:
        print(f"执行失败：{e}")


def example_json_communication():
    """示例 4：使用 JSON 进行输入输出"""
    print("\n" + "=" * 60)
    print("示例 4：使用 JSON 进行输入输出")
    print("=" * 60)

    manager = get_manager()

    # 获取子技能配置
    sub_skill = manager.get_sub_skill('phoneagent_tools', 'execute_task')
    print(f"\n子技能：{sub_skill.name}")
    print(f"描述：{sub_skill.description}")

    print("\n输入参数:")
    for param in sub_skill.input_params:
        required = "必填" if param.required else "选填"
        default = f"(默认：{param.default})" if param.default is not None else ""
        print(f"  - {param.name} ({param.type}): {param.description} [{required}] {default}")

    print(f"\n输出配置:")
    if sub_skill.output_config:
        print(f"  - 字段：{sub_skill.output_config.field}")
        print(f"  - 类型：{sub_skill.output_config.type}")
        print(f"  - 描述：{sub_skill.output_config.description}")


def example_custom_skill_workflow():
    """示例 5：自定义技能工作流"""
    print("\n" + "=" * 60)
    print("示例 5：自定义技能工作流")
    print("=" * 60)

    print("""
你可以创建自定义的工作流，组合多个子技能：

1. 首先连接设备
   manager.execute('phoneagent_tools', 'adb_connect',
                   connection_request='连接设备',
                   device_address='192.168.1.100:5555')

2. 配置模型
   manager.execute('phoneagent_tools', 'model_config',
                   config_request='使用 OpenAI 兼容接口',
                   current_config='{}')

3. 执行任务
   manager.execute('phoneagent_tools', 'execute_task',
                   task='打开抖音搜索猫咪视频',
                   model_provider='local',
                   model_name='qwen3.5:4b',
                   max_steps=30)

4. 查询结果
   manager.execute('phoneagent_tools', 'query_history', limit=1)

5. 获取统计
   manager.execute('phoneagent_tools', 'get_stats')
""")


def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("PhoneAgent Skills 使用示例")
    print("=" * 60)

    example_list_skills()
    example_build_prompt()
    example_execute_skill()
    example_json_communication()
    example_custom_skill_workflow()

    print("\n" + "=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)


if __name__ == '__main__':
    main()
