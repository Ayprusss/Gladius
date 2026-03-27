import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ConfigLoader:
    """Loads configuration from yaml and overrides with environment variables."""

    @staticmethod
    def load_config() -> Dict[str, Any]:
        # Path to config/settings.yaml relative to this file
        config_path = Path(__file__).parent.parent / 'config' / 'settings.yaml'
        config = {}
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                logger.debug(f"Loaded config from {config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config file {config_path}: {e}")

        # Override with environment variables
        # Format: GLADIUS_SECTION_KEY=value -> config['section']['key'] = value
        for env_var, value in os.environ.items():
            if env_var.startswith('GLADIUS_'):
                parts = env_var[8:].lower().split('_')
                if len(parts) >= 2:
                    section = parts[0]
                    # The rest forms the key
                    key = '_'.join(parts[1:])
                    
                    if section not in config:
                        if isinstance(config, dict):
                            config[section] = {}
                        else:
                            continue
                            
                    # Type conversion
                    if value.lower() in ('true', 'yes', '1'):
                        val = True
                    elif value.lower() in ('false', 'no', '0'):
                        val = False
                    elif value.isdigit():
                        val = int(value)
                    else:
                        val = value
                        
                    if isinstance(config.get(section), dict):
                        config[section][key] = val
                        logger.debug(f"Overridden config via env var: {section}.{key} = {val}")

        return config
