"""
Main entry point for the Discord bot.

This module initializes and runs the bot, handling startup and shutdown processes.
"""

import asyncio
import nextcord
import logging
from bot import MusicBot
from bot.events import EventHandlers
from cogs import get_all_cogs
import signal
import sys
import config

# Set up logging
logging.basicConfig(
    level=logging.INFO if config.ENV != "development" else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('music_bot')
logger.info(f"Starting bot in {config.ENV} environment")

# Create bot instance
intents = nextcord.Intents(
    messages=True,
    guilds=True,
    voice_states=True,
    message_content=True
)

bot = MusicBot(intents=intents)

# Global variable for clean shutdown
shutdown_event = asyncio.Event()

async def load_extensions():
    """Load all extensions (cogs) for the bot."""
    for cog in get_all_cogs():
        try:
            await bot.load_extension(cog)
            logger.info(f"Loaded extension: {cog}")
        except Exception as e:
            logger.error(f"Failed to load extension {cog}: {e}")

async def cleanup():
    """Perform cleanup operations before shutdown."""
    logger.info("Performing cleanup operations...")
    
    # Disconnect from all voice channels
    for voice_client in list(bot.voice_clients):
        try:
            await voice_client.disconnect(force=True)
        except:
            pass
    
    # Close lavalink connections
    if hasattr(bot, 'pool'):
        for node in bot.pool.nodes.values():
            await node.disconnect()
    
    # Close character AI connections
    if hasattr(bot, 'char_ai_client'):
        try:
            await bot.char_ai_client.close()
        except:
            pass
    
    logger.info("Cleanup complete")

async def shutdown():
    """Shutdown the bot gracefully."""
    logger.info("Shutting down...")
    
    # Set shutdown event
    shutdown_event.set()
    
    # Perform cleanup
    await cleanup()
    
    # Close the bot
    await bot.close()

def handle_signal(sig, frame):
    """Handle termination signals."""
    logger.info(f"Received signal {sig}")
    
    # Schedule the shutdown in the event loop
    if bot.loop.is_running():
        bot.loop.create_task(shutdown())
    else:
        # If the loop isn't running, run the shutdown function directly
        asyncio.run(shutdown())

# Register signal handlers
signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

@bot.event
async def on_ready():
    """Event that fires when the bot is ready."""
    logger.info(f'Logged in as {bot.user} (ID: {bot.user.id})')
    logger.info(f'Connected to {len(bot.guilds)} guilds')
    
    # Initialize Character AI
    if config.ENABLE_CHARACTER_AI and config.AI_TOKEN and config.CHAR_ID:
        await bot.init_character_ai()
    
    # Set custom status
    activity = nextcord.Activity(
        type=nextcord.ActivityType.listening,
        name="music and chatting"
    )
    await bot.change_presence(activity=activity)
    
    logger.info("Bot is ready!")

# Run the bot
if __name__ == "__main__":
    # Load extensions first
    bot.loop.create_task(load_extensions())
    
    try:
        # Start the bot
        bot.run(config.TOKEN)
    except Exception as e:
        logger.critical(f"Failed to start bot: {e}")
        sys.exit(1)
    finally:
        # If we get here, the bot has closed
        logger.info("Bot has shut down")