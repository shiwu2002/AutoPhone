#!/usr/bin/env python3
"""
Phone Agent API - 程序化接口

为其他项目提供手机自动化功能的调用接口。
支持多设备并行执行批量任务。
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from phone_agent import PhoneAgent, AgentConfig, ModelConfig
from phone_agent.device_factory import DeviceType, set_device_factory


@dataclass
class TaskResult:
    """单个任务执行结果。"""
    success: bool  # 是否成功
    answer: str  # 答案/结果
    error: Optional[str] = None  # 错误信息
    steps: int = 0  # 执行步数
    screenshot_base64: Optional[str] = None  # 截图的 base64 数据


@dataclass
class ParallelBatchResult:
    """多设备并行批量任务执行结果。"""
    total: int  # 总问题数
    success_count: int  # 成功数
    failed_count: int  # 失败数
    device_results: List[Dict[str, Any]]  # 各设备的详细结果
    results: List[TaskResult]  # 合并后的结果（按原顺序）
    output_file: Optional[str] = None  # 输出文件路径
    total_time: float = 0.0  # 总耗时（秒）


class PhoneAgentAPI:
    """
    Phone Agent 程序化接口。
    
    为其他项目提供调用手机自动化功能的方法。
    支持多设备并行执行批量任务。
    
    示例:
        >>> from phone_agent.api import PhoneAgentAPI, ModelConfig, AgentConfig
        
        >>> # 初始化 API
        >>> api = PhoneAgentAPI()
        
        >>> # 单个任务
        >>> result = api.run_task("打开微信")
        >>> print(result.answer)
        
        >>> # 多设备并行批量任务
        >>> batch_result = api.run_batch_parallel(
        ...     questions=["问题 1", "问题 2", "问题 3"],
        ...     task_template="请回答：{content}"
        ... )
        >>> print(f"成功：{batch_result.success_count}/{batch_result.total}")
        >>> print(f"总耗时：{batch_result.total_time:.2f}秒")
    """
    
    def __init__(
        self,
        model_config: Optional[ModelConfig] = None,
        agent_config: Optional[AgentConfig] = None,
        config_path: str = "config.json"
    ):
        """
        初始化 Phone Agent API。
        
        参数:
            model_config: 模型配置。如果为 None，则从 config_path 加载
            agent_config: Agent 配置。如果为 None，则从 config_path 加载
            config_path: config.json 文件路径
        """
        # 全局设置设备类型
        set_device_factory(DeviceType.ADB)
        
        # 如果未提供配置，则从文件加载
        if model_config is None or agent_config is None:
            config = self._load_config(config_path)
            
            if model_config is None:
                model_config_dict = config.get('model', {})
                provider = model_config_dict.get('provider', 'local')
                provider_config = model_config_dict.get(provider, {})
                
                model_config = ModelConfig(
                    base_url=provider_config.get('base_url', 'http://localhost:8000/v1'),
                    model_name=provider_config.get('model', 'claude-opus-4-6-20251101'),
                    api_key=provider_config.get('api_key', ''),
                    lang='cn',
                    use_thinking=model_config_dict.get('use_thinking', False),
                    provider=provider,
                )
            
            if agent_config is None:
                agent_config_dict = config.get('agent', {})
                agent_config = AgentConfig(
                    max_steps=agent_config_dict.get('max_steps', 50),
                    verbose=agent_config_dict.get('verbose', True),
                    lang=agent_config_dict.get('lang', 'cn'),
                )
        
        self.model_config = model_config
        self.agent_config = agent_config
        self.config_path = config_path
    
    def _load_config(self, config_path: str) -> dict:
        """从 JSON 文件加载配置。"""
        import json
        from pathlib import Path
        
        path = Path(config_path)
        if not path.exists():
            return {}
        
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def run_task(
        self,
        task: str,
        save_screenshot: bool = False,
        verbose: bool = False
    ) -> TaskResult:
        """
        在手机上执行单个任务。
        
        参数:
            task: 自然语言描述的任务
            save_screenshot: 是否保存截图
            verbose: 是否显示详细输出
            
        返回:
            TaskResult 对象，包含执行状态和答案
            
        示例:
            >>> api = PhoneAgentAPI()
            >>> result = api.run_task("打开微信并给张三发消息")
            >>> if result.success:
            ...     print(f"答案：{result.answer}")
            ... else:
            ...     print(f"错误：{result.error}")
        """
        # 设置临时 verbose 模式
        original_verbose = self.agent_config.verbose
        self.agent_config.verbose = verbose or original_verbose
        
        try:
            # 创建 Agent 实例
            agent = PhoneAgent(
                model_config=self.model_config,
                agent_config=self.agent_config,
            )
            
            # 执行任务
            answer = agent.run(task)
            
            # 获取截图（如果需要）
            screenshot_b64 = None
            if save_screenshot:
                try:
                    from phone_agent.device_factory import get_device_factory
                    screenshot = get_device_factory().get_screenshot(enable_compression=False)
                    screenshot_b64 = screenshot.base64_data
                except Exception as e:
                    print(f"警告：获取截图失败：{e}")
            
            return TaskResult(
                success=True,
                answer=answer,
                steps=agent.step_count,
                screenshot_base64=screenshot_b64
            )
            
        except Exception as e:
            return TaskResult(
                success=False,
                answer="",
                error=str(e),
                steps=0
            )
        finally:
            self.agent_config.verbose = original_verbose
    
    def run_batch_parallel(
        self,
        questions: List[str],
        task_template: str,
        embed_screenshot: bool = False,
        verbose: bool = False,
        max_workers: Optional[int] = None
    ) -> ParallelBatchResult:
        """
        多设备并行执行批量任务。
        
        自动检测可用设备，并将任务均匀分配到各个设备并发执行。
        
        参数:
            questions: 问题列表
            task_template: 任务模板，使用 {content} 作为占位符
            embed_screenshot: 是否保存截图
            verbose: 是否显示详细输出
            max_workers: 最大工作线程数（默认等于设备数）
            
        返回:
            ParallelBatchResult 对象，包含统计信息和详细结果
            
        示例:
            >>> api = PhoneAgentAPI()
            >>> questions = ["问题 1", "问题 2", "问题 3", "问题 4"]
            >>> result = api.run_batch_parallel(
            ...     questions=questions,
            ...     task_template="请回答：{content}",
            ...     embed_screenshot=True
            ... )
            >>> print(f"总计：{result.total}")
            >>> print(f"成功：{result.success_count}")
            >>> print(f"耗时：{result.total_time:.2f}秒")
            
            >>> # 查看各设备的执行结果
            >>> for device_result in result.device_results:
            ...     print(f"设备 {device_result['device_id']}: {device_result['success_count']} 个成功")
        """
        from phone_agent.parallel_executor import ParallelExecutor
        
        # 创建并行执行器
        executor = ParallelExecutor(
            model_config=self.model_config,
            agent_config=self.agent_config,
            max_workers=max_workers
        )
        
        # 执行并行批量任务
        parallel_result = executor.run_parallel_batch(
            questions=questions,
            task_template=task_template,
            embed_screenshot=embed_screenshot,
            verbose=verbose
        )
        
        # 转换为我们的结果类型
        task_results = []
        for r in parallel_result.merged_results:
            if r.get('success', False):
                task_results.append(TaskResult(
                    success=True,
                    answer=r.get('answer', ''),
                    steps=r.get('steps', 0),
                    screenshot_base64=r.get('screenshot_base64')
                ))
            else:
                task_results.append(TaskResult(
                    success=False,
                    answer='',
                    error=r.get('error', 'Unknown error')
                ))
        
        return ParallelBatchResult(
            total=parallel_result.total,
            success_count=parallel_result.success_count,
            failed_count=parallel_result.failed_count,
            device_results=[dr.to_dict() for dr in parallel_result.device_results],
            results=task_results,
            output_file=None,
            total_time=parallel_result.total_time
        )
