import nextcord
from nextcord.ext import commands
import mafic
import logging
from collections import deque, Counter
import random

from utils import MusicQueue, MusicLock
import config

class MusicBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set up music client
        self.pool = mafic.NodePool(self)
        self.loop.create_task(self.add_nodes())
        
        # Music state tracking
        self.music_queues = {}
        self.text_channels = {}  # Store text channels for each guild
        self.play_locks = {}
        self.current_song = {}
        self.play_history = {}
        
        # Recommendation system
        self.recommendation_enabled = {}
        self.recommendation_history = {}
        self.max_recommendation_history = config.MAX_RECOMMENDATION_HISTORY
        
        # Replay mode
        self.replay_mode = {}  # Store replay mode state for each guild

    async def add_nodes(self):
        """Add Lavalink nodes to the pool."""
        await self.pool.create_node(
            host=config.LAVALINK_HOST,
            port=config.LAVALINK_PORT,
            label=config.LAVALINK_LABEL,
            password=config.LAVALINK_PASSWORD,
        )

    async def on_ready(self):
        """Called when the bot is ready."""
        logging.info(f'We have logged in as {self.user}')
        
    async def on_message(self, message):
        """Handle incoming messages."""
        # Skip messages from bots to prevent loops
        if message.author.bot:
            return
            
        # Process commands in messages if they exist
        await self.process_commands(message)