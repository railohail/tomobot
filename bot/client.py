import nextcord
from nextcord.ext import commands
import mafic
import logging
from characterai import aiocai
from utils.music_queue import MusicQueue
from .events import EventHandlers
import config

class MusicBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set up logging
        self.logger = logging.getLogger('music_bot')
        
        # Set up music system
        self.pool = mafic.NodePool(self)
        self.loop.create_task(self.add_nodes())
        self.music_queue = MusicQueue()
        
        # Set up character AI
        self.char_ai_client = aiocai.Client(config.AI_TOKEN)
        self.char_ai_chat = None
        self.char_ai_chat_id = None
        self.me = None
        
        # Set up event handlers
        self.event_handlers = EventHandlers(self)
    
    async def add_nodes(self):
        """Connect to Lavalink nodes."""
        try:
            await self.pool.create_node(
                host=config.LAVALINK_HOST,
                port=config.LAVALINK_PORT,
                label="MAIN",
                password=config.LAVALINK_PASSWORD,
            )
            self.logger.info(f"Connected to Lavalink node at {config.LAVALINK_HOST}:{config.LAVALINK_PORT}")
        except Exception as e:
            self.logger.error(f"Failed to connect to Lavalink node: {e}")
    
    async def setup_hook(self):
        """Additional setup after the bot is ready."""
        self.logger.info("Loading extensions...")
        
        # Load cogs
        await self.load_extension("cogs.music")
        await self.load_extension("cogs.recommendations")
        await self.load_extension("cogs.character_ai")
        
        self.logger.info("All extensions loaded")
        
    async def init_character_ai(self):
        """Initialize the Character AI chat."""
        try:
            self.me = await self.char_ai_client.get_me()
            
            # Initialize the single chat
            async with await self.char_ai_client.connect() as chat:
                new, answer = await chat.new_chat(config.CHAR_ID, self.me.id)
                self.char_ai_chat = chat
                self.char_ai_chat_id = new.chat_id
            self.logger.info("Character AI chat initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize Character AI: {e}")