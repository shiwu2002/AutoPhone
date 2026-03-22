"""Timing 配置应用"""


def apply_timing_config(timing_dict: dict, args) -> None:
    """Apply timing configuration from config file and command line args."""
    from phone_agent.config.timing import (
        ActionTimingConfig,
        DeviceTimingConfig,
        ConnectionTimingConfig,
        update_timing_config,
    )

    action = ActionTimingConfig.from_dict(timing_dict.get('action', {}))
    device = DeviceTimingConfig.from_dict(timing_dict.get('device', {}))
    connection = ConnectionTimingConfig.from_dict(timing_dict.get('connection', {}))

    if args.keyboard_switch_delay is not None:
        action.keyboard_switch_delay = args.keyboard_switch_delay
    if args.text_clear_delay is not None:
        action.text_clear_delay = args.text_clear_delay
    if args.text_input_delay is not None:
        action.text_input_delay = args.text_input_delay
    if args.keyboard_restore_delay is not None:
        action.keyboard_restore_delay = args.keyboard_restore_delay

    if args.tap_delay is not None:
        device.default_tap_delay = args.tap_delay
    if args.double_tap_delay is not None:
        device.default_double_tap_delay = args.double_tap_delay
    if args.double_tap_interval is not None:
        device.double_tap_interval = args.double_tap_interval
    if args.long_press_delay is not None:
        device.default_long_press_delay = args.long_press_delay
    if args.swipe_delay is not None:
        device.default_swipe_delay = args.swipe_delay
    if args.back_delay is not None:
        device.default_back_delay = args.back_delay
    if args.home_delay is not None:
        device.default_home_delay = args.home_delay
    if args.launch_delay is not None:
        device.default_launch_delay = args.launch_delay

    if args.adb_restart_delay is not None:
        connection.adb_restart_delay = args.adb_restart_delay
    if args.server_restart_delay is not None:
        connection.server_restart_delay = args.server_restart_delay

    update_timing_config(action=action, device=device, connection=connection)
