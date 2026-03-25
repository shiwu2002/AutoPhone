#!/usr/bin/env python3
"""
HTTP 服务器接口 - 对接 MasterAgent（主智能体）
"""

import os
import uuid
import tempfile
import shutil
from pathlib import Path
from functools import wraps
from typing import Optional
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

from mainAgent.agent import MasterAgent, MasterAgentConfig
from mainAgent.skills import list_skills, get_skill_info
from mainAgent.skill_config import get_manager as get_skill_config_manager
from mainAgent.skill_template import create_skill, validate_skill, get_examples
from phone_agent.utils.logger import setup_logger
from phone_agent.history import get_history_manager

logger = setup_logger(__name__)

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

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_SIZE

# CORS 配置
app.config['CORS_ENABLED'] = True
CORS(app)

# ============== 认证配置 ==============

AUTH_ENABLED = False
AUTH_TOKEN = os.environ.get('AUTOPHONE_SERVER_TOKEN', 'admin')


def check_auth():
    """检查请求是否通过认证。"""
    if not AUTH_ENABLED:
        return True
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
    else:
        token = auth_header
    return token == AUTH_TOKEN


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

# 全局 MasterAgent 实例
_agent_instance: Optional[MasterAgent] = None


def get_agent() -> MasterAgent:
    """获取全局 MasterAgent 实例。"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = MasterAgent()
    return _agent_instance


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点。"""
    return jsonify({'status': 'healthy', 'message': 'Server is running'})


