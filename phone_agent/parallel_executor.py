"""多设备并行执行器 - 支持多设备并发执行任务。"""

import asyncio
import concurrent.futures
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from phone_agent import PhoneAgent
from phone_agent.agent import AgentConfig
from phone_agent.device_factory import get_device_factory
from phone_agent.model import ModelConfig
from phone_agent.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class DeviceTask:
    """分配给设备的任务。"""
    device_id: str
    questions: List[str]
    task_template: str
    index_start: int
    index_end: int


@dataclass
class DeviceResult:
    """单个设备的执行结果。"""
    device_id: str
    results: List[Dict[str, Any]]
    success_count: int = 0
    failed_count: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        """转换为字典。"""
        return {
            "device_id": self.device_id,
            "results": self.results,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "start_time": self.start_time.isoformat() if self.start_time else "",
            "end_time": self.end_time.isoformat() if self.end_time else "",
            "error": self.error or ""
        }


@dataclass
class ParallelBatchResult:
    """并行批量执行的总结果。"""
    total: int
    success_count: int
    failed_count: int
    device_results: List[DeviceResult]
    merged_results: List[Dict[str, Any]]
    output_file: Optional[str] = None
    total_time: float = 0.0
    
    def to_dict(self) -> dict:
        """转换为字典。"""
        return {
            "total": self.total,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "device_results": [dr.to_dict() for dr in self.device_results],
            "merged_results": self.merged_results,
            "output_file": self.output_file or "",
            "total_time": self.total_time
        }


