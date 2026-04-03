"""
允许使用 `python -m phone_agent` 方式运行 CLI。
"""

from .cli import main

if __name__ == "__main__":
    # 入口转发到 Typer 应用
    main()
