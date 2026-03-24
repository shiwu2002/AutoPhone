#!/usr/bin/env python3
"""
HTTP 服务器接口 - 安全增强版
"""

import os
import uuid
import tempfile
import shutil
from pathlib import Path
from functools import wraps
from flask import Flask, request, jsonify, g
from flask_cors import CORS

from phone_agent import PhoneAgent
from phone_agent.agent import AgentConfig
from phone_agent.history import get_history_manager
from phone_agent.model import ModelConfig
from phone_agent.device_factory import get_device_factory
from phone_agent.config.manager import get_config_manager

# ============== 安全配置 ==============

# 最大上传文件大小：100MB
MAX_UPLOAD_SIZE = 100 * 1024 * 1024

# 允许的上传扩展名
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'txt'}

# 上传文件目录（使用系统临时目录）
UPLOAD_DIR = Path(tempfile.gettempdir()) / 'autophone_uploads'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 配置文件路径
CONFIG_PATH = Path(__file__).parent / "config.json"

# ============== Flask 应用初始化 ==============

app = Flask(__name__, static_folder='templates', static_url_path='')

# 配置最大上传大小
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_SIZE

# CORS 配置 - 可从配置读取
config_manager = get_config_manager()
server_config = config_manager.server

if server_config.enable_cors:
    CORS(app)


# ============== 认证中间件 ==============

def check_auth():
    """检查请求是否通过认证。"""
    if not server_config.auth_enabled:
        return True

    # 从 Header 获取 token
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
    else:
        token = auth_header

    # 优先使用环境变量 token，其次使用配置文件
    env_token = os.environ.get('AUTOPHONE_SERVER_TOKEN')
    valid_token = env_token or server_config.auth_token

    return token == valid_token if valid_token else False


def require_auth(f):
    """需要认证的路由装饰器。"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not check_auth():
            return jsonify({'success': False, 'error': '认证失败，请提供有效的 Authorization header'}), 401
        return f(*args, **kwargs)
    return decorated_function


# ============== 安全工具函数 ==============

def allowed_file(filename: str) -> bool:
    """检查文件扩展名是否允许。"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_safe_filename(original_filename: str) -> str:
    """生成安全的文件名，防止路径遍历攻击。"""
    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'tmp'
    return f"{uuid.uuid4().hex}.{ext}"


def cleanup_old_files(max_age_hours: int = 24) -> int:
    """清理超过指定时间的上传文件。"""
    import time
    current_time = time.time()
    cleaned = 0

    if not UPLOAD_DIR.exists():
        return 0

    for file_path in UPLOAD_DIR.iterdir():
        if file_path.is_file():
            file_age = current_time - file_path.stat().st_mtime
            if file_age > max_age_hours * 3600:
                try:
                    file_path.unlink()
                    cleaned += 1
                except OSError:
                    pass

    return cleaned


# ============== 路由处理器 ==============

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点（无需认证）。"""
    return jsonify({'status': 'healthy', 'message': 'Server is running'})


@app.route('/', methods=['GET'])
def index():
    """返回主页。"""
    from flask import send_from_directory
    return send_from_directory('templates', 'index.html')


@app.route('/devices', methods=['GET'])
@require_auth
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
@require_auth
def connect_device():
    """连接到远程设备。"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Request must be JSON'}), 400
        address = request.get_json().get('address', '')
        if not address:
            return jsonify({'success': False, 'error': 'Missing device address'}), 400

        # 验证地址格式
        if ':' not in address and '.' not in address:
            return jsonify({'success': False, 'error': 'Invalid address format'}), 400

        from phone_agent.adb.connection import ADBConnection
        conn = ADBConnection()
        success, message = conn.connect(address)
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/devices/disconnect', methods=['POST'])
@require_auth
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
@require_auth
def refresh_devices():
    """刷新设备列表。"""
    try:
        return get_devices()
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def build_model_config_from_manager(override: dict = None) -> ModelConfig:
    """使用 ConfigManager 构建模型配置。"""
    creds = config_manager.get_model_credentials()
    provider = config_manager.get("model", "provider", default="local")

    if override:
        if "base_url" in override:
            creds["base_url"] = override["base_url"]
        if "model" in override:
            creds["model"] = override["model"]
        if "api_key" in override:
            creds["api_key"] = override["api_key"]

    return ModelConfig(
        base_url=creds["base_url"],
        model_name=creds["model"],
        api_key=creds["api_key"] or "EMPTY",
        use_thinking=config_manager.get("model", "use_thinking", default=False),
        lang=config_manager.get("agent", "lang", default="cn"),
        provider=provider,
    )


