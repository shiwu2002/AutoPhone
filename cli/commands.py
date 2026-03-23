"""设备命令和批量模式处理"""

from phone_agent.config.apps import list_supported_apps
from phone_agent.device_factory import DeviceType, get_device_factory, set_device_type
from phone_agent.model import ModelConfig

# Try to import pandas for batch mode
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

from .config_loader import load_config
from .checks import check_system_requirements


def handle_device_commands(args) -> bool:
    """
    Handle device-related commands.

    Returns:
        True if a device command was handled (should exit), False otherwise.
    """
    device_factory = get_device_factory()
    ConnectionClass = device_factory.get_connection_class()
    conn = ConnectionClass()

    # Handle --list-devices
    if args.list_devices:
        devices = device_factory.list_devices()
        if not devices:
            print("No devices connected.")
        else:
            print("Connected devices:")
            print("-" * 60)
            for device in devices:
                status_icon = "[OK]" if device.status == "device" else "[ERR]"
                conn_type = device.connection_type.value
                model_info = f" ({device.model})" if device.model else ""
                print(
                    f"  {status_icon} {device.device_id:<30} [{conn_type}]{model_info}"
                )
        return True

    # Handle --connect
    if args.connect:
        print(f"Connecting to {args.connect}...")
        success, message = conn.connect(args.connect)
        print(f"{'✓' if success else '✗'} {message}")
        if success:
            args.device_id = args.connect
        return not success

    # Handle --disconnect
    if args.disconnect:
        if args.disconnect == "all":
            print("Disconnecting all remote devices...")
            success, message = conn.disconnect()
        else:
            print(f"Disconnecting from {args.disconnect}...")
            success, message = conn.disconnect(args.disconnect)
        print(f"{'✓' if success else '✗'} {message}")
        return True

    # Handle --enable-tcpip
    if args.enable_tcpip:
        port = args.enable_tcpip
        print(f"Enabling TCP/IP debugging on port {port}...")
        success, message = conn.enable_tcpip(port, args.device_id)
        print(f"{'✓' if success else '✗'} {message}")

        if success:
            ip = conn.get_device_ip(args.device_id)
            if ip:
                print(f"\nYou can now connect remotely using:")
                print(f"  python main.py --connect {ip}:{port}")
                print(f"\nOr via ADB directly:")
                print(f"  adb connect {ip}:{port}")
            else:
                print("\nCould not determine device IP. Check device WiFi settings.")
        return True

    return False


def run_batch_mode(args) -> None:
    """运行批量模式。"""
    from phone_agent.batch_runner import BatchQuestionRunner, BatchConfig

    print("=" * 60)
    print("Phone Agent - Batch Mode")
    print("=" * 60)

    device_type = DeviceType.ADB
    set_device_type(device_type)

    config = load_config()
    model_config_dict = config.get('model', {})
    agent_config_dict = config.get('agent', {})

    # Get provider-specific config
    provider = model_config_dict.get('provider', 'local')
    provider_config = model_config_dict.get(provider, {})

    model_cfg = ModelConfig(
        base_url=args.base_url or provider_config.get('base_url', 'http://localhost:11434/v1'),
        model_name=args.model or provider_config.get('model', 'qwen3.5:4b'),
        api_key=args.apikey or provider_config.get('api_key', 'ollama'),
        use_thinking=model_config_dict.get('use_thinking', False),
        lang=args.lang,
        provider=provider,
    )

    batch_cfg = BatchConfig(
        question_column=args.question_column,
        max_questions=args.max_questions,
        skip_existing=args.skip_existing,
        verbose=args.verbose or (not args.quiet),
        max_steps=agent_config_dict.get('max_steps', 50),
    )

    print(f"Input file:      {args.batch}")
    print(f"Output file:     {args.batch_output}")
    print(f"Question column: {args.question_column}")
    print(f"Max questions:   {args.max_questions if args.max_questions > 0 else 'All'}")
    print(f"Skip existing:   {args.skip_existing}")
    print(f"Model:           {model_cfg.model_name}")
    print("=" * 60)

    if not PANDAS_AVAILABLE:
        print("\n⚠️  Warning: pandas not installed. Excel support requires pandas.")
        print("   Install with: pip install pandas openpyxl\n")

    runner = BatchQuestionRunner(model_config=model_cfg, batch_config=batch_cfg)

    if args.skip_existing and args.batch.lower().endswith(('.xlsx', '.xls')):
        print("\nLoading existing results...")

    print(f"\nLoading questions from {args.batch}...")
    try:
        runner.load_questions(args.batch, column=args.question_column)
    except Exception as e:
        print(f"❌ Failed to load questions: {e}")
        return

    if not check_system_requirements(device_type, args):
        print("\n⚠️  System check failed, continuing anyway...")

    print("\nStarting batch execution...\n")
    try:
        results = runner.run_batch()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        runner._save_progress()
        print("Progress saved to batch_progress.json")
        return
    except Exception as e:
        print(f"\n❌ Batch execution failed: {e}")
        return

    print(f"\nExporting results to {args.batch_output}...")
    try:
        runner.export_results(args.batch_output, format="excel")
    except Exception as e:
        print(f"❌ Failed to export results: {e}")
        json_output = args.batch_output.rsplit('.', 1)[0] + '.json'
        runner.export_results(json_output, format="json")
        print(f"Results exported to {json_output} instead.")

    success_count = sum(1 for r in results if r.success)
    failed_count = len(results) - success_count

    print("\n" + "=" * 60)
    print("Batch Execution Summary")
    print("=" * 60)
    print(f"Total questions:  {len(results)}")
    print(f"Successful:       {success_count}")
    print(f"Failed:           {failed_count}")
    print(f"Success rate:     {success_count/len(results)*100:.1f}%" if results else "N/A")
    print("=" * 60)
