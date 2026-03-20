#!/usr/bin/env python3
"""
Excel 任务执行器 - 读取 Excel 文件内容，让智能体在手机上执行任务

使用示例：
    python excel_task.py --file 工作簿 2.xlsx --task "打开微信，给峰峰峰回路转发送文档里的所有问题"
"""

import argparse
import json
import sys
from pathlib import Path

# Try to import pandas
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

from phone_agent import PhoneAgent
from phone_agent.agent import AgentConfig
from phone_agent.config import get_system_prompt
from phone_agent.model import ModelConfig


def load_excel_content(file_path: str, column: str = None) -> str:
    """
    读取 Excel 文件内容

    Args:
        file_path: Excel 文件路径
        column: 指定读取的列名（可选）

    Returns:
        格式化的文本内容
    """
    if not PANDAS_AVAILABLE:
        raise ImportError("需要安装 pandas: pip install pandas openpyxl")

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在：{file_path}")

    # 读取 Excel
    df = pd.read_excel(path)

    # 获取所有列名
    columns = df.columns.tolist()

    # 如果指定了列，只读取该列
    if column:
        if column not in columns:
            raise ValueError(f"列'{column}'不存在，可用列：{columns}")
        items = df[column].dropna().tolist()
        return "\n".join([f"{i+1}. {str(item)}" for i, item in enumerate(items)])

    # 否则读取所有列
    # 查找"问题"列（不区分大小写）
    question_col = None
    for col in columns:
        if '问题' in col.lower() or 'question' in col.lower():
            question_col = col
            break

    if question_col:
        items = df[question_col].dropna().tolist()
        return "\n".join([f"{i+1}. {str(item)}" for i, item in enumerate(items)])

    # 如果没有找到问题列，返回所有数据
    lines = []
    for idx, row in df.iterrows():
        row_str = "，".join([f"{col}: {row[col]}" for col in columns if pd.notna(row[col])])
        lines.append(f"{idx+1}. {row_str}")

    return "\n".join(lines)


def load_txt_content(file_path: str) -> str:
    """读取 TXT 文件内容（每行一个）"""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在：{file_path}")

    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    items = [line.strip() for line in lines if line.strip()]
    return "\n".join([f"{i+1}. {item}" for i, item in enumerate(items)])


def load_file_content(file_path: str, column: str = None) -> str:
    """根据文件类型读取内容"""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in ['.xlsx', '.xls']:
        return load_excel_content(file_path, column)
    elif suffix == '.txt':
        return load_txt_content(file_path)
    else:
        raise ValueError(f"不支持的文件格式：{suffix}")


def load_config(config_path: str = "config.json") -> dict:
    """加载配置文件"""
    path = Path(config_path)
    if not path.exists():
        return {}

    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(
        description="读取 Excel/TXT 文件内容，让智能体在手机上执行任务",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 读取 Excel 问题列表，打开微信发送给某人
    python excel_task.py --file 工作簿 2.xlsx --task "打开微信，给峰峰峰回路转发送文档里的所有问题"

    # 指定读取的列
    python excel_task.py --file questions.xlsx --column 问题 --task "打开微信，把所有问题发给张三"

    # 读取 TXT 文件
    python excel_task.py --file questions.txt --task "在抖音搜索文档里的每个问题"
        """
    )

    parser.add_argument(
        "--file", "-f",
        type=str,
        required=True,
        help="Excel 或 TXT 文件路径"
    )

    parser.add_argument(
        "--task", "-t",
        type=str,
        required=True,
        help="任务描述，可以使用 {content} 占位符引用文件内容"
    )

    parser.add_argument(
        "--column", "-c",
        type=str,
        default=None,
        help="指定读取的 Excel 列名（默认自动检测'问题'列）"
    )

    parser.add_argument(
        "--preview",
        action="store_true",
        help="只预览文件内容，不执行任务"
    )

    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="配置文件路径（默认：config.json）"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细输出"
    )

    args = parser.parse_args()

    # 检查 pandas
    if not PANDAS_AVAILABLE and args.file.lower().endswith(('.xlsx', '.xls')):
        print("❌ 错误：读取 Excel 需要安装 pandas")
        print("   请运行：pip install pandas openpyxl")
        sys.exit(1)

    # 加载文件内容
    print(f"📄 读取文件：{args.file}")
    try:
        content = load_file_content(args.file, args.column)
    except Exception as e:
        print(f"❌ 读取文件失败：{e}")
        sys.exit(1)

    # 预览模式
    if args.preview:
        print("\n📋 文件内容预览：")
        print("-" * 50)
        lines = content.split("\n")
        for line in lines[:10]:  # 只显示前 10 行
            print(f"  {line}")
        if len(lines) > 10:
            print(f"  ... 还有 {len(lines) - 10} 行")
        print("-" * 50)
        return

    # 构建任务提示
    # 关键：明确告诉智能体文件已在电脑上读取，不是在手机里
    if "{content}" in args.task:
        full_task = f"""【重要说明】
我已经从电脑上的文件读取了以下内容，请直接使用这些内容执行任务。
注意：文件已经读取完成，不需要在手机上查找或打开任何文件。

文件内容：
---
{content}
---

用户任务：{args.task.replace("{content}", "上述内容")}
"""
    else:
        full_task = f"""【重要说明】
我已经从电脑上的文件 "{args.file}" 中读取了所有内容。
注意：文件已经读取完成，不需要在手机上查找或打开任何文件。
请直接根据以下文件内容执行任务。

=== 文件内容开始 ===
{content}
=== 文件内容结束 ===

用户任务：{args.task}

请按照上述任务要求，在手机执行相应操作。
如果需要发送文件内容，请直接逐条发送上述列表中的内容。
"""

    # 加载配置
    config = load_config(args.config)
    model_config_dict = config.get('model', {})
    agent_config_dict = config.get('agent', {})

    # 创建模型配置
    model_cfg = ModelConfig(
        base_url=model_config_dict.get('base_url', 'http://localhost:11434/v1'),
        model_name=model_config_dict.get('model_name', 'qwen3.5:4b'),
        api_key=model_config_dict.get('api_key', 'ollama'),
        use_thinking=model_config_dict.get('use_thinking', False),
        lang=agent_config_dict.get('lang', 'cn'),
    )

    # 创建 Agent 配置，添加自定义 system prompt
    base_prompt = get_system_prompt(agent_config_dict.get('lang', 'cn'))
    file_task_prompt = """

【文件任务特别说明】
- 用户提到的文件（如 Excel、TXT）已经在电脑上读取完成
- 文件内容已经提供在用户任务中
- 不要在手机里查找或打开任何文件
- 直接根据提供的文件内容执行任务即可
"""
    custom_system_prompt = base_prompt + file_task_prompt

    agent_cfg = AgentConfig(
        max_steps=agent_config_dict.get('max_steps', 50),
        verbose=args.verbose,
        lang=agent_config_dict.get('lang', 'cn'),
        system_prompt=custom_system_prompt,
    )

    print("\n🤖 开始执行任务...")
    print(f"   任务：{args.task[:50]}..." if len(args.task) > 50 else f"   任务：{args.task}")
    print(f"   文件内容：共 {len(content.split(chr(10)))} 行")
    print("-" * 50)

    # 创建并运行 Agent
    agent = PhoneAgent(
        model_config=model_cfg,
        agent_config=agent_cfg,
    )

    try:
        result = agent.run(full_task)
        print("\n" + "=" * 50)
        print(f"✅ 任务完成：{result}")
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    except Exception as e:
        print(f"\n❌ 任务失败：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