@app.route('/chat', methods=['POST'])
def chat():
    """与 MasterAgent 聊天。"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Request must be JSON'}), 400
        data = request.get_json()

        message = data.get('message', '')
        file_path = data.get('file', '')

        if not message:
            return jsonify({'success': False, 'error': 'Missing required field: message'}), 400

        # 获取 Agent 实例
        agent = get_agent()

        # 如果有文件，更新工作文件
        if file_path:
            agent._working_files.append(file_path)

        # 聊天
        reply = agent.chat(message)

        return jsonify({
            'success': True,
            'reply': reply,
            'status': agent.get_status()
        })

    except Exception as e:
        logger.error(f"Chat failed: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/execute', methods=['POST'])
@require_auth
def execute_task():
    """执行任务（使用 MasterAgent）。"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Request must be JSON'}), 400
        data = request.get_json()
        if not data or 'task' not in data:
            return jsonify({'success': False, 'error': 'Missing required field: task'}), 400

        # 创建 MasterAgent 并执行任务
        agent = MasterAgent()
        result = agent.execute_task(data['task'])

        return jsonify({
            'success': True,
            'result': result,
            'message': 'Task executed successfully'
        })
    except Exception as e:
        logger.error(f"Task execution failed: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/history', methods=['GET'])
@require_auth
def get_history():
    """获取任务历史记录。"""
    try:
        limit = request.args.get('limit', 100, type=int)
        history_mgr = get_history_manager()
        records = history_mgr.get_all_records(limit=limit)
        return jsonify({
            'success': True,
            'count': len(records),
            'records': [record.to_dict() for record in records]
        })
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
        safe_filename = generate_safe_filename(file.filename)
        file_path = UPLOAD_DIR / safe_filename
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
    """Excel 批量任务执行端点（使用 MasterAgent）。"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Request must be JSON'}), 400
        data = request.get_json()
        if not data or 'file' not in data or 'task' not in data:
            return jsonify({'success': False, 'error': 'Missing required fields: file or task'}), 400

        # 创建 MasterAgent 并执行 Excel 批量任务
        agent = MasterAgent()
        task_desc = f'处理 {data["file"]} 中的所有问题，任务模板：{data["task"]}'
        result = agent.execute_task(task_desc)

        return jsonify({
            'success': True,
            'result': result,
            'output_file': data.get('file'),
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


@app.route('/download', methods=['GET'])
@require_auth
def download_file():
    """下载文件端点。"""
    try:
        file_path = request.args.get('file', '')
        if not file_path:
            return jsonify({'success': False, 'error': '缺少文件路径参数'}), 400
        path = Path(file_path)
        if not path.exists():
            return jsonify({'success': False, 'error': '文件不存在'}), 404
        if not path.is_file():
            return jsonify({'success': False, 'error': '不是有效文件'}), 400
        return send_file(
            path,
            as_attachment=True,
            download_name=path.name,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' if path.suffix == '.xlsx' else 'application/octet-stream'
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============== Skills 管理 ==============

@app.route('/skills', methods=['GET'])
@require_auth
def list_all_skills():
    """列出所有 Skills。"""
    try:
        skills = list_skills()
        return jsonify({'success': True, 'skills': skills})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/skills/<skill_id>', methods=['GET'])
@require_auth
def get_skill_detail(skill_id: str):
    """获取 Skill 详细信息。"""
    try:
        info = get_skill_info(skill_id)
        if info:
            return jsonify({'success': True, 'skill': info})
        return jsonify({'success': False, 'error': f'Skill not found: {skill_id}'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/skills/<skill_id>/config', methods=['POST'])
@require_auth
def update_skill_config(skill_id: str):
    """更新 Skill 配置。"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Request must be JSON'}), 400
        data = request.get_json()

        manager = get_skill_config_manager()
        if manager.update_user_config(skill_id, data):
            return jsonify({'success': True, 'message': '配置已更新'})
        return jsonify({'success': False, 'error': '更新失败，Skill 可能不存在或配置验证失败'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/skills/<skill_id>/toggle', methods=['POST'])
@require_auth
def toggle_skill(skill_id: str):
    """启用/禁用 Skill。"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Request must be JSON'}), 400
        data = request.get_json()
        enabled = data.get('enabled', True)

        manager = get_skill_config_manager()
        if enabled:
            success = manager.enable_skill(skill_id)
        else:
            success = manager.disable_skill(skill_id)

        if success:
            return jsonify({'success': True, 'message': f'Skill 已{"启用" if enabled else "禁用"}'})
        return jsonify({'success': False, 'error': '操作失败'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============== Skill 模板和创建 ==============

@app.route('/skills/templates', methods=['GET'])
@require_auth
def get_skill_templates():
    """获取 Skill 模板示例。"""
    try:
        examples = get_examples()
        return jsonify({'success': True, 'templates': examples})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/skills/create', methods=['POST'])
@require_auth
def create_new_skill():
    """创建新的 Skill。"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Request must be JSON'}), 400
        data = request.get_json()

        # 必填字段
        required_fields = ['skill_id', 'name', 'description', 'purpose', 'parameters']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'缺少必填字段：{field}'}), 400

        # 验证 skill_id 格式
        skill_id = data['skill_id']
        if not skill_id.replace('_', '').isalnum():
            return jsonify({'success': False, 'error': 'skill_id 只能包含字母、数字和下划线'}), 400

        # 创建 Skill
        result = create_skill(
            skill_id=skill_id,
            skill_name=data['name'],
            skill_description=data['description'],
            skill_purpose=data['purpose'],
            parameters=data['parameters'],
            config_schema=data.get('config_schema'),
            user_config=data.get('user_config'),
        )

        if result.get('success'):
            return jsonify({
                'success': True,
                'message': result.get('message'),
                'skill_id': skill_id,
                'skill_dir': result.get('skill_dir'),
            }), 201
        else:
            return jsonify({'success': False, 'error': result.get('error')}), 400

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/skills/<skill_id>/validate', methods=['GET'])
@require_auth
def validate_skill_endpoint(skill_id: str):
    """验证 Skill 是否有效。"""
    try:
        result = validate_skill(skill_id)
        return jsonify({
            'success': True,
            'valid': result.get('valid', False),
            'errors': result.get('errors', []),
            'warnings': result.get('warnings', [])
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
    import subprocess
    import sys
    import time
    from pathlib import Path

    print("=" * 50)
    print("Phone Agent HTTP Server (对接 MasterAgent)")
    print("=" * 50)

    host = os.environ.get('AUTOPHONE_HOST', 'localhost')
    port = int(os.environ.get('AUTOPHONE_PORT', 5001))

    print(f"Starting server on http://{host}:{port}")
    print("\nAvailable endpoints:")
    print("  GET  /health           - Health check")
    print("  POST /execute          - Execute task (MasterAgent)")
    print("  POST /upload           - File upload")
    print("  POST /excel/batch      - Excel batch execution")
    print("  POST /excel/preview    - Preview Excel content")
    print("  GET  /download         - Download file")
    print("  GET  /history          - Get task history")
    print("  GET  /history/stats    - Get statistics")
    print("  POST /history/clear    - Clear history")
    print("=" * 50)

    # 启动服务器
    import threading

    def run_server():
        app.run(host=host, port=port, debug=False, use_reloader=False)

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    time.sleep(2)

    # 启动 GUI 界面
    print("正在启动 GUI 界面...")
    gui_script = Path(__file__).parent / "gui_app.py"
    if gui_script.exists():
        subprocess.Popen([sys.executable, str(gui_script)])

    # 保持主线程运行
    while True:
        time.sleep(1)
