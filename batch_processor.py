#!/usr/bin/env python3
"""
Excel 批量问答处理 - 多设备并行版

用法：
    python batch_processor.py --input 问题.xlsx
    python batch_processor.py --input 问题.xlsx --output 答案.xlsx
"""

import argparse
import pandas as pd
from pathlib import Path
from main import PhoneAgentAPI


def process_excel(
    input_path: str,
    output_path: str = None,
    question_column: str = "问题",
    task_template: str = "请回答：{content}",
    verbose: bool = False
):
    """
    读取 Excel 中的问题，批量执行后保存答案到原文档。
    
    参数:
        input_path: 输入 Excel 文件路径
        output_path: 输出 Excel 文件路径（默认：input_answers.xlsx）
        question_column: 问题所在的列名
        task_template: 任务模板，{content} 会被替换为实际问题
        verbose: 是否显示详细输出
    """
    # 确定输出文件
    if output_path is None:
        input_file = Path(input_path)
        output_path = input_file.parent / f"{input_file.stem}_answers{input_file.suffix}"
    
    print(f"📖 读取文件：{input_path}")
    print(f"📝 问题列：{question_column}")
    print(f"💾 输出文件：{output_path}")
    print("-" * 60)
    
    # 读取 Excel
    df = pd.read_excel(input_path)
    
    # 检查列是否存在
    if question_column not in df.columns:
        print(f"❌ 错误：找不到列 '{question_column}'")
        print(f"   可用列：{list(df.columns)}")
        return
    
    # 提取问题
    questions = df[question_column].dropna().astype(str).tolist()
    questions = [q.strip() for q in questions if q.strip() and q != 'nan']
    
    if not questions:
        print("❌ 错误：没有找到任何问题")
        return
    
    print(f"✅ 找到 {len(questions)} 个问题")
    print("-" * 60)
    
    # 初始化 API 并执行
    api = PhoneAgentAPI()
    
    print("🚀 开始批量执行...")
    result = api.run_batch_parallel(
        questions=questions,
        task_template=task_template,
        verbose=verbose
    )
    
    # 输出统计
    print("\n" + "=" * 60)
    print(f"✅ 执行完成")
    print(f"   总计：{result.total}")
    print(f"   成功：{result.success_count}")
    print(f"   失败：{result.failed_count}")
    print(f"   耗时：{result.total_time:.2f}秒")
    print("=" * 60)
    
    # 添加答案列到 DataFrame
    answers = [r.answer for r in result.results]
    df['答案'] = answers
    
    # 保存结果
    df.to_excel(output_path, index=False, engine='openpyxl')
    print(f"\n💾 已保存到：{output_path}")
    print(f"   新增列：答案")
    
    # 显示前几个结果示例
    print("\n" + "-" * 60)
    print("结果示例（前 3 个）:")
    print("-" * 60)
    for i in range(min(3, len(questions))):
        print(f"\n{i+1}. 问题：{questions[i][:50]}...")
        print(f"   答案：{answers[i][:100]}...")


def main():
    parser = argparse.ArgumentParser(
        description="Excel 批量问答处理（多设备并行）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 基础使用
    python batch_processor.py --input 问题.xlsx
    
    # 指定输出文件和自定义模板
    python batch_processor.py --input 问题.xlsx --output 答案.xlsx --template "请详细解答：{content}"
        """
    )
    
    parser.add_argument("--input", "-i", type=str, required=True, help="输入 Excel 文件路径")
    parser.add_argument("--output", "-o", type=str, default=None, help="输出 Excel 文件路径")
    parser.add_argument("--column", "-c", type=str, default="问题", help="问题所在的列名（默认：问题）")
    parser.add_argument("--template", "-t", type=str, default="请回答：{content}", help="任务模板（默认：请回答：{content}）")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细输出")
    
    args = parser.parse_args()
    
    process_excel(
        input_path=args.input,
        output_path=args.output,
        question_column=args.column,
        task_template=args.template,
        verbose=args.verbose
    )


if __name__ == "__main__":
    main()
