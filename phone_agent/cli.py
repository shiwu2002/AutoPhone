"""
AutoPhone 命令行工具（基于 Typer）

子命令结构（类似 git/npm）：
- autophone run <任务描述> [--save-screenshot] [-v]
- autophone batch --input FILE [--output FILE] [--column 列名] [--template 模板] [-v]
- autophone wifi connect --ip IP [--port 5555]
- autophone wifi disconnect --ip IP [--port 5555]
- autophone wifi list
- autophone keyboard install [--device 设备ID] [--verify-only]
- autophone version

使用示例：
  autophone run "打开微信"
  autophone run "查看时间" --save-screenshot -v
  autophone batch -i 问题.xlsx -o 答案.xlsx -t "请详细解答：{content}"
  autophone wifi connect --ip 192.168.1.100 --port 5555
  autophone wifi disconnect --ip 192.168.1.100
  autophone wifi list
  autophone keyboard install --device ABC123DEF456
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

import json
from datetime import datetime
import typer

try:
    # 仅在需要时导入，避免无 pandas 的环境下调用非 batch 命令出错
    import pandas as pd  # type: ignore
except Exception:
    pd = None  # 延迟校验

# 延迟导入 PhoneAgentAPI，以避免仅查看 --help 时触发重型依赖导入

app = typer.Typer(help="AutoPhone 命令行工具", add_completion=False)

# ------------------------
# 公共工具函数
# ------------------------

def _run_command(command: str, timeout: Optional[int] = None):
    """
    执行系统命令，返回 (returncode, stdout, stderr)
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "命令执行超时"
    except Exception as e:
        return -1, "", str(e)


def _project_root() -> Path:
    """
    计算项目根目录（phone_agent 包的上级目录）
    """
    return Path(__file__).resolve().parents[1]


# ------------------------
# run 子命令（单任务）
# ------------------------

