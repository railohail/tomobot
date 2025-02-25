import nextcord
import logging
import os
from dotenv import load_dotenv

from bot import MusicBot

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

def main():
    # Create bot instance with all privileges
    intents = nextcord.Intents.default()
    intents.message_content = True
    intents.messages = True
    intents.guilds = True
    intents.voice_states = True
    
    bot = MusicBot(intents=intents)
    
    # Load cogs - no CharacterAI
    bot.load_extension("cogs.music")
    bot.load_extension("cogs.recommendations")
    bot.load_extension("cogs.library") 
    
    # Start bot
    bot.run(os.getenv("DISCORD_BOT_TOKEN"))

if __name__ == "__main__":
    main()