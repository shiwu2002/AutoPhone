#!/usr/bin/env python3
"""Phone Agent - AI-powered phone automation

Main entry point for the Phone Agent application.
Provides programmatic API with multi-device parallel execution support.
"""

import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from phone_agent import PhoneAgent
from phone_agent.agent import AgentConfig
from phone_agent.device_factory import DeviceType, set_device_type, get_device_factory
from phone_agent.model import ModelConfig


# ============================================================================
# Programmatic API - For other projects to call
# ============================================================================

@dataclass
class TaskResult:
    """Task execution result."""
    success: bool
    answer: str
    error: Optional[str] = None
    steps: int = 0
    screenshot_base64: Optional[str] = None


@dataclass
class ParallelBatchResult:
    """Parallel batch task execution result."""
    total: int
    success_count: int
    failed_count: int
    device_results: List[Dict[str, Any]]  # Results per device
    results: List[TaskResult]  # Merged results
    output_file: Optional[str] = None
    total_time: float = 0.0  # Total execution time in seconds


class PhoneAgentAPI:
    """
    Phone Agent Programmatic Interface.
    
    Provides methods for other projects to call phone automation features.
    Supports multi-device parallel execution for batch tasks.
    
    Example:
        >>> from main import PhoneAgentAPI, ModelConfig, AgentConfig
        >>> 
        >>> # Initialize API
        >>> api = PhoneAgentAPI()
        >>> 
        >>> # Single task
        >>> result = api.run_task("打开微信")
        >>> print(result.answer)
        >>> 
        >>> # Batch tasks with multi-device parallel
        >>> batch_result = api.run_batch_parallel(
        ...     questions=["问题 1", "问题 2", "问题 3"],
        ...     task_template="请回答：{content}"
        ... )
        >>> print(f"Success: {batch_result.success_count}/{batch_result.total}")
        >>> print(f"Total time: {batch_result.total_time:.2f}s")
    """
    
    def __init__(
        self,
        model_config: Optional[ModelConfig] = None,
        agent_config: Optional[AgentConfig] = None,
        config_path: str = "config.json"
    ):
        """
        Initialize Phone Agent API.
        
        Args:
            model_config: Model configuration. If None, loads from config_path
            agent_config: Agent configuration. If None, loads from config_path
            config_path: Path to config.json
        """
        # Set device type globally
        set_device_type(DeviceType.ADB)
        
        # Load configuration from file if not provided
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
        """Load configuration from JSON file."""
        import json
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
        Run a single task on phone.
        
        Args:
            task: Task description in natural language
            save_screenshot: Whether to save screenshot
            verbose: Whether to show verbose output
            
        Returns:
            TaskResult with success status and answer
            
        Example:
            >>> api = PhoneAgentAPI()
            >>> result = api.run_task("打开微信并给张三发消息")
            >>> if result.success:
            ...     print(f"Answer: {result.answer}")
            >>> else:
            ...     print(f"Error: {result.error}")
        """
        # Create agent with temporary verbose setting
        original_verbose = self.agent_config.verbose
        self.agent_config.verbose = verbose or original_verbose
        
        try:
            agent = PhoneAgent(
                model_config=self.model_config,
                agent_config=self.agent_config,
            )
            
            answer = agent.run(task)
            
            screenshot_b64 = None
            if save_screenshot:
                try:
                    from phone_agent.device_factory import get_device_factory
                    screenshot = get_device_factory().get_screenshot(enable_compression=False)
                    screenshot_b64 = screenshot.base64_data
                except Exception as e:
                    print(f"Warning: Failed to get screenshot: {e}")
            
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
    
    def run_batch_from_file(
        self,
        file_path: str,
        task_template: str,
        output_path: Optional[str] = None,
        column: Optional[str] = None,
        embed_screenshot: bool = False,
        compare_answer: bool = False,
        max_questions: int = 0,
        verbose: bool = False
    ) -> BatchTaskResult:
        """
        Run batch tasks from Excel or TXT file.
        
        Args:
            file_path: Path to Excel/TXT file containing questions
            task_template: Task template, use {content} as placeholder
            output_path: Output file path (default: input_results.xlsx)
            column: Column name to read questions from (Excel only)
            embed_screenshot: Whether to embed screenshots in Excel
            compare_answer: Whether to compare with standard answers
            max_questions: Max questions to process (0 = all)
            verbose: Whether to show verbose output
            
        Returns:
            BatchTaskResult with statistics and detailed results
            
        Example:
            >>> api = PhoneAgentAPI()
            >>> result = api.run_batch_from_file(
            ...     file_path="questions.xlsx",
            ...     task_template="请回答：{content}",
            ...     embed_screenshot=True
            ... )
            >>> print(f"Total: {result.total}")
            >>> print(f"Success: {result.success_count}")
        """
        # Import excel_task module
        from bin.excel_task import (
            process_excel_questions,
            load_file_content,
            PANDAS_AVAILABLE
        )
        
        if not PANDAS_AVAILABLE and file_path.lower().endswith(('.xlsx', '.xls')):
            return BatchTaskResult(
                total=0,
                success_count=0,
                failed_count=0,
                results=[],
                output_file=None
            )
        
        # Determine output file
        if output_path is None:
            input_path = Path(file_path)
            output_path = str(input_path.parent / f"{input_path.stem}_results{input_path.suffix}")
        
        # Create temporary callback for progress tracking
        def progress_callback(current: int, total: int, question: str):
            print(f"\nProcessing {current}/{total}: {question[:50]}...")
        
        # Process questions
        original_verbose = self.agent_config.verbose
        self.agent_config.verbose = verbose or original_verbose
        
        try:
            results = process_excel_questions(
                excel_path=file_path,
                task_template=task_template,
                output_path=output_path,
                model_cfg=self.model_config,
                agent_cfg=self.agent_config,
                embed_screenshot=embed_screenshot,
                compare_answer=compare_answer,
                column=column,
                progress_callback=progress_callback
            )
            
            # Convert to TaskResult list
            task_results = []
            success_count = 0
            failed_count = 0
            
            for r in results:
                if r.get('success', False):
                    success_count += 1
                    task_results.append(TaskResult(
                        success=True,
                        answer=r.get('answer', ''),
                        steps=r.get('steps', 0),
                        screenshot_base64=r.get('screenshot_base64')
                    ))
                else:
                    failed_count += 1
                    task_results.append(TaskResult(
                        success=False,
                        answer="",
                        error=r.get('error', 'Unknown error')
                    ))
            
            return BatchTaskResult(
                total=len(results),
                success_count=success_count,
                failed_count=failed_count,
                results=task_results,
                output_file=output_path
            )
            
        except Exception as e:
            print(f"Batch execution failed: {e}")
            return BatchTaskResult(
                total=0,
                success_count=0,
                failed_count=0,
                results=[],
                output_file=None
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
        Run batch tasks in parallel across multiple devices.
        
        Automatically detects available devices and distributes tasks
        evenly across them for parallel execution.
        
        Args:
            questions: List of questions to process
            task_template: Task template, use {content} as placeholder
            embed_screenshot: Whether to save screenshots
            verbose: Whether to show verbose output
            max_workers: Max concurrent workers (default: number of devices)
            
        Returns:
            ParallelBatchResult with statistics and detailed results
            
        Example:
            >>> api = PhoneAgentAPI()
            >>> questions = ["问题 1", "问题 2", "问题 3", "问题 4"]
            >>> result = api.run_batch_parallel(
            ...     questions=questions,
            ...     task_template="请回答：{content}",
            ...     embed_screenshot=True
            ... )
            >>> print(f"Total: {result.total}")
            >>> print(f"Success: {result.success_count}")
            >>> print(f"Time: {result.total_time:.2f}s")
            >>> 
            >>> # Access per-device results
            >>> for device_result in result.device_results:
            ...     print(f"Device {device_result['device_id']}: {device_result['success_count']} success")
        """
        from phone_agent.parallel_executor import ParallelExecutor
        
        # Create parallel executor
        executor = ParallelExecutor(
            model_config=self.model_config,
            agent_config=self.agent_config,
            max_workers=max_workers
        )
        
        # Run parallel batch
        parallel_result = executor.run_parallel_batch(
            questions=questions,
            task_template=task_template,
            embed_screenshot=embed_screenshot,
            verbose=verbose
        )
        
        # Convert to our result type
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


# ============================================================================
# Standalone Execution - For direct script usage
# ============================================================================

def main():
    """Main entry point for standalone execution."""
    print("Phone Agent API - Multi-Device Parallel Execution")
    print("=" * 60)
    
    # Initialize API
    api = PhoneAgentAPI()
    
    # Get available devices
    devices = get_device_factory().list_devices()
    print(f"\nAvailable devices: {len(devices)}")
    for device in devices:
        print(f"  - {device.device_id}")
    
    if len(devices) == 0:
        print("\n❌ No devices connected. Please connect ADB devices.")
        return
    
    # Demo: Single task
    print("\n" + "=" * 60)
    print("Demo: Single Task Execution")
    print("=" * 60)
    
    result = api.run_task("查看时间", verbose=False)
    print(f"Result: {result.answer}")
    
    # Demo: Parallel batch execution
    if len(devices) > 1:
        print("\n" + "=" * 60)
        print("Demo: Multi-Device Parallel Batch Execution")
        print("=" * 60)
        
        questions = [
            "今天天气怎么样？",
            "北京到上海的高铁要多久？",
            "推荐几本好看的书",
            "如何学习 Python？",
            "世界上最大的海洋是哪个？"
        ]
        
        batch_result = api.run_batch_parallel(
            questions=questions,
            task_template="请回答：{content}",
            verbose=False
        )
        
        print(f"\n📊 Statistics:")
        print(f"  Total questions: {batch_result.total}")
        print(f"  Success: {batch_result.success_count}")
        print(f"  Failed: {batch_result.failed_count}")
        print(f"  Total time: {batch_result.total_time:.2f}s")
        
        print(f"\n📱 Device Results:")
        for dr in batch_result.device_results:
            print(f"  Device {dr['device_id']}: {dr['success_count']} success, {dr['failed_count']} failed")
        
        print(f"\n✅ Detailed Results:")
        for i, r in enumerate(batch_result.results[:3], 1):
            status = "✅" if r.success else "❌"
            print(f"  {i}. {status} {r.answer[:50] if r.answer else r.error}")
    else:
        print("\n⚠️  Only 1 device available, parallel execution not demonstrated.")
    
    print("\n" + "=" * 60)
    print("For more examples, see: examples/api_usage.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
