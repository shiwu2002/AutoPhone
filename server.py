#!/usr/bin/env python3
"""
HTTP 服务器接口，用于通过 API 调用 PhoneAgent。
"""

import json
import os
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS

from phone_agent import PhoneAgent
from phone_agent.agent import AgentConfig
from phone_agent.history import get_history_manager
from phone_agent.model import ModelConfig


app = Flask(__name__, static_folder='templates', static_url_path='')
# 启用 CORS 支持跨域请求
CORS(app)

# 配置文件路径
CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config() -> dict:
    """从配置文件加载配置。"""
    if not CONFIG_PATH.exists():
        return {}
    
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点。"""
    return jsonify({
        'status': 'healthy',
        'message': 'Server is running'
    })


@app.route('/', methods=['GET'])
def index():
    """返回主页。"""
    from flask import send_from_directory
    return send_from_directory('templates', 'index.html')


@app.route('/devices', methods=['GET'])
def get_devices():
    """获取已连接的设备列表。"""
    try:
        from phone_agent.device_factory import get_device_factory
        device_factory = get_device_factory()
        devices = device_factory.list_devices()
        
        return jsonify({
            'success': True,
            'count': len(devices),
            'devices': [
                {
                    'device_id': d.device_id,
                    'status': d.status,
                    'connection_type': d.connection_type.value,
                    'model': d.model or 'Unknown'
                }
                for d in devices
            ]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/devices/connect', methods=['POST'])
def connect_device():
    """连接到远程设备。"""
    try:
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': 'Request must be JSON'
            }), 400
        
        data = request.get_json()
        address = data.get('address', '')
        
        if not address:
            return jsonify({
                'success': False,
                'error': 'Missing device address'
            }), 400
        
        from phone_agent.adb.connection import ADBConnection
        conn = ADBConnection()
        success, message = conn.connect(address)
        
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/devices/disconnect', methods=['POST'])
def disconnect_device():
    """断开远程设备。"""
    try:
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': 'Request must be JSON'
            }), 400
        
        data = request.get_json()
        address = data.get('address', 'all')
        
        from phone_agent.adb.connection import ADBConnection
        conn = ADBConnection()
        success, message = conn.disconnect(address if address != 'all' else None)
        
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/devices/refresh', methods=['POST'])
def refresh_devices():
    """刷新设备列表。"""
    try:
        return get_devices()
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/execute', methods=['POST'])
def execute_task():
    """
    执行任务的端点。
    
    请求体 (JSON):
    {
        "task": "要执行的任务描述",
        "model": {  # 可选，覆盖配置文件中的模型配置
            "base_url": "http://localhost:8000/v1",
            "model_name": "autoglm-phone-9b",
            "api_key": "EMPTY"
        },
        "agent": {  # 可选，覆盖配置文件中的代理配置
            "max_steps": 100,
            "device_id": null,
            "lang": "cn",
            "verbose": true
        }
    }
    
    响应 (JSON):
    {
        "success": true,
        "result": "任务执行结果",
        "steps": 10,
        "message": "成功消息"
    }
    """
    try:
        # 检查请求体
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': 'Request must be JSON'
            }), 400
        
        data = request.get_json()
        
        if not data or 'task' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: task'
            }), 400
        
        task = data['task']
        
        # 加载配置文件
        config = load_config()
        
        # 使用配置文件中的默认值，允许请求覆盖
        model_config_data = data.get('model', config.get('model', {}))
        agent_config_data = data.get('agent', config.get('agent', {}))
        
        # 创建模型配置
        model_config = ModelConfig(
            base_url=model_config_data.get('base_url', 'http://localhost:8000/v1'),
            model_name=model_config_data.get('model_name', 'autoglm-phone-9b'),
            api_key=model_config_data.get('api_key', 'EMPTY'),
            lang=agent_config_data.get('lang', 'cn')
        )
        
        # 创建代理配置
        agent_config = AgentConfig(
            max_steps=int(agent_config_data.get('max_steps', 100)),
            device_id=agent_config_data.get('device_id'),
            lang=agent_config_data.get('lang', 'cn'),
            verbose=bool(agent_config_data.get('verbose', True))
        )
        
        # 检查是否有可用设备
        from phone_agent.device_factory import get_device_factory
        device_factory = get_device_factory()
        devices = device_factory.list_devices()
        if not devices:
            return jsonify({
                'success': False,
                'error': '没有可用的设备',
                'message': '请先连接 ADB 设备（USB 或无线），刷新页面后重试'
            }), 400
        
        # 创建并运行代理
        agent = PhoneAgent(
            model_config=model_config,
            agent_config=agent_config
        )
        
        # 执行任务
        result = agent.run(task)
        
        # 返回成功响应
        return jsonify({
            'success': True,
            'result': result,
            'steps': agent.step_count,
            'message': 'Task executed successfully'
        })
        
    except Exception as e:
        # 返回错误响应
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Task execution failed'
        }), 500


@app.route('/run', methods=['POST'])
def run_simple():
    """
    简化版的任务执行端点，仅需要任务描述。
    所有配置从 config.json 自动读取。
    
    请求体 (JSON):
    {
        "task": "要执行的任务描述"
    }
    
    响应 (JSON):
    {
        "success": true,
        "result": "任务执行结果",
        "steps": 10
    }
    """
    try:
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': 'Request must be JSON'
            }), 400
        
        data = request.get_json()
        
        if not data or 'task' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: task'
            }), 400
        
        task = data['task']
        
        # 加载配置文件
        config = load_config()
        
        # 从配置中读取模型和代理配置
        model_config_data = config.get('model', {})
        agent_config_data = config.get('agent', {})
        
        # 创建模型配置
        model_config = ModelConfig(
            base_url=model_config_data.get('base_url', 'http://localhost:8000/v1'),
            model_name=model_config_data.get('model_name', 'autoglm-phone-9b'),
            api_key=model_config_data.get('api_key', 'EMPTY'),
            lang=agent_config_data.get('lang', 'cn')
        )
        
        # 创建代理配置
        agent_config = AgentConfig(
            max_steps=int(agent_config_data.get('max_steps', 100)),
            device_id=agent_config_data.get('device_id'),
            lang=agent_config_data.get('lang', 'cn'),
            verbose=bool(agent_config_data.get('verbose', True))
        )
        
        # 检查是否有可用设备
        from phone_agent.device_factory import get_device_factory
        device_factory = get_device_factory()
        devices = device_factory.list_devices()
        if not devices:
            return jsonify({
                'success': False,
                'error': '没有可用的设备',
                'message': '请先连接 ADB 设备（USB 或无线），刷新页面后重试'
            }), 400
        
        # 创建并运行代理
        agent = PhoneAgent(
            model_config=model_config,
            agent_config=agent_config
        )
        
        # 执行任务
        result = agent.run(task)
        
        # 返回成功响应
        return jsonify({
            'success': True,
            'result': result,
            'steps': agent.step_count
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/config', methods=['GET'])
def get_config():
    """获取当前配置。"""
    config = load_config()
    return jsonify(config)


@app.route('/config', methods=['POST'])
def update_config():
    """更新配置文件。"""
    try:
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': 'Request must be JSON'
            }), 400
        
        new_config = request.get_json()
        
        # 保存配置到文件
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(new_config, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            'success': True,
            'message': 'Configuration updated'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/history', methods=['GET'])
def get_history():
    """获取任务历史记录。"""
    try:
        limit = request.args.get('limit', 100, type=int)
        success_filter = request.args.get('success', type=str)
        
        history_mgr = get_history_manager()
        
        if success_filter == 'true':
            records = history_mgr.get_successful_records(limit=limit)
        elif success_filter == 'false':
            records = history_mgr.get_failed_records(limit=limit)
        else:
            records = history_mgr.get_all_records(limit=limit)
        
        return jsonify({
            'success': True,
            'count': len(records),
            'records': [record.to_dict() for record in records]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/history/clear', methods=['POST'])
def clear_history():
    """清空所有历史记录。"""
    try:
        history_mgr = get_history_manager()
        success = history_mgr.clear_all()
        
        if success:
            return jsonify({
                'success': True,
                'message': '所有历史记录已清空'
            })
        else:
            return jsonify({
                'success': False,
                'error': '清空历史记录失败'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/history/stats', methods=['GET'])
def get_history_stats():
    """获取历史统计信息。"""
    try:
        history_mgr = get_history_manager()
        stats = history_mgr.get_statistics()
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/history/search', methods=['GET'])
def search_history():
    """搜索历史记录。"""
    try:
        keyword = request.args.get('keyword', '')
        limit = request.args.get('limit', 50, type=int)
        
        if not keyword:
            return jsonify({
                'success': False,
                'error': 'Missing required parameter: keyword'
            }), 400
        
        history_mgr = get_history_manager()
        records = history_mgr.search_records(keyword, limit=limit)
        
        return jsonify({
            'success': True,
            'count': len(records),
            'records': [record.to_dict() for record in records]
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# 导入 excel_task 模块中的函数
from excel_task import process_excel_questions


@app.route('/upload', methods=['POST'])
def upload_file():
    """
    上传文件端点，支持拖放上传 Excel/TXT 文件

    响应 (JSON):
    {
        "success": true,
        "file_path": "保存的文件路径",
        "filename": "原始文件名"
    }
    """
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': '没有文件上传'
            }), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({
                'success': False,
                'error': '文件名为空'
            }), 400

        # 检查文件扩展名
        allowed_extensions = {'xlsx', 'xls', 'txt'}
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''

        if ext not in allowed_extensions:
            return jsonify({
                'success': False,
                'error': f'不支持的文件格式：.{ext}，请上传 .xlsx, .xls 或 .txt 文件'
            }), 400

        # 保存到 uploads 目录
        from pathlib import Path
        import uuid

        upload_dir = Path(__file__).parent / 'uploads'
        upload_dir.mkdir(exist_ok=True)

        # 生成唯一的文件名
        original_name = file.filename
        safe_name = f"{uuid.uuid4().hex}_{original_name}"
        file_path = upload_dir / safe_name

        file.save(str(file_path))

        return jsonify({
            'success': True,
            'file_path': str(file_path),
            'filename': original_name
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/excel/batch', methods=['POST'])
def excel_batch_task():
    """
    Excel 批量任务执行端点

    请求体 (JSON):
    {
        "file": "Excel 文件路径",
        "task": "任务模板，可以使用 {content} 占位符",
        "column": "问题列名（可选）",
        "output": "输出文件路径（可选）",
        "save_screenshots": "是否保存截图（可选，默认 false）",
        "embed_screenshot": "是否嵌入截图（可选，默认 false）",
        "max_questions": "最大问题数（可选，0=全部）"
    }

    响应 (JSON):
    {
        "success": true,
        "results": [
            {"question": "...", "answer": "...", "success": true, ...}
        ],
        "output_file": "输出文件路径",
        "statistics": {"total": 4, "success": 3, "failed": 1}
    }
    """
    try:
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': 'Request must be JSON'
            }), 400

        data = request.get_json()

        if not data or 'file' not in data or 'task' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: file or task'
            }), 400

        # 加载配置
        config = load_config()
        model_config_data = config.get('model', {})
        agent_config_data = config.get('agent', {})

        # 创建配置
        model_cfg = ModelConfig(
            base_url=model_config_data.get('base_url', 'http://localhost:11434/v1'),
            model_name=model_config_data.get('model_name', 'qwen3.5:4b'),
            api_key=model_config_data.get('api_key', 'ollama'),
            use_thinking=model_config_data.get('use_thinking', False),
            lang=agent_config_data.get('lang', 'cn')
        )

        agent_cfg = AgentConfig(
            max_steps=agent_config_data.get('max_steps', 50),
            verbose=agent_config_data.get('verbose', True),
            lang=agent_config_data.get('lang', 'cn')
        )

        # 确定输出文件（默认覆盖原文件）
        from pathlib import Path
        output_file = data.get('output')
        if not output_file:
            # 默认直接覆盖原文件
            output_file = data['file']

        # 执行批量任务
        results = process_excel_questions(
            excel_path=data['file'],
            task_template=data['task'],
            output_path=output_file,
            model_cfg=model_cfg,
            agent_cfg=agent_cfg,
            embed_screenshot=data.get('embed_screenshot', False),
            column=data.get('column')
        )

        # 统计
        success_count = sum(1 for r in results if r.get('success', False))

        return jsonify({
            'success': True,
            'results': results,
            'output_file': output_file,
            'statistics': {
                'total': len(results),
                'success': success_count,
                'failed': len(results) - success_count
            }
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/excel/preview', methods=['POST'])
def excel_preview():
    """
    预览 Excel 文件内容

    请求体 (JSON):
    {
        "file": "Excel 文件路径",
        "column": "列名（可选）"
    }

    响应 (JSON):
    {
        "success": true,
        "columns": ["问题", "答案", "状态"],
        "questions": ["问题 1", "问题 2", ...],
        "count": 10
    }
    """
    try:
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': 'Request must be JSON'
            }), 400

        data = request.get_json()

        if not data or 'file' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: file'
            }), 400

        if not PANDAS_AVAILABLE:
            return jsonify({
                'success': False,
                'error': 'pandas not installed'
            }), 400

        import pandas as pd
        from pathlib import Path

        path = Path(data['file'])
        if not path.exists():
            return jsonify({
                'success': False,
                'error': f'File not found: {data["file"]}'
            }), 400

        # 读取 Excel
        df = pd.read_excel(path)
        columns = df.columns.tolist()

        # 查找问题列
        question_col = data.get('column')
        if not question_col:
            for col in columns:
                if '问题' in col.lower() or 'question' in col.lower():
                    question_col = col
                    break
            if not question_col:
                question_col = columns[0]

        # 获取问题列表
        questions = df[question_col].dropna().astype(str).tolist()
        questions = [q.strip() for q in questions if q.strip() and q != 'nan']

        return jsonify({
            'success': True,
            'columns': columns,
            'question_column': question_col,
            'questions': questions,
            'count': len(questions)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    print("=" * 50)
    print("Phone Agent HTTP Server")
    print("=" * 50)
    print("Starting server on http://localhost:5001")
    print("\nAvailable endpoints:")
    print("  GET  /health      - Health check")
    print("  POST /run         - Simple task execution (uses config.json)")
    print("  POST /execute     - Advanced task execution (can override config)")
    print("  POST /upload      - File upload (drag & drop support)")
    print("  POST /excel/batch - Excel batch task execution")
    print("  POST /excel/preview - Preview Excel file content")
    print("  GET  /config      - Get current configuration")
    print("  POST /config      - Update configuration")
    print("  GET  /history     - Get task history")
    print("  GET  /history/stats - Get statistics")
    print("  GET  /history/search - Search history")
    print("=" * 50)

    # 启动 Flask 服务器
    app.run(host='0.0.0.0', port=5001, debug=False)
