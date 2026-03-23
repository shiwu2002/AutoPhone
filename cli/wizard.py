"""配置向导模块"""

import json
from pathlib import Path
from urllib.parse import urlparse

from openai import OpenAI

from .config_loader import load_config


def check_ollama_service(base_url: str) -> bool:
    """Check if Ollama service is running."""
    import requests

    try:
        parsed = urlparse(base_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        response = requests.get(f"{base}/api/tags", timeout=3.0)
        if response.status_code == 200:
            return True
    except Exception:
        pass

    try:
        parsed = urlparse(base_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        response = requests.get(f"{base}/api/version", timeout=3.0)
        if response.status_code == 200:
            return True
    except Exception:
        pass

    try:
        client = OpenAI(base_url=base_url, api_key="ollama", timeout=3.0)
        response = client.chat.completions.create(
            model="llama3.2",
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=1,
            stream=False,
        )
        return True
    except Exception:
        return False


def list_ollama_models(base_url: str) -> list[str]:
    """List available models in Ollama."""
    try:
        client = OpenAI(base_url=base_url, api_key="ollama", timeout=5.0)
        models = client.models.list()
        return [model.id for model in models.data]
    except Exception:
        return []


def _save_config(config: dict, config_path: Path):
    """Save configuration to file."""
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def _save_config_interactive(config: dict, config_path: Path):
    """Save configuration to file."""
    print()
    print("Saving configuration...")
    _save_config(config, config_path)
    print("✅ Configuration saved!")


def _configure_agent_interactive(config: dict, agent_config: dict):
    """Configure agent settings interactively."""
    print()
    print("=" * 50)
    print("Agent Configuration")
    print("=" * 50)
    print()

    default_max_steps = agent_config.get('max_steps', 0)
    max_steps_input = input(f"Enter maximum steps per task (0=unlimited) [{default_max_steps}]: ").strip()
    max_steps = int(max_steps_input) if max_steps_input else default_max_steps

    default_lang = agent_config.get('lang', 'cn')
    print("Select language:")
    print("  1. 中文 (Chinese)")
    print("  2. English")
    lang_choice = input(f"Enter choice (1/2) [{'1' if default_lang == 'cn' else '2'}]: ").strip()
    lang = 'cn' if lang_choice == '1' or (not lang_choice and default_lang == 'cn') else 'en'

    default_verbose = agent_config.get('verbose', True)
    verbose_input = input(f"Enable verbose output? [Y/n]: ").strip().lower()
    verbose = verbose_input not in ('n', 'no') if verbose_input else default_verbose

    config['agent'] = {
        'max_steps': max_steps,
        'device_id': agent_config.get('device_id'),
        'verbose': verbose,
        'lang': lang
    }

    print("✅ Agent configuration saved!")


def _configure_device_interactive(config: dict, device_config: dict):
    """Configure device settings interactively."""
    print()
    print("=" * 50)
    print("Device Configuration")
    print("=" * 50)
    print()

    default_auto_connect = device_config.get('auto_connect', True)
    auto_connect_input = input(f"Auto-connect to device on startup? [Y/n]: ").strip().lower()
    auto_connect = auto_connect_input not in ('n', 'no') if auto_connect_input else default_auto_connect

    config['device'] = {
        'type': 'adb',
        'remote_address': device_config.get('remote_address'),
        'auto_connect': auto_connect
    }
    print("✅ Device configuration saved!")


def _configure_timing_interactive(config: dict):
    """Configure timing settings interactively."""
    print()
    print("=" * 50)
    print("Advanced Configuration (Timing)")
    print("=" * 50)
    print()

    timing_config = config.get('timing', {})

    configure_timing = input("Would you like to configure timing settings? [y/N]: ").strip().lower()
    if configure_timing not in ('y', 'yes'):
        print("⏭️  Skipping advanced timing configuration.")
        return

    print()
    print("Timing settings control delays between actions.")
    print("You can accept defaults by pressing Enter for each option.")
    print()

    # Action timing
    action_config = timing_config.get('action', {})
    print("--- Action Timing ---")
    default_value = action_config.get('keyboard_switch_delay', 1.0)
    value = input(f"Keyboard switch delay (seconds) [{default_value}]: ").strip()
    keyboard_switch_delay = float(value) if value else default_value

    default_value = action_config.get('text_clear_delay', 1.0)
    value = input(f"Text clear delay (seconds) [{default_value}]: ").strip()
    text_clear_delay = float(value) if value else default_value

    default_value = action_config.get('text_input_delay', 1.0)
    value = input(f"Text input delay (seconds) [{default_value}]: ").strip()
    text_input_delay = float(value) if value else default_value

    default_value = action_config.get('keyboard_restore_delay', 1.0)
    value = input(f"Keyboard restore delay (seconds) [{default_value}]: ").strip()
    keyboard_restore_delay = float(value) if value else default_value

    config['timing'] = {
        'action': {
            'keyboard_switch_delay': keyboard_switch_delay,
            'text_clear_delay': text_clear_delay,
            'text_input_delay': text_input_delay,
            'keyboard_restore_delay': keyboard_restore_delay
        }
    }

    # Device timing
    device_timing_config = timing_config.get('device', {})
    print()
    print("--- Device Timing ---")
    default_value = device_timing_config.get('default_tap_delay', 1.0)
    value = input(f"Tap delay (seconds) [{default_value}]: ").strip()
    default_tap_delay = float(value) if value else default_value

    default_value = device_timing_config.get('default_double_tap_delay', 1.0)
    value = input(f"Double tap delay (seconds) [{default_value}]: ").strip()
    default_double_tap_delay = float(value) if value else default_value

    default_value = device_timing_config.get('double_tap_interval', 0.1)
    value = input(f"Double tap interval (seconds) [{default_value}]: ").strip()
    double_tap_interval = float(value) if value else default_value

    default_value = device_timing_config.get('default_long_press_delay', 1.0)
    value = input(f"Long press delay (seconds) [{default_value}]: ").strip()
    default_long_press_delay = float(value) if value else default_value

    default_value = device_timing_config.get('default_swipe_delay', 1.0)
    value = input(f"Swipe delay (seconds) [{default_value}]: ").strip()
    default_swipe_delay = float(value) if value else default_value

    default_value = device_timing_config.get('default_back_delay', 1.0)
    value = input(f"Back delay (seconds) [{default_value}]: ").strip()
    default_back_delay = float(value) if value else default_value

    default_value = device_timing_config.get('default_home_delay', 1.0)
    value = input(f"Home delay (seconds) [{default_value}]: ").strip()
    default_home_delay = float(value) if value else default_value

    default_value = device_timing_config.get('default_launch_delay', 1.0)
    value = input(f"Launch delay (seconds) [{default_value}]: ").strip()
    default_launch_delay = float(value) if value else default_value

    config['timing']['device'] = {
        'default_tap_delay': default_tap_delay,
        'default_double_tap_delay': default_double_tap_delay,
        'double_tap_interval': double_tap_interval,
        'default_long_press_delay': default_long_press_delay,
        'default_swipe_delay': default_swipe_delay,
        'default_back_delay': default_back_delay,
        'default_home_delay': default_home_delay,
        'default_launch_delay': default_launch_delay
    }

    # Connection timing
    connection_config = timing_config.get('connection', {})
    print()
    print("--- Connection Timing ---")
    default_value = connection_config.get('adb_restart_delay', 2.0)
    value = input(f"ADB restart delay (seconds) [{default_value}]: ").strip()
    adb_restart_delay = float(value) if value else default_value

    default_value = connection_config.get('server_restart_delay', 1.0)
    value = input(f"Server restart delay (seconds) [{default_value}]: ").strip()
    server_restart_delay = float(value) if value else default_value

    config['timing']['connection'] = {
        'adb_restart_delay': adb_restart_delay,
        'server_restart_delay': server_restart_delay
    }

    print()
    print("✅ Timing configuration saved!")


def _configure_provider_interactive(config: dict, provider: str) -> dict:
    """Configure provider-specific settings interactively."""
    model_config = config.get('model', {})
    provider_config = model_config.get(provider, {})

    if provider == 'anthropic':
        print()
        print("Configuring Anthropic (Claude)")
        print("-" * 50)

        default_api_key = provider_config.get('api_key', '')
        default_model = provider_config.get('model', 'claude-opus-4-6-20251101')
        default_base_url = provider_config.get('base_url', 'https://api.anthropic.com')

        api_key = input(f"Enter Anthropic API key [{default_api_key or 'required'}]: ").strip() or default_api_key
        model = input(f"Enter model name [{default_model}]: ").strip() or default_model
        base_url = input(f"Enter base URL [{default_base_url}]: ").strip() or default_base_url

        return {
            'api_key': api_key,
            'base_url': base_url,
            'model': model,
            'max_tokens': provider_config.get('max_tokens', 4096)
        }

    elif provider == 'openai':
        print()
        print("Configuring OpenAI")
        print("-" * 50)

        default_api_key = provider_config.get('api_key', '')
        default_model = provider_config.get('model', 'gpt-4o')
        default_base_url = provider_config.get('base_url', 'https://api.openai.com/v1')

        api_key = input(f"Enter OpenAI API key [{default_api_key or 'required'}]: ").strip() or default_api_key
        model = input(f"Enter model name [{default_model}]: ").strip() or default_model
        base_url = input(f"Enter base URL [{default_base_url}]: ").strip() or default_base_url

        return {
            'api_key': api_key,
            'base_url': base_url,
            'model': model,
            'max_tokens': provider_config.get('max_tokens', 4096)
        }

    elif provider == 'local':
        print()
        print("Configuring Local Ollama")
        print("-" * 50)

        default_base_url = provider_config.get('base_url', 'http://localhost:11434/v1')
        default_model = provider_config.get('model', 'qwen3.5:7b')

        print()
        print(f"Checking Ollama service at {default_base_url}...", end=" ")
        ollama_running = check_ollama_service(default_base_url)

        if ollama_running:
            print("✅ Running")
            print()
            models = list_ollama_models(default_base_url)
            if models:
                print("Available models:")
                for i, model in enumerate(models, 1):
                    print(f"  {i}. {model}")
                print()

                model_choice = input(f"Select a model (1-{len(models)}) or enter custom name: ").strip()
                if model_choice.isdigit() and 1 <= int(model_choice) <= len(models):
                    selected_model = models[int(model_choice) - 1]
                elif model_choice:
                    selected_model = model_choice
                else:
                    selected_model = default_model
            else:
                print("⚠️  No models found. You may need to pull a model first.")
                print("   Run: ollama pull qwen3.5:7b")
                selected_model = input(f"Enter model name [{default_model}]: ").strip() or default_model
        else:
            print("❌ Not running")
            print()
            print("Please start Ollama service:")
            print("  1. Install Ollama: https://ollama.com/download")
            print("  2. Run: ollama serve")
            print("  3. Pull a model: ollama pull qwen3.5:7b")
            print()

            base_url = input(f"Enter Ollama base URL [{default_base_url}]: ").strip() or default_base_url
            selected_model = input(f"Enter model name [{default_model}]: ").strip() or default_model

        enable_thinking = input("Enable thinking feature for local model? [Y/n]: ").strip().lower()
        use_thinking = enable_thinking != 'n' and enable_thinking != 'no'

        config['use_thinking'] = use_thinking

        return {
            'base_url': default_base_url,
            'model': selected_model,
            'max_tokens': provider_config.get('max_tokens', 4096)
        }

    return {}


def _print_config_summary(config: dict):
    """Print configuration summary."""
    print()
    print("=" * 50)
    print("Configuration Summary")
    print("=" * 50)

    model = config.get('model', {})
    agent = config.get('agent', {})
    device = config.get('device', {})
    timing = config.get('timing', {})
    provider = model.get('provider', 'anthropic')
    provider_config = model.get(provider, {})

    print(f"Provider:        {provider.capitalize()}")
    print(f"Model:           {provider_config.get('model', 'unknown')}")
    if provider != 'local':
        print(f"API Key:         {'*' * 8}{provider_config.get('api_key', '')[-4:] if provider_config.get('api_key') else 'Not set'}")
    print(f"Base URL:        {provider_config.get('base_url', 'unknown')}")
    if provider == 'local':
        print(f"Thinking:        {'Enabled' if model.get('use_thinking') else 'Disabled'}")
    print(f"Language:        {'中文 (Chinese)' if agent.get('lang') == 'cn' else 'English'}")
    print(f"Max Steps:       {agent.get('max_steps', 0) if agent.get('max_steps', 0) > 0 else 'Unlimited'}")
    print(f"Verbose Output:  {'Yes' if agent.get('verbose') else 'No'}")
    print(f"Auto-connect:    {'Yes' if device.get('auto_connect') else 'No'}")

    if timing:
        print()
        print("Timing Settings:")
        action = timing.get('action', {})
        device_timing = timing.get('device', {})
        connection = timing.get('connection', {})
        if action:
            print(f"  Action delays: keyboard={action.get('keyboard_switch_delay', 1.0)}s, "
                  f"text_input={action.get('text_input_delay', 1.0)}s")
        if device_timing:
            print(f"  Device delays: tap={device_timing.get('default_tap_delay', 1.0)}s, "
                  f"swipe={device_timing.get('default_swipe_delay', 1.0)}s")
        if connection:
            print(f"  Connection delays: adb_restart={connection.get('adb_restart_delay', 2.0)}s")

    print("=" * 50)
    print()
    print("You can now run the agent with:")
    print("  python main.py")
    print()


def run_config_wizard():
    """Interactive configuration wizard for setting up model provider."""
    print("=" * 50)
    print("Phone Agent - Configuration Wizard")
    print("=" * 50)
    print()

    config_path = Path(__file__).parent.parent / "config.json"
    config = load_config()

    model_config = config.get('model', {})
    agent_config = config.get('agent', {})
    device_config = config.get('device', {})

    # ========== Provider Selection ==========
    print("=" * 50)
    print("1. Select Model Provider")
    print("=" * 50)
    print()
    print("Select model provider:")
    print("  1. Anthropic (Claude)")
    print("  2. OpenAI (GPT)")
    print("  3. Local (Ollama)")
    print()

    current_provider = model_config.get('provider', 'anthropic')
    provider_map = {'1': 'anthropic', '2': 'openai', '3': 'local'}
    provider_display = {'anthropic': '1', 'openai': '2', 'local': '3'}

    choice = input(f"Enter your choice (1/2/3) [{provider_display.get(current_provider, '1')}]: ").strip()
    provider = provider_map.get(choice, provider_map.get(provider_display.get(current_provider, '1'), 'anthropic'))

    print()
    print(f"Selected: {provider.capitalize()}")

    # ========== Provider Configuration ==========
    provider_settings = _configure_provider_interactive(config, provider)

    # Initialize model config with provider
    if 'model' not in config:
        config['model'] = {}

    config['model']['provider'] = provider
    config['model'][provider] = provider_settings

    # Remove old format keys if they exist
    for key in ['type', 'base_url', 'model_name', 'api_key']:
        if key in config['model']:
            del config['model'][key]

    _save_config_interactive(config, config_path)
    _configure_agent_interactive(config, agent_config)
    _configure_device_interactive(config, device_config)
    _configure_timing_interactive(config)
    _save_config(config, config_path)
    _print_config_summary(config)
