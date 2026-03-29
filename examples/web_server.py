#!/usr/bin/env python3
"""
Web 服务集成示例 - Flask REST API

展示如何将 Phone Agent 封装为 Web 服务。
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import PhoneAgentAPI, TaskResult, BatchTaskResult

app = Flask(__name__)
CORS(app)  # 启用跨域支持

# 全局 API 实例
api = None


def init_api():
    """初始化 Phone Agent API"""
    global api
    if api is None:
        api = PhoneAgentAPI()
    return api


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'ok',
        'message': 'Phone Agent API is running'
    })


@app.route('/api/task', methods=['POST'])
def run_single_task():
    """
    执行单个任务
    
    Request JSON:
    {
        "task": "打开微信",
        "save_screenshot": false,
        "verbose": true
    }
    
    Response JSON:
    {
        "success": true,
        "answer": "任务完成",
        "error": null,
        "steps": 5,
        "screenshot_base64": null
    }
    """
    try:
        data = request.json
        if not data or 'task' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing task parameter'
            }), 400
        
        task = data.get('task')
        save_screenshot = data.get('save_screenshot', False)
        verbose = data.get('verbose', False)
        
        api = init_api()
        result = api.run_task(
            task=task,
            save_screenshot=save_screenshot,
            verbose=verbose
        )
        
        return jsonify({
            'success': result.success,
            'answer': result.answer,
            'error': result.error,
            'steps': result.steps,
            'screenshot_base64': result.screenshot_base64
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/batch/file', methods=['POST'])
def run_batch_from_file():
    """
    从文件批量执行任务
    
    Request JSON:
    {
        "file_path": "questions.xlsx",
        "task_template": "请回答：{content}",
        "output_path": "results.xlsx",
        "column": "问题",
        "embed_screenshot": false,
        "compare_answer": false,
        "max_questions": 10,
        "verbose": false
    }
    
    Response JSON:
    {
        "total": 10,
        "success_count": 8,
        "failed_count": 2,
        "output_file": "results.xlsx",
        "results": [
            {
                "success": true,
                "answer": "...",
                "steps": 5
            },
            ...
        ]
    }
    """
    try:
        data = request.json
        if not data or 'file_path' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing file_path parameter'
            }), 400
        
        api = init_api()
        result = api.run_batch_from_file(
            file_path=data.get('file_path'),
            task_template=data.get('task_template', '{content}'),
            output_path=data.get('output_path'),
            column=data.get('column'),
            embed_screenshot=data.get('embed_screenshot', False),
            compare_answer=data.get('compare_answer', False),
            max_questions=data.get('max_questions', 0),
            verbose=data.get('verbose', False)
        )
        
        # 序列化结果
        results_data = []
        for r in result.results:
            results_data.append({
                'success': r.success,
                'answer': r.answer,
                'error': r.error,
                'steps': r.steps
            })
        
        return jsonify({
            'total': result.total,
            'success_count': result.success_count,
            'failed_count': result.failed_count,
            'output_file': result.output_file,
            'results': results_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/batch/list', methods=['POST'])
def run_batch_from_list():
    """
    从列表批量执行任务
    
    Request JSON:
    {
        "questions": ["问题 1", "问题 2", "问题 3"],
        "task_template": "请回答：{content}",
        "output_path": "results.xlsx",
        "embed_screenshot": false,
        "max_questions": 0,
        "verbose": false
    }
    
    Response JSON:
    {
        "total": 3,
        "success_count": 2,
        "failed_count": 1,
        "results": [...]
    }
    """
    try:
        data = request.json
        if not data or 'questions' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing questions parameter'
            }), 400
        
        api = init_api()
        result = api.run_batch_from_list(
            questions=data.get('questions', []),
            task_template=data.get('task_template', '{content}'),
            output_path=data.get('output_path'),
            embed_screenshot=data.get('embed_screenshot', False),
            max_questions=data.get('max_questions', 0),
            verbose=data.get('verbose', False)
        )
        
        # 序列化结果
        results_data = []
        for r in result.results:
            results_data.append({
                'success': r.success,
                'answer': r.answer,
                'error': r.error,
                'steps': r.steps
            })
        
        return jsonify({
            'total': result.total,
            'success_count': result.success_count,
            'failed_count': result.failed_count,
            'results': results_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/status', methods=['GET'])
def get_status():
    """获取 API 状态"""
    api = init_api()
    return jsonify({
        'initialized': True,
        'model': api.model_config.model_name,
        'base_url': api.model_config.base_url,
        'max_steps': api.agent_config.max_steps,
        'lang': api.agent_config.lang
    })


def run_async_task(func, *args, **kwargs):
    """在后台线程运行任务"""
    thread = threading.Thread(target=func, args=args, kwargs=kwargs)
    thread.daemon = True
    thread.start()
    return thread


if __name__ == '__main__':
    print("=" * 60)
    print("Phone Agent Web Server")
    print("=" * 60)
    print("\n启动服务器...")
    print("API 文档：http://localhost:5000/health")
    print("单个任务：POST http://localhost:5000/api/task")
    print("批量任务 (文件): POST http://localhost:5000/api/batch/file")
    print("批量任务 (列表): POST http://localhost:5000/api/batch/list")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=False)
