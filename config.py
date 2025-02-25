"""
Configuration management for the Discord bot.

This module handles loading and validating configuration from environment variables.
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv
import logging

logger = logging.getLogger('music_bot')

# Load environment variables
load_dotenv()

# Environment selection
ENV = os.getenv("ENV", "development").lower()

# Bot configuration
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN must be set in .env file")

TESTING_GUILD_ID = os.getenv("DISCORD_GUILD")
try:
    if TESTING_GUILD_ID:
        TESTING_GUILD_ID = int(TESTING_GUILD_ID)
except ValueError:
    logger.warning(f"Invalid DISCORD_GUILD value: {TESTING_GUILD_ID}. Must be an integer.")
    TESTING_GUILD_ID = None

# Lavalink configuration
LAVALINK_HOST = os.getenv("LAVALINK_HOST", "127.0.0.1")
LAVALINK_PORT = int(os.getenv("LAVALINK_PORT", "2333"))
LAVALINK_PASSWORD = os.getenv("LAVALINK_PASSWORD", "youshallnotpass")

# Character AI configuration
AI_TOKEN = os.getenv("AI_TOKEN")
if not AI_TOKEN and ENV != "test":
    logger.warning("AI_TOKEN not set. Character AI features will be disabled.")

CHAR_ID = os.getenv("CHAR_ID")
if not CHAR_ID and ENV != "test":
    logger.warning("CHAR_ID not set. Character AI features will be disabled.")

# Bot settings
MAX_RECOMMENDATION_HISTORY = int(os.getenv("MAX_RECOMMENDATION_HISTORY", "100"))
DEFAULT_PREFIX = os.getenv("DEFAULT_PREFIX", "!")
COMMAND_COOLDOWN = int(os.getenv("COMMAND_COOLDOWN", "3"))
MAX_QUEUE_SIZE = int(os.getenv("MAX_QUEUE_SIZE", "500"))
AUTO_DISCONNECT_AFTER = int(os.getenv("AUTO_DISCONNECT_AFTER", "300"))  # 5 minutes

# Feature flags
ENABLE_CHARACTER_AI = os.getenv("ENABLE_CHARACTER_AI", "true").lower() == "true"
ENABLE_RECOMMENDATIONS = os.getenv("ENABLE_RECOMMENDATIONS", "true").lower() == "true"

def get_config() -> Dict[str, Any]:
    """
    Get the complete configuration as a dictionary.
    
    Returns:
        Dictionary containing all configuration values
    """
    return {k: v for k, v in globals().items() 
            if k.isupper() and not k.startswith('_')}