@app.command("run")
def cmd_run(
    task: str = typer.Argument(..., help="任务描述（用引号包裹）"),
    save_screenshot: bool = typer.Option(False, "--save-screenshot", help="保存截图"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示详细输出"),
):
    """
    在手机上执行单个任务。
    """
    typer.echo(f"🚀 执行任务：{task}")
    typer.echo("-" * 60)

    from phone_agent.api import PhoneAgentAPI
    api = PhoneAgentAPI()
    result = api.run_task(task=task, save_screenshot=save_screenshot, verbose=verbose)

    typer.echo("\n" + "=" * 60)
    if getattr(result, "success", False):
        typer.echo("✅ 任务成功")
        typer.echo(f"答案：{getattr(result, 'answer', '')}")
        typer.echo(f"步数：{getattr(result, 'steps', 0)}")
        if getattr(result, "screenshot_base64", None):
            typer.echo("截图：已保存")
        raise typer.Exit(code=0)
    else:
        typer.echo("❌ 任务失败")
        typer.echo(f"错误：{getattr(result, 'error', 'unknown')}")
        raise typer.Exit(code=1)


# ------------------------
# batch 子命令（Excel 批量）
# ------------------------

@app.command("batch")
def cmd_batch(
    input: str = typer.Option(..., "--input", "-i", help="输入 Excel 文件路径"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="输出 Excel 文件路径（默认：input_answers.xlsx）"),
    column: str = typer.Option("问题", "--column", "-c", help="问题所在的列名"),
    template: str = typer.Option("请回答：{content}", "--template", "-t", help="任务模板，{content} 会被替换为实际问题"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示详细输出"),
):
    """
    读取 Excel 中的问题，批量执行后保存答案到原文档。
    """
    if pd is None:
        typer.echo("❌ 当前环境缺少 pandas/openpyxl，无法执行批处理。")
        typer.echo("   请安装依赖：pip install pandas openpyxl 或使用 uv 添加依赖")
        raise typer.Exit(code=1)

    input_path = Path(input)
    if output is None:
        output_path = input_path.parent / f"{input_path.stem}_answers{input_path.suffix}"
    else:
        output_path = Path(output)

    typer.echo(f"📖 读取文件：{input_path}")
    typer.echo(f"📝 问题列：{column}")
    typer.echo(f"💾 输出文件：{output_path}")
    typer.echo("-" * 60)

    # 读取 Excel
    df = pd.read_excel(str(input_path))  # type: ignore

    # 校验列
    if column not in df.columns:
        typer.echo(f"❌ 错误：找不到列 '{column}'")
        typer.echo(f"   可用列：{list(df.columns)}")
        raise typer.Exit(code=1)

    # 提取问题
    questions = (
        df[column].dropna().astype(str).map(lambda s: s.strip()).tolist()
    )
    questions = [q for q in questions if q and q != "nan"]

    if not questions:
        typer.echo("❌ 错误：没有找到任何问题")
        raise typer.Exit(code=1)

    typer.echo(f"✅ 找到 {len(questions)} 个问题")
    typer.echo("-" * 60)

    from phone_agent.api import PhoneAgentAPI
    api = PhoneAgentAPI()

    typer.echo("🚀 开始批量执行...")
    result = api.run_batch_parallel(
        questions=questions, task_template=template, verbose=verbose
    )

    # 输出统计
    typer.echo("\n" + "=" * 60)
    typer.echo("✅ 执行完成")
    typer.echo(f"   总计：{getattr(result, 'total', len(questions))}")
    typer.echo(f"   成功：{getattr(result, 'success_count', 0)}")
    typer.echo(f"   失败：{getattr(result, 'failed_count', 0)}")
    total_time = getattr(result, 'total_time', None)
    if total_time is not None:
        try:
            typer.echo(f"   耗时：{float(total_time):.2f}秒")
        except Exception:
            pass
    typer.echo("=" * 60)

    # 保存答案
    answers = [getattr(r, "answer", "") for r in getattr(result, "results", [])]
    # 若结果长度与问题不等，简单回填空串
    if len(answers) != len(df):
        # 尝试根据非空问题行回填
        filled = []
        it = iter(answers)
        for v in df[column]:
            if isinstance(v, float) and str(v) == "nan":
                filled.append("")
            elif v is None or (isinstance(v, str) and not v.strip()):
                filled.append("")
            else:
                filled.append(next(it, ""))
        df["答案"] = filled
    else:
        df["答案"] = answers  # type: ignore

    # 保存
    try:
        df.to_excel(str(output_path), index=False, engine="openpyxl")  # type: ignore
        typer.echo(f"\n💾 已保存到：{output_path}")
        typer.echo("   新增列：答案")
    except Exception as e:
        typer.echo(f"❌ 保存 Excel 失败：{e}")
        raise typer.Exit(code=1)

    # 示例输出
    typer.echo("\n" + "-" * 60)
    typer.echo("结果示例（前 3 个）:")
    typer.echo("-" * 60)
    for i in range(min(3, len(questions))):
        q = questions[i]
        a = answers[i] if i < len(answers) else ""
        typer.echo(f"\n{i+1}. 问题：{q[:50]}...")
        typer.echo(f"   答案：{a[:100]}...")


# ------------------------
# wifi 子命令组
# ------------------------

wifi_app = typer.Typer(help="WiFi 设备连接工具")
app.add_typer(wifi_app, name="wifi")

@wifi_app.command("list")
def cmd_wifi_list():
    """列出所有已连接的设备"""
    typer.echo("📱 已连接的 ADB 设备:")
    typer.echo("-" * 60)

    code, stdout, stderr = _run_command("adb devices")
    if code != 0:
        typer.echo("❌ 无法获取设备列表")
        raise typer.Exit(code=1)

    lines = stdout.strip().split("\n")
    if len(lines) <= 1:
        typer.echo("没有已连接的设备")
        raise typer.Exit(code=0)

    for line in lines[1:]:
        if line.strip():
            parts = line.split()
            if len(parts) >= 2:
                device_id = parts[0]
                status = parts[1]
                if "wifi" in device_id or ":" in device_id:
                    typer.echo(f"  📶 WiFi: {device_id} ({status})")
                else:
                    typer.echo(f"  🔌 USB:   {device_id} ({status})")


@wifi_app.command("connect")
def cmd_wifi_connect(
    ip: str = typer.Option(..., "--ip", "-i", help="设备 IP 地址（可含端口，如 192.168.1.3:40333）"),
    port: int = typer.Option(5555, "--port", "-p", help="ADB 端口（默认：5555，若 IP 已含端口则忽略）"),
):
    """连接 WiFi 设备"""
    # 处理设备地址
    if ":" in ip and not ip.endswith(":"):
        device_address = ip
        typer.echo(f"ℹ️  检测到 IP 已包含端口：{device_address}")
    else:
        device_address = f"{ip}:{port}"

    typer.echo(f"🔌 正在连接 WiFi 设备：{device_address}")
    typer.echo("-" * 60)

    # 检查 adb
    typer.echo("1️⃣ 检查 ADB 状态...")
    code, _, stderr = _run_command("adb version")
    if code != 0:
        typer.echo("❌ ADB 未安装或不可用")
        typer.echo(f"   错误：{stderr}")
        raise typer.Exit(code=1)
    typer.echo("✅ ADB 正常")

    # 尝试连接
    typer.echo(f"\n2️⃣ 连接到 {device_address}...")
    code, stdout, stderr = _run_command(f"adb connect {device_address}")
    output = (stdout or "") + (stderr or "")
    typer.echo(output)

    if "connected" in output or "already connected" in output.lower():
        typer.echo("✅ 连接成功！")
        # 验证列表
        typer.echo("\n3️⃣ 验证连接...")
        code, stdout, _ = _run_command("adb devices")
        typer.echo("已连接的设备:")
        found = False
        for line in stdout.split("\n"):
            if device_address in line and "device" in line:
                typer.echo(f"  ✅ {line.strip()}")
                found = True
                break
        if not found:
            typer.echo("⚠️  设备已连接但未在列表中显示，请稍后检查")
        raise typer.Exit(code=0)
    else:
        typer.echo("❌ 连接失败")
        if stderr:
            typer.echo(f"   错误：{stderr}")
        raise typer.Exit(code=1)


@wifi_app.command("disconnect")
def cmd_wifi_disconnect(
    ip: str = typer.Option(..., "--ip", "-i", help="设备 IP 地址"),
    port: int = typer.Option(5555, "--port", "-p", help="ADB 端口（默认：5555）"),
):
    """断开 WiFi 设备"""
    device_address = f"{ip}:{port}"
    typer.echo(f"🔌 正在断开 WiFi 设备：{device_address}")
    typer.echo("-" * 60)

    code, stdout, stderr = _run_command(f"adb disconnect {device_address}")
    output = (stdout or "") + (stderr or "")
    typer.echo(output)

    if "disconnected" in output.lower() or "no such device" in output.lower():
        typer.echo("✅ 已断开连接")
        raise typer.Exit(code=0)
    else:
        typer.echo("⚠️  设备可能已经断开或未连接")
        raise typer.Exit(code=1)


# ------------------------
# keyboard 子命令组（安装 ADB 键盘）
# ------------------------

keyboard_app = typer.Typer(help="USB 设备 ADB 键盘安装工具")
app.add_typer(keyboard_app, name="keyboard")


def _check_adb_installed() -> bool:
    typer.echo("🔍 检查 ADB 状态...")
    code, stdout, stderr = _run_command("adb version")
    if code != 0:
        typer.echo("❌ ADB 未安装或不可用")
        typer.echo("   请确保已安装 ADB 并添加到 PATH")
        return False
    version_line = stdout.strip().split("\n")[0] if stdout else "ADB"
    typer.echo(f"✅ ADB 已安装：{version_line}")
    return True


def _find_first_device() -> Optional[str]:
    code, stdout, _ = _run_command("adb devices")
    if code != 0:
        return None
    lines = (stdout or "").strip().split("\n")
    for line in lines[1:]:
        if line.strip() and "\tdevice" in line:
            return line.split("\t")[0]
    return None


def _verify_keyboard(device_id: str) -> bool:
    typer.echo("\n🔍 验证安装...")
    code, stdout, _ = _run_command(
        f'adb -s {device_id} shell pm list packages | grep com.android.adbkeyboard',
        timeout=10,
    )
    if "com.android.adbkeyboard" in (stdout or ""):
        typer.echo("✅ ADB 键盘已安装")
        typer.echo("\n💡 使用方法:")
        typer.echo("   1. 在手机上打开任意输入框")
        typer.echo("   2. 点击输入法选择按钮")
        typer.echo("   3. 选择 'ADB Keyboard'")
        typer.echo("   4. 现在可以自动输入文本了")
        return True
    else:
        typer.echo("⚠️  未检测到 ADB 键盘，可能需要手动在手机上切换输入法")
        return False


@keyboard_app.command("install")
def cmd_keyboard_install(
    device: Optional[str] = typer.Option(None, "--device", "-d", help="指定设备 ID（默认使用第一个）"),
    verify_only: bool = typer.Option(False, "--verify-only", help="只验证安装，不执行安装"),
):
    """安装或验证 ADB 键盘"""
    typer.echo("=" * 60)
    typer.echo("USB 设备 ADB 键盘安装工具")
    typer.echo("=" * 60)

    if not _check_adb_installed():
        raise typer.Exit(code=1)

    device_id = device or _find_first_device()
    if not device_id:
        typer.echo("❌ 没有已连接的设备")
        typer.echo("\n💡 提示:")
        typer.echo("   1. 用 USB 线连接手机到电脑")
        typer.echo("   2. 在手机上授权 USB 调试")
        typer.echo("   3. 运行 'adb devices' 验证")
        raise typer.Exit(code=1)

    if verify_only:
        ok = _verify_keyboard(device_id)
        raise typer.Exit(code=0 if ok else 1)

    # 寻找 APK 文件
    typer.echo("\n⌨️  安装 ADB 键盘...")
    candidate_paths = [
        _project_root() / "ADBKeyboard.apk",
        Path.cwd() / "ADBKeyboard.apk",
    ]
    apk_path: Optional[Path] = None
    for p in candidate_paths:
        if p.exists():
            apk_path = p
            break
    if not apk_path:
        typer.echo("❌ 找不到 ADBKeyboard.apk 文件")
        typer.echo("   请确保该文件在项目根目录")
        raise typer.Exit(code=1)

    typer.echo(f"📦 APK 文件：{apk_path}")
    typer.echo(f"\n🚀 开始安装到设备 {device_id}...")
    code, stdout, stderr = _run_command(f'adb -s {device_id} install "{apk_path}"', timeout=60)
    output = (stdout or "") + (stderr or "")
    typer.echo(output)

    if "Success" in output or "success" in output.lower():
        typer.echo("\n✅ 安装成功！")
        _verify_keyboard(device_id)
        raise typer.Exit(code=0)
    else:
        typer.echo("\n❌ 安装失败")
        if "already exists" in output.lower():
            typer.echo("ℹ️  键盘可能已经安装，可以在手机设置中切换输入法")
        raise typer.Exit(code=1)


# ------------------------
# config 子命令组（配置文件管理）
# ------------------------

config_app = typer.Typer(help="配置文件管理工具（读取/修改 config.json）")
app.add_typer(config_app, name="config")


def _config_default_path() -> Path:
    """默认配置文件路径：项目根目录下的 config.json"""
    return _project_root() / "config.json"


def _load_config(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        typer.echo(f"❌ 读取配置失败：{e}")
        raise typer.Exit(code=1)


def _save_config(path: Path, data: dict, backup: bool = True):
    if backup and path.exists():
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        backup_path = path.with_suffix(path.suffix + f".bak.{ts}")
        try:
            backup_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
            typer.echo(f"🗂️  已创建备份：{backup_path}")
        except Exception as e:
            typer.echo(f"⚠️  创建备份失败：{e}")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except Exception as e:
        typer.echo(f"❌ 写入配置失败：{e}")
        raise typer.Exit(code=1)


def _get_by_path(d: dict, path: str):
    cur = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _set_by_path(d: dict, path: str, value):
    parts = path.split(".")
    cur = d
    for p in parts[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = value


@config_app.command("path")
def cmd_config_path(
    path: Optional[str] = typer.Option(None, "--path", help="配置文件路径（默认：项目根目录 config.json）"),
):
    """显示配置文件实际路径"""
    target = Path(path) if path else _config_default_path()
    typer.echo(str(target.resolve()))


@config_app.command("show")
def cmd_config_show(
    path: Optional[str] = typer.Option(None, "--path", help="配置文件路径（默认：项目根目录 config.json）"),
):
    """打印完整配置内容（JSON 格式）"""
    target = Path(path) if path else _config_default_path()
    data = _load_config(target)
    typer.echo(json.dumps(data, ensure_ascii=False, indent=2))


@config_app.command("get")
def cmd_config_get(
    key: str = typer.Argument(..., help='键路径，支持点号语法，例如 "model.provider"'),
    path: Optional[str] = typer.Option(None, "--path", help="配置文件路径（默认：项目根目录 config.json）"),
):
    """读取配置中的指定键"""
    target = Path(path) if path else _config_default_path()
    data = _load_config(target)
    value = _get_by_path(data, key)
    if value is None:
        typer.echo("null")
    else:
        # 尽量以 JSON 形式输出，便于脚本化使用
        try:
            typer.echo(json.dumps(value, ensure_ascii=False))
        except Exception:
            typer.echo(str(value))


@config_app.command("set")
def cmd_config_set(
    key: str = typer.Argument(..., help='键路径，支持点号语法，例如 "model.local.base_url"'),
    value: str = typer.Argument(..., help='值，优先按 JSON 解析（如 true/123/{"a":1}），解析失败则作为字符串写入'),
    path: Optional[str] = typer.Option(None, "--path", help="配置文件路径（默认：项目根目录 config.json）"),
    backup: bool = typer.Option(True, "--backup/--no-backup", help="保存前是否生成备份（默认：是）"),
):
    """设置配置中的指定键并写回磁盘"""
    target = Path(path) if path else _config_default_path()
    data = _load_config(target)

    # 解析 value：优先尝试当作 JSON
    parsed = value
    try:
        parsed = json.loads(value)
    except Exception:
        # 保留原始字符串
        parsed = value

    _set_by_path(data, key, parsed)
    _save_config(target, data, backup=backup)
    typer.echo(f"✅ 已更新 {key}")
    # 输出变更后该键值，便于脚本化
    new_value = _get_by_path(data, key)
    try:
        typer.echo(json.dumps(new_value, ensure_ascii=False))
    except Exception:
        typer.echo(str(new_value))


# ------------------------
# 版本信息
# ------------------------

@app.command("version")
def cmd_version():
    """显示版本信息（简单占位）"""
    ver = None
    try:
        import phone_agent  # type: ignore
        ver = getattr(phone_agent, "__version__", None)
    except Exception:
        pass
    typer.echo(f"AutoPhone CLI 版本：{ver or '0.1.0'}")


def main():
    """入口函数，便于 python -m 或直接调用"""
    app()


if __name__ == "__main__":
    main()
