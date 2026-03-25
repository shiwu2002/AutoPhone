"""全局钩子注册示例 - 监控整个智能体系统。

此文件展示如何注册钩子来监控主 Agent 和所有 Skill 的执行过程。
将这些钩子注册到启动脚本中，可以实现全局监控。
"""

from phone_agent.hooks import register_hook, set_hook_enabled
from phone_agent.utils.logger import setup_logger

logger = setup_logger(__name__)


# ==================== 主 Agent 监控钩子 ====================

def on_master_dispatch(task: str, **kwargs):
    """主 Agent 接收到任务时触发。"""
    logger.info(f"[主 Agent] 接收任务：{task}")


def on_master_route(task: str, route: str, **kwargs):
    """主 Agent 任务路由时触发。"""
    route_names = {
        "liantong": "联通客服",
        "excel": "Excel 处理",
        "unsupported": "不支持的任务"
    }
    logger.info(f"[主 Agent] 路由到：{route_names.get(route, route)}")


# ==================== Skill 执行监控钩子 ====================

def on_skill_start(skill_id: str, **kwargs):
    """Skill 开始执行时触发。"""
    logger.info(f"[Skill] 开始执行：{skill_id}")


def on_skill_complete(skill_id: str, result: dict, **kwargs):
    """Skill 执行完成时触发。"""
    success = result.get("success", False)
    status = "✅" if success else "❌"
    logger.info(f"[Skill] {status} 完成：{skill_id}")


def on_skill_error(skill_id: str, error: str, **kwargs):
    """Skill 执行失败时触发。"""
    logger.error(f"[Skill] ❌ 失败：{skill_id} - {error}")


# ==================== 手机操作监控钩子 ====================

def on_app_changed(old_app: str, new_app: str, **kwargs):
    """应用切换时触发。"""
    logger.info(f"[手机] 应用切换：{old_app} → {new_app}")


def on_wait(duration: float, **kwargs):
    """执行 Wait 动作时触发。"""
    logger.info(f"[手机] 等待 {duration} 秒")


# ==================== 任务生命周期监控钩子 ====================

def on_task_start(task: str, **kwargs):
    """任务开始时触发。"""
    logger.info(f"[任务] 🚀 开始：{task}")


def on_task_end(task: str, result: str, **kwargs):
    """任务结束时触发。"""
    logger.info(f"[任务] 🏁 结束：{result[:100] if result else '无结果'}")


# ==================== 注册所有钩子 ====================

def setup_global_hooks():
    """注册所有全局监控钩子。"""
    # 主 Agent 监控
    register_hook("on_master_dispatch", on_master_dispatch, "主 Agent 接收任务")
    register_hook("on_master_route", on_master_route, "主 Agent 任务路由")

    # Skill 监控
    register_hook("on_skill_start", on_skill_start, "Skill 开始执行")
    register_hook("on_skill_complete", on_skill_complete, "Skill 执行完成")
    register_hook("on_skill_error", on_skill_error, "Skill 执行失败")

    # 手机操作监控
    register_hook("on_app_changed", on_app_changed, "应用切换")
    register_hook("on_wait", on_wait, "等待动作")

    # 任务生命周期监控
    register_hook("on_task_start", on_task_start, "任务开始")
    register_hook("on_task_end", on_task_end, "任务结束")

    logger.info("所有全局监控钩子已注册")


# ==================== 钩子启用/禁用配置 ====================

def enable_verbose_mode():
    """启用详细模式（所有钩子）。"""
    set_hook_enabled("on_master_dispatch", True)
    set_hook_enabled("on_master_route", True)
    set_hook_enabled("on_skill_start", True)
    set_hook_enabled("on_skill_complete", True)
    set_hook_enabled("on_app_changed", True)
    set_hook_enabled("on_wait", True)
    set_hook_enabled("on_task_start", True)
    set_hook_enabled("on_task_end", True)


def enable_quiet_mode():
    """启用静默模式（仅错误）。"""
    # 只保留错误钩子
    set_hook_enabled("on_skill_error", True)
    # 禁用其他钩子
    for hook in ["on_master_dispatch", "on_master_route", "on_skill_start",
                 "on_skill_complete", "on_app_changed", "on_wait",
                 "on_task_start", "on_task_end"]:
        set_hook_enabled(hook, False)


# 自动注册
setup_global_hooks()
