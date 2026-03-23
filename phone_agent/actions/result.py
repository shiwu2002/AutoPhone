"""动作处理结果。"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ActionResult:
    """动作执行的结果。"""

    success: bool
    should_finish: bool
    message: str | None = None
    requires_confirmation: bool = False
