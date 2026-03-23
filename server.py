#!/usr/bin/env python3
"""
HTTP 服务器接口，用于通过 API 调用 PhoneAgent。
"""

import json
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS

from phone_agent import PhoneAgent
from phone_agent.agent import AgentConfig
from phone_agent.history import get_history_manager
from phone_agent.model import ModelConfig
from phone_agent.device_factory import get_device_factory

# 配置文件路径
CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config() -> dict:
    """从配置文件加载配置。"""
    if not CONFIG_PATH.exists():
        return {}
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}


def build_model_config(config: dict, override: dict = None) -> ModelConfig:
    """构建模型配置。"""
    if override:
        model_config_data = {**config.get('model', {}), **override}
        agent_config_data = {**config.get('agent', {}), **override.get('agent', {})}
    else:
        model_config_data = config.get('model', {})
        agent_config_data = config.get('agent', {})

    provider = model_config_data.get('provider', 'local')
    provider_config = model_config_data.get(provider, {})

    return ModelConfig(
        base_url=model_config_data.get('base_url') or provider_config.get('base_url', 'http://localhost:8000/v1'),
        model_name=model_config_data.get('model_name') or provider_config.get('model', 'autoglm-phone-9b'),
        api_key=model_config_data.get('api_key') or provider_config.get('api_key', 'EMPTY'),
        use_thinking=model_config_data.get('use_thinking', False),
        lang=agent_config_data.get('lang', 'cn'),
        provider=provider,
    )


def build_agent_config(config: dict, override: dict = None) -> AgentConfig:
    """构建代理配置。"""
    if override:
        agent_config_data = {**config.get('agent', {}), **override.get('agent', {})}
    else:
        agent_config_data = config.get('agent', {})

    return AgentConfig(
        max_steps=int(agent_config_data.get('max_steps', 100)),
        device_id=agent_config_data.get('device_id'),
        lang=agent_config_data.get('lang', 'cn'),
        verbose=bool(agent_config_data.get('verbose', True)),
    )


def check_device_available() -> tuple[bool, str]:
    """检查是否有可用设备。"""
    try:
        devices = get_device_factory().list_devices()
        if not devices:
            return False, '没有可用的设备，请先连接 ADB 设备（USB 或无线），刷新页面后重试'
        return True, ''
    except Exception as e:
        return False, f'检查设备失败：{str(e)}'


