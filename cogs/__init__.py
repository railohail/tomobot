"""
Cog modules for the Discord bot.

This package contains all the cogs that provide functionality to the bot.
"""

# Define available cogs
def get_all_cogs():
    """Return a list of all available cogs."""
    return [
        "cogs.music",
        "cogs.admin",
        "cogs.character_ai",
        "cogs.general"
    ]

__all__ = ["get_all_cogs"]