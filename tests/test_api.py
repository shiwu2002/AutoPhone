#!/usr/bin/env python3
"""
Phone Agent API 测试脚本

验证 API 接口是否可以正常初始化和调用。
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_import():
    """测试导入"""
    print("测试 1: 导入模块...")
    try:
        from main import PhoneAgentAPI, ModelConfig, AgentConfig, TaskResult, BatchTaskResult
        print("✅ 导入成功")
        return True
    except Exception as e:
        print(f"❌ 导入失败：{e}")
        return False


def test_api_init():
    """测试 API 初始化"""
    print("\n测试 2: 初始化 API...")
    try:
        from main import PhoneAgentAPI
        api = PhoneAgentAPI()
        print("✅ API 初始化成功")
        print(f"   - Model: {api.model_config.model_name}")
        print(f"   - Base URL: {api.model_config.base_url}")
        print(f"   - Max Steps: {api.agent_config.max_steps}")
        return True, api
    except Exception as e:
        print(f"❌ API 初始化失败：{e}")
        return False, None


def test_data_classes():
    """测试数据类"""
    print("\n测试 3: 测试数据类...")
    try:
        from main import TaskResult, BatchTaskResult
        
        # 创建 TaskResult 实例
        task_result = TaskResult(
            success=True,
            answer="Test answer",
            steps=5
        )
        print(f"✅ TaskResult 创建成功：{task_result}")
        
        # 创建 BatchTaskResult 实例
        batch_result = BatchTaskResult(
            total=10,
            success_count=8,
            failed_count=2,
            results=[task_result]
        )
        print(f"✅ BatchTaskResult 创建成功：{batch_result}")
        
        return True
    except Exception as e:
        print(f"❌ 数据类测试失败：{e}")
        return False


def test_method_signatures():
    """测试方法签名"""
    print("\n测试 4: 测试方法签名...")
    try:
        from main import PhoneAgentAPI
        import inspect
        
        api = PhoneAgentAPI()
        
        # 检查 run_task 方法
        assert hasattr(api, 'run_task'), "缺少 run_task 方法"
        sig = inspect.signature(api.run_task)
        params = list(sig.parameters.keys())
        assert 'task' in params, "run_task 缺少 task 参数"
        print(f"✅ run_task 方法签名正确：{params}")
        
        # 检查 run_batch_from_file 方法
        assert hasattr(api, 'run_batch_from_file'), "缺少 run_batch_from_file 方法"
        sig = inspect.signature(api.run_batch_from_file)
        params = list(sig.parameters.keys())
        assert 'file_path' in params, "run_batch_from_file 缺少 file_path 参数"
        assert 'task_template' in params, "run_batch_from_file 缺少 task_template 参数"
        print(f"✅ run_batch_from_file 方法签名正确：{params}")
        
        # 检查 run_batch_from_list 方法
        assert hasattr(api, 'run_batch_from_list'), "缺少 run_batch_from_list 方法"
        sig = inspect.signature(api.run_batch_from_list)
        params = list(sig.parameters.keys())
        assert 'questions' in params, "run_batch_from_list 缺少 questions 参数"
        assert 'task_template' in params, "run_batch_from_list 缺少 task_template 参数"
        print(f"✅ run_batch_from_list 方法签名正确：{params}")
        
        return True
    except Exception as e:
        print(f"❌ 方法签名测试失败：{e}")
        return False


def test_config_loading():
    """测试配置加载"""
    print("\n测试 5: 测试配置加载...")
    try:
        from main import PhoneAgentAPI
        import json
        
        # 测试从默认配置文件加载
        api = PhoneAgentAPI(config_path="config.json")
        
        # 验证配置已加载
        assert api.model_config is not None, "ModelConfig 未加载"
        assert api.agent_config is not None, "AgentConfig 未加载"
        
        print(f"✅ 配置加载成功")
        print(f"   - Provider: {api.model_config.provider}")
        print(f"   - Lang: {api.agent_config.lang}")
        
        return True
    except Exception as e:
        print(f"❌ 配置加载失败：{e}")
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Phone Agent API 测试")
    print("=" * 60)
    
    tests = [
        ("导入测试", test_import),
        ("API 初始化", test_api_init),
        ("数据类", test_data_classes),
        ("方法签名", test_method_signatures),
        ("配置加载", test_config_loading),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            if isinstance(result, tuple):
                results.append((name, result[0]))
            else:
                results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name}测试异常：{e}")
            results.append((name, False))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    print(f"\n总计：{passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！API 可以正常使用。")
    else:
        print("\n⚠️  部分测试失败，请检查配置和依赖。")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
