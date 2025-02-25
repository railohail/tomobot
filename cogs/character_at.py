import nextcord
from nextcord.ext import commands
from utils.validators import contains_mention, remove_mention
import config

class CharacterAICog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle messages that mention the bot."""
        if message.author.bot:
            return
        
        # Check if the message mentions the bot
        user_id = self.bot.user.id
        if contains_mention(message.content, str(user_id)):
            # Extract the actual message content without the mention
            content = remove_mention(message.content, str(user_id))
            
            # Format the message with the author's name
            formatted_message = f"{message.author.name}: {content}"
            
            # Ensure Character AI is initialized
            if not self.bot.char_ai_chat or not self.bot.char_ai_chat_id:
                try:
                    await self.bot.init_character_ai()
                except Exception as e:
                    await message.channel.send(f"Failed to initialize Character AI: {e}")
                    return
            
            # Send the message to Character AI and get a response
            try:
                async with self.bot.char_ai_chat:
                    ai_message = await self.bot.char_ai_chat.send_message(
                        config.CHAR_ID, 
                        self.bot.char_ai_chat_id, 
                        formatted_message
                    )
                    await message.channel.send(f'{ai_message.text}')
            except Exception as e:
                self.bot.logger.error(f"Error sending message to Character AI: {e}")
                await message.channel.send("Sorry, I'm having trouble connecting to Character AI right now.")

async def setup(bot):
    await bot.add_cog(CharacterAICog(bot))