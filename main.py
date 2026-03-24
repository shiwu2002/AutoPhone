#!/usr/bin/env python3
"""Phone Agent - AI-powered phone automation

Main entry point for the Phone Agent application.
"""

import sys

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from phone_agent import PhoneAgent
from phone_agent.agent import AgentConfig
from phone_agent.device_factory import DeviceType, set_device_type
from phone_agent.model import ModelConfig
from phone_agent.adb.cmd_executor import close_console

# Import CLI module
from cli import (
    parse_args,
    load_config,
    check_system_requirements,
    check_model_api,
    handle_device_commands,
    run_batch_mode,
    run_config_wizard,
    apply_timing_config,
)
from phone_agent.config.apps import list_supported_apps


def main():
    """Main entry point."""
    args = parse_args()

    # Set device type globally
    device_type = DeviceType.ADB
    set_device_type(device_type)

    # Handle --config (interactive configuration wizard)
    if args.config:
        run_config_wizard()
        return

    # Handle --list-apps (no system check needed)
    if args.list_apps:
        print("Supported Android apps:")
        apps = list_supported_apps()
        for app in sorted(apps):
            print(f"  - {app}")
        return

    # Handle --install-keyboard
    if args.install_keyboard:
        from bin.install_keyboard import main as install_keyboard_main
        sys.exit(install_keyboard_main())

    # Handle --batch mode
    if args.batch:
        run_batch_mode(args)
        return

    # Handle device commands
    if handle_device_commands(args):
        return

    # Run system requirements check
    if not check_system_requirements(device_type, args):
        sys.exit(1)

    # Check model API connectivity
    if not check_model_api(args.base_url, args.model, args.apikey):
        sys.exit(1)

    # Load timing configuration
    config = load_config()
    timing_dict = config.get('timing', {})
    apply_timing_config(timing_dict, args)

    # Create model and agent configurations
    model_config_dict = config.get('model', {})
    provider = model_config_dict.get('provider', 'local')
    # Support both new format (model.providers.{provider}) and old format (model.{provider})
    provider_config = model_config_dict.get('providers', {}).get(provider, {}) or model_config_dict.get(provider, {})

    # Use provider-specific config, fallback to CLI args
    model_config = ModelConfig(
        base_url=args.base_url or provider_config.get('base_url', 'http://localhost:8000/v1'),
        model_name=args.model or provider_config.get('model', 'claude-opus-4-6-20251101'),
        api_key=args.apikey or provider_config.get('api_key', ''),
        lang=args.lang,
        use_thinking=model_config_dict.get('use_thinking', False),
        provider=provider,
    )

    # Priority: --verbose > --quiet > config file
    verbose = args.verbose or (not args.quiet)
    agent_config = AgentConfig(
        max_steps=args.max_steps or config.get('agent', 'max_steps', 0),
        device_id=args.device_id or config.get('agent', 'device_id'),
        verbose=verbose,
        lang=args.lang or config.get('agent', 'lang', 'cn'),
        max_context_rounds=config.get('agent', 'max_context_rounds', 5),
        remember_app_info=config.get('agent', 'remember_app_info', True),
        max_repeated_actions=config.get('agent', 'max_repeated_actions', 3),
        enable_repeat_detection=config.get('agent', 'enable_repeat_detection', True),
    )

    # Create and run agent
    agent = PhoneAgent(
        model_config=model_config,
        agent_config=agent_config,
    )

    # Print header
    print("=" * 50)
    print("Phone Agent - AI-powered phone automation")
    print("=" * 50)
    print(f"Model: {model_config.model_name}")
    print(f"Base URL: {model_config.base_url}")
    print(f"Max Steps: {agent_config.max_steps}")
    print(f"Language: {agent_config.lang}")
    print(f"Device Type: ADB")

    # Show device info
    from phone_agent.device_factory import get_device_factory
    devices = get_device_factory().list_devices()
    if agent_config.device_id:
        print(f"Device: {agent_config.device_id}")
    elif devices:
        print(f"Device: {devices[0].device_id} (auto-detected)")

    print("=" * 50)

    # Run with provided task or enter interactive mode
    if args.task:
        print(f"\nTask: {args.task}\n")
        result = agent.run(args.task)
        print(f"\nResult: {result}")
    else:
        # Interactive mode
        print("\nEntering interactive mode. Type 'quit' to exit.\n")

        while True:
            try:
                task = input("Enter your task: ").strip()

                if task.lower() in ("quit", "exit", "q"):
                    print("Goodbye!")
                    break

                if not task:
                    continue

                print()
                result = agent.run(task)
                print(f"\nResult: {result}\n")
                agent.reset()

            except KeyboardInterrupt:
                print("\n\nInterrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\nError: {e}\n")

    # Close the console window
    close_console()


if __name__ == "__main__":
    main()