app = Flask(__name__, static_folder='templates', static_url_path='')
CORS(app)


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点。"""
    return jsonify({'status': 'healthy', 'message': 'Server is running'})


@app.route('/', methods=['GET'])
def index():
    """返回主页。"""
    from flask import send_from_directory
    return send_from_directory('templates', 'index.html')


@app.route('/devices', methods=['GET'])
def get_devices():
    """获取已连接的设备列表。"""
    try:
        devices = get_device_factory().list_devices()
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
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/devices/connect', methods=['POST'])
def connect_device():
    """连接到远程设备。"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Request must be JSON'}), 400
        address = request.get_json().get('address', '')
        if not address:
            return jsonify({'success': False, 'error': 'Missing device address'}), 400
        from phone_agent.adb.connection import ADBConnection
        conn = ADBConnection()
        success, message = conn.connect(address)
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/devices/disconnect', methods=['POST'])
def disconnect_device():
    """断开远程设备。"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Request must be JSON'}), 400
        address = request.get_json().get('address', 'all')
        from phone_agent.adb.connection import ADBConnection
        conn = ADBConnection()
        success, message = conn.disconnect(address if address != 'all' else None)
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/devices/refresh', methods=['POST'])
def refresh_devices():
    """刷新设备列表。"""
    try:
        return get_devices()
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/execute', methods=['POST'])
def execute_task():
    """执行任务（高级版，可覆盖配置）。"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Request must be JSON'}), 400
        data = request.get_json()
        if not data or 'task' not in data:
            return jsonify({'success': False, 'error': 'Missing required field: task'}), 400

        config = load_config()
        model_config = build_model_config(config, data.get('model'))
        agent_config = build_agent_config(config, data.get('agent'))

        success, error = check_device_available()
        if not success:
            return jsonify({'success': False, 'error': error}), 400

        agent = PhoneAgent(model_config=model_config, agent_config=agent_config)
        result = agent.run(data['task'])

        return jsonify({
            'success': True,
            'result': result,
            'steps': agent.step_count,
            'message': 'Task executed successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/run', methods=['POST'])
def run_simple():
    """执行任务（简化版，使用 config.json 配置）。"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Request must be JSON'}), 400
        data = request.get_json()
        if not data or 'task' not in data:
            return jsonify({'success': False, 'error': 'Missing required field: task'}), 400

        config = load_config()
        model_config = build_model_config(config)
        agent_config = build_agent_config(config)

        success, error = check_device_available()
        if not success:
            return jsonify({'success': False, 'error': error}), 400

        agent = PhoneAgent(model_config=model_config, agent_config=agent_config)
        result = agent.run(data['task'])

        return jsonify({
            'success': True,
            'result': result,
            'steps': agent.step_count
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/config', methods=['GET'])
def get_config():
    """获取当前配置。"""
    return jsonify(load_config())


@app.route('/config', methods=['POST'])
def update_config():
    """更新配置文件。"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Request must be JSON'}), 400
        new_config = request.get_json()
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(new_config, f, indent=2, ensure_ascii=False)
        return jsonify({'success': True, 'message': 'Configuration updated'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


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
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/history/clear', methods=['POST'])
def clear_history():
    """清空所有历史记录。"""
    try:
        history_mgr = get_history_manager()
        if history_mgr.clear_all():
            return jsonify({'success': True, 'message': '所有历史记录已清空'})
        return jsonify({'success': False, 'error': '清空历史记录失败'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/history/stats', methods=['GET'])
def get_history_stats():
    """获取历史统计信息。"""
    try:
        history_mgr = get_history_manager()
        return jsonify({'success': True, 'statistics': history_mgr.get_statistics()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/history/search', methods=['GET'])
def search_history():
    """搜索历史记录。"""
    try:
        keyword = request.args.get('keyword', '')
        limit = request.args.get('limit', 50, type=int)
        if not keyword:
            return jsonify({'success': False, 'error': 'Missing required parameter: keyword'}), 400

        history_mgr = get_history_manager()
        records = history_mgr.search_records(keyword, limit=limit)
        return jsonify({
            'success': True,
            'count': len(records),
            'records': [record.to_dict() for record in records]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# Excel 批量任务处理
from bin.excel_task import process_excel_questions

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


@app.route('/upload', methods=['POST'])
def upload_file():
    """上传文件端点，支持拖放上传 Excel/TXT 文件。"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '没有文件上传'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': '文件名为空'}), 400

        allowed_extensions = {'xlsx', 'xls', 'txt'}
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if ext not in allowed_extensions:
            return jsonify({
                'success': False,
                'error': f'不支持的文件格式：.{ext}，请上传 .xlsx, .xls 或 .txt 文件'
            }), 400

        import uuid
        upload_dir = Path(__file__).parent / 'uploads'
        upload_dir.mkdir(exist_ok=True)
        safe_name = f"{uuid.uuid4().hex}_{file.filename}"
        file_path = upload_dir / safe_name
        file.save(str(file_path))

        return jsonify({
            'success': True,
            'file_path': str(file_path),
            'filename': file.filename
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/excel/batch', methods=['POST'])
def excel_batch_task():
    """Excel 批量任务执行端点。"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Request must be JSON'}), 400
        data = request.get_json()
        if not data or 'file' not in data or 'task' not in data:
            return jsonify({'success': False, 'error': 'Missing required fields: file or task'}), 400

        config = load_config()
        model_cfg = build_model_config(config)
        agent_cfg = build_agent_config(config)

        output_file = data.get('output') or data['file']

        results = process_excel_questions(
            excel_path=data['file'],
            task_template=data['task'],
            output_path=output_file,
            model_cfg=model_cfg,
            agent_cfg=agent_cfg,
            embed_screenshot=data.get('embed_screenshot', False),
            column=data.get('column')
        )

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
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/excel/preview', methods=['POST'])
def excel_preview():
    """预览 Excel 文件内容。"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Request must be JSON'}), 400
        data = request.get_json()
        if not data or 'file' not in data:
            return jsonify({'success': False, 'error': 'Missing required field: file'}), 400

        if not PANDAS_AVAILABLE:
            return jsonify({'success': False, 'error': 'pandas not installed'}), 400

        from pathlib import Path
        path = Path(data['file'])
        if not path.exists():
            return jsonify({'success': False, 'error': f'File not found: {data["file"]}'}), 400

        df = pd.read_excel(path)
        columns = df.columns.tolist()

        question_col = data.get('column')
        if not question_col:
            for col in columns:
                if '问题' in col.lower() or 'question' in col.lower():
                    question_col = col
                    break
            if not question_col:
                question_col = columns[0]

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
        return jsonify({'success': False, 'error': str(e)}), 500


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
    app.run(host='0.0.0.0', port=5001, debug=False)
