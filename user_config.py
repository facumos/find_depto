import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_FILE = Path("user_configs.json")

DEFAULT_CONFIG = {
    "min_price": 100000,
    "max_price": 500000,
    "min_rooms": 1,
    "max_rooms": 3,  
    "max_expensas": 100000
}


def load_all_configs():
    """Load all user configurations from disk."""
    try:
        if CONFIG_FILE.exists():
            content = CONFIG_FILE.read_text(encoding='utf-8')
            return json.loads(content)
        return {}
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Failed to load user configs: {e}")
        return {}


def save_all_configs(configs):
    """Save all user configurations to disk."""
    try:
        CONFIG_FILE.write_text(
            json.dumps(configs, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
    except Exception as e:
        logger.error(f"Failed to save user configs: {e}")


def get_user_config(user_id):
    """Get configuration for a specific user, returning defaults if not set."""
    configs = load_all_configs()
    user_id_str = str(user_id)
    if user_id_str in configs:
        config = DEFAULT_CONFIG.copy()
        config.update(configs[user_id_str])
        return config
    return DEFAULT_CONFIG.copy()


def set_user_config(user_id, key, value):
    """Set a specific configuration value for a user."""
    configs = load_all_configs()
    user_id_str = str(user_id)
    if user_id_str not in configs:
        configs[user_id_str] = {}
    configs[user_id_str][key] = value
    save_all_configs(configs)


def get_all_user_ids():
    """Get all user IDs that have configurations."""
    configs = load_all_configs()
    return list(configs.keys())
