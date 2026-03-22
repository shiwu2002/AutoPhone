"""配置加载器"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def load_config() -> dict:
    """从配置文件加载配置。"""
    config_path = Path(__file__).parent.parent / "config.json"

    if not config_path.exists():
        logger.warning("Config file not found, using default values")
        return {}

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        logger.info("Loaded configuration from config.json")
        return config
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing config.json: {e}, using default values")
        return {}
    except Exception as e:
        logger.error(f"Error loading config: {e}, using default values")
        return {}