def build_agent_config_from_manager(override: dict = None) -> AgentConfig:
    """使用 ConfigManager 构建 Agent 配置。"""
    return AgentConfig(
        max_steps=int(config_manager.get("agent", "max_steps", default=0)),
        device_id=config_manager.get("agent", "device_id"),
        lang=config_manager.get("agent", "lang", default="cn"),
        verbose=bool(config_manager.get("agent", "verbose", default=True)),
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


@app.route('/execute', methods=['POST'])
@require_auth
def execute_task():
    """执行任务（高级版，可覆盖配置）。"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Request must be JSON'}), 400
        data = request.get_json()
        if not data or 'task' not in data:
            return jsonify({'success': False, 'error': 'Missing required field: task'}), 400

        model_config = build_model_config_from_manager(data.get('model'))
        agent_config = build_agent_config_from_manager(data.get('agent'))

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
@require_auth
def run_simple():
    """执行任务（简化版，使用 config.json 配置）。"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Request must be JSON'}), 400
        data = request.get_json()
        if not data or 'task' not in data:
            return jsonify({'success': False, 'error': 'Missing required field: task'}), 400

        model_config = build_model_config_from_manager()
        agent_config = build_agent_config_from_manager()

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
@require_auth
def get_config():
    """获取当前配置（不包含敏感信息）。"""
    config = config_manager._raw_config.copy()

    # 隐藏敏感信息
    if 'model' in config and 'providers' in config['model']:
        for provider in config['model']['providers'].values():
            if 'api_key' in provider and provider['api_key']:
                provider['api_key'] = '***hidden***'

    return jsonify(config)


@app.route('/config', methods=['POST'])
@require_auth
def update_config():
    """更新配置文件（不允许通过 API 更新敏感信息）。"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Request must be JSON'}), 400

        new_config = request.get_json()

        # 不允许通过 API 设置敏感信息
        if 'model' in new_config and 'providers' in new_config['model']:
            for provider in new_config['model']['providers'].values():
                if 'api_key' in provider:
                    del provider['api_key']

        config_manager._raw_config.update(new_config)
        config_manager.save()

        return jsonify({'success': True, 'message': 'Configuration updated (sensitive fields excluded)'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/history', methods=['GET'])
@require_auth
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
@require_auth
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
@require_auth
def get_history_stats():
    """获取历史统计信息。"""
    try:
        history_mgr = get_history_manager()
        return jsonify({'success': True, 'statistics': history_mgr.get_statistics()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/history/search', methods=['GET'])
@require_auth
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


# ============== Excel 批量任务 ==============

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


@app.route('/upload', methods=['POST'])
@require_auth
def upload_file():
    """上传文件端点，支持拖放上传 Excel/TXT 文件。"""
    try:
        # 清理旧文件
        cleanup_old_files()

        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '没有文件上传'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': '文件名为空'}), 400

        if not allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'unknown'
            return jsonify({
                'success': False,
                'error': f'不支持的文件格式：.{ext}，请上传 {", ".join(ALLOWED_EXTENSIONS)} 文件'
            }), 400

        # 生成安全文件名
        safe_filename = generate_safe_filename(file.filename)
        file_path = UPLOAD_DIR / safe_filename

        # 保存文件
        file.save(str(file_path))

        return jsonify({
            'success': True,
            'file_path': str(file_path),
            'filename': file.filename,
            '_expires_hint': '文件将在 24 小时后自动清理'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/excel/batch', methods=['POST'])
@require_auth
def excel_batch_task():
    """Excel 批量任务执行端点。"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Request must be JSON'}), 400
        data = request.get_json()
        if not data or 'file' not in data or 'task' not in data:
            return jsonify({'success': False, 'error': 'Missing required fields: file or task'}), 400

        model_cfg = build_model_config_from_manager()
        agent_cfg = build_agent_config_from_manager()

        output_file = data.get('output') or data['file']

        from bin.excel_task import process_excel_questions
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
@require_auth
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


# ============== 错误处理 ==============

@app.errorhandler(413)
def too_large(e):
    """处理文件过大错误。"""
    return jsonify({'success': False, 'error': f'文件过大，最大允许 {MAX_UPLOAD_SIZE // 1024 // 1024}MB'}), 413


@app.errorhandler(500)
def internal_error(e):
    """处理内部错误。"""
    return jsonify({'success': False, 'error': '服务器内部错误'}), 500


# ============== 主程序 ==============

if __name__ == '__main__':
    print("=" * 50)
    print("Phone Agent HTTP Server (安全增强版)")
    print("=" * 50)
    print(f"Starting server on http://{server_config.host}:{server_config.port}")

    if server_config.auth_enabled:
        print("⚠️  认证已启用，请使用 Authorization header 发送请求")
    else:
        print("⚠️  认证未启用，生产环境建议开启")

    print("\nAvailable endpoints:")
    print("  GET  /health           - Health check")
    print("  POST /run              - Simple task execution")
    print("  POST /execute          - Advanced task execution")
    print("  POST /upload           - File upload (max 100MB, auto-cleanup)")
    print("  POST /excel/batch      - Excel batch execution")
    print("  POST /excel/preview    - Preview Excel content")
    print("  GET  /config           - Get configuration")
    print("  POST /config           - Update configuration")
    print("  GET  /history          - Get task history")
    print("  GET  /history/stats    - Get statistics")
    print("  GET  /history/search   - Search history")
    print("=" * 50)

    app.run(host=server_config.host, port=server_config.port, debug=False)