class ParallelExecutor:
    """
    多设备并行执行器。
    
    自动检测可用设备，将任务分配到多个设备并发执行。
    
    Example:
        >>> executor = ParallelExecutor(model_config, agent_config)
        >>> devices = executor.get_available_devices()
        >>> if len(devices) > 1:
        ...     result = executor.run_parallel_batch(questions, task_template)
    """
    
    def __init__(
        self,
        model_config: ModelConfig,
        agent_config: AgentConfig,
        max_workers: Optional[int] = None
    ):
        """
        初始化并行执行器。
        
        Args:
            model_config: 模型配置
            agent_config: Agent 配置
            max_workers: 最大工作线程数（默认等于设备数）
        """
        self.model_config = model_config
        self.agent_config = agent_config
        self.max_workers = max_workers
        
        self.device_factory = get_device_factory()
        self._available_devices: List[str] = []
        
    def get_available_devices(self) -> List[str]:
        """
        获取可用的设备列表。
        
        Returns:
            设备 ID 列表
        """
        devices = self.device_factory.list_devices()
        self._available_devices = [d.device_id for d in devices]
        logger.info(f"发现 {len(self._available_devices)} 个设备：{self._available_devices}")
        return self._available_devices
    
    def distribute_tasks(
        self,
        questions: List[str],
        task_template: str
    ) -> List[DeviceTask]:
        """
        将任务均匀分配到各个设备。
        
        Args:
            questions: 问题列表
            task_template: 任务模板
            
        Returns:
            设备任务列表
        """
        devices = self.get_available_devices()
        if not devices:
            raise ValueError("没有可用设备")
        
        num_devices = len(devices)
        total_questions = len(questions)
        
        # 计算每个设备的问题数
        base_count = total_questions // num_devices
        remainder = total_questions % num_devices
        
        tasks = []
        current_index = 0
        
        for i, device_id in enumerate(devices):
            # 前 remainder 个设备多分配一个问题
            count = base_count + (1 if i < remainder else 0)
            
            if count > 0:
                device_questions = questions[current_index:current_index + count]
                
                tasks.append(DeviceTask(
                    device_id=device_id,
                    questions=device_questions,
                    task_template=task_template,
                    index_start=current_index,
                    index_end=current_index + count
                ))
                
                current_index += count
        
        logger.info(f"任务分配完成：{len(tasks)} 个设备任务")
        for task in tasks:
            logger.info(f"  设备 {task.device_id}: {len(task.questions)} 个问题")
        
        return tasks
    
    def run_device_task(
        self,
        device_task: DeviceTask,
        embed_screenshot: bool = False,
        verbose: bool = False
    ) -> DeviceResult:
        """
        在单个设备上执行任务。
        
        Args:
            device_task: 设备任务
            embed_screenshot: 是否保存截图
            verbose: 是否显示详细输出
            
        Returns:
            设备执行结果
        """
        start_time = datetime.now()
        results = []
        success_count = 0
        failed_count = 0
        
        logger.info(f"设备 {device_task.device_id} 开始执行 {len(device_task.questions)} 个任务")
        
        try:
            # 为当前设备创建 Agent
            device_agent_config = AgentConfig(
                max_steps=self.agent_config.max_steps,
                device_id=device_task.device_id,
                verbose=verbose,
                lang=self.agent_config.lang
            )
            
            agent = PhoneAgent(
                model_config=self.model_config,
                agent_config=device_agent_config
            )
            
            for i, question in enumerate(device_task.questions):
                try:
                    # 构建完整任务
                    if "{content}" in device_task.task_template:
                        full_task = device_task.task_template.replace("{content}", question)
                    else:
                        full_task = f"{device_task.task_template}\n\n问题：{question}"
                    
                    # 执行任务
                    answer = agent.run(full_task)
                    
                    # 获取截图（如果需要）
                    screenshot_b64 = None
                    if embed_screenshot:
                        try:
                            screenshot = self.device_factory.get_screenshot(
                                device_id=device_task.device_id,
                                enable_compression=False
                            )
                            screenshot_b64 = screenshot.base64_data
                        except Exception as e:
                            logger.warning(f"获取截图失败：{e}")
                    
                    # 记录结果
                    results.append({
                        'question': question,
                        'answer': answer,
                        'success': True,
                        'steps': agent.step_count,
                        'screenshot_base64': screenshot_b64,
                        'device_id': device_task.device_id,
                        'global_index': device_task.index_start + i
                    })
                    
                    success_count += 1
                    
                    logger.info(f"设备 {device_task.device_id} 完成 {i+1}/{len(device_task.questions)}: {answer[:50]}...")
                    
                    # 重置 Agent 状态
                    agent.reset()
                    
                except Exception as e:
                    logger.error(f"设备 {device_task.device_id} 任务失败：{e}")
                    results.append({
                        'question': question,
                        'answer': '',
                        'success': False,
                        'error': str(e),
                        'device_id': device_task.device_id,
                        'global_index': device_task.index_start + i
                    })
                    failed_count += 1
            
            end_time = datetime.now()
            
            return DeviceResult(
                device_id=device_task.device_id,
                results=results,
                success_count=success_count,
                failed_count=failed_count,
                start_time=start_time,
                end_time=end_time
            )
            
        except Exception as e:
            logger.error(f"设备 {device_task.device_id} 执行失败：{e}")
            end_time = datetime.now()
            
            return DeviceResult(
                device_id=device_task.device_id,
                results=[],
                success_count=0,
                failed_count=len(device_task.questions),
                start_time=start_time,
                end_time=end_time,
                error=str(e)
            )
    
    def run_parallel_batch(
        self,
        questions: List[str],
        task_template: str,
        embed_screenshot: bool = False,
        verbose: bool = False
    ) -> ParallelBatchResult:
        """
        并行执行批量任务。
        
        Args:
            questions: 问题列表
            task_template: 任务模板
            embed_screenshot: 是否保存截图
            verbose: 是否显示详细输出
            
        Returns:
            并行执行结果
        """
        overall_start = datetime.now()
        
        # 获取可用设备
        devices = self.get_available_devices()
        
        if len(devices) == 0:
            raise ValueError("没有可用设备")
        
        # 如果只有 1 个设备，使用串行执行
        if len(devices) == 1:
            logger.info("只有 1 个设备，使用串行执行模式")
            single_task = DeviceTask(
                device_id=devices[0],
                questions=questions,
                task_template=task_template,
                index_start=0,
                index_end=len(questions)
            )
            
            device_result = self.run_device_task(
                single_task,
                embed_screenshot=embed_screenshot,
                verbose=verbose
            )
            
            # 合并结果
            merged = sorted(device_result.results, key=lambda x: x['global_index'])
            for r in merged:
                del r['global_index']
            
            overall_end = datetime.now()
            
            return ParallelBatchResult(
                total=len(questions),
                success_count=device_result.success_count,
                failed_count=device_result.failed_count,
                device_results=[device_result],
                merged_results=merged,
                total_time=(overall_end - overall_start).total_seconds()
            )
        
        # 多设备并行执行
        logger.info(f"开始并行执行：{len(devices)} 个设备，{len(questions)} 个问题")
        
        # 分配任务
        device_tasks = self.distribute_tasks(questions, task_template)
        
        # 使用线程池并行执行
        max_workers = self.max_workers or len(devices)
        device_results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self.run_device_task,
                    task,
                    embed_screenshot,
                    verbose
                ): task for task in device_tasks
            }
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    device_results.append(result)
                except Exception as e:
                    logger.error(f"设备执行异常：{e}")
        
        # 合并所有结果
        all_results = []
        total_success = 0
        total_failed = 0
        
        for dr in device_results:
            all_results.extend(dr.results)
            total_success += dr.success_count
            total_failed += dr.failed_count
        
        # 按全局索引排序
        merged_results = sorted(all_results, key=lambda x: x['global_index'])
        
        # 移除内部使用的索引
        for r in merged_results:
            del r['global_index']
        
        overall_end = datetime.now()
        total_time = (overall_end - overall_start).total_seconds()
        
        logger.info(f"并行执行完成：总耗时 {total_time:.2f}秒")
        logger.info(f"成功：{total_success}, 失败：{total_failed}")
        
        return ParallelBatchResult(
            total=len(questions),
            success_count=total_success,
            failed_count=total_failed,
            device_results=device_results,
            merged_results=merged_results,
            total_time=total_time
        )
