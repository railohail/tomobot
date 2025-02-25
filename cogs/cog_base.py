"""
Base cog class with common functionality.

This module provides a base class for cogs with common error handling and utilities.
"""

import traceback
from nextcord.ext import commands
import nextcord
import logging

logger = logging.getLogger('music_bot')

class BaseCog(commands.Cog):
    """Base cog with common error handling and utilities."""

    def __init__(self, bot):
        self.bot = bot
    
    async def cog_command_error(self, ctx, error):
        """
        Handle errors from commands in this cog.
        
        Args:
            ctx: The command context
            error: The exception raised
        """
        if isinstance(error, commands.CommandInvokeError):
            error = error.original
        
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument: `{error.param.name}`")
            return
        
        if isinstance(error, commands.BadArgument):
            await ctx.send(f"Invalid argument: {error}")
            return
        
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"Command on cooldown. Try again in {error.retry_after:.2f} seconds.")
            return
        
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have permission to use this command.")
            return
        
        if isinstance(error, commands.BotMissingPermissions):
            await ctx.send(f"I'm missing permissions to execute this command: {error.missing_perms}")
            return
        
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.send("This command cannot be used in private messages.")
            return
        
        # Log unexpected errors
        error_trace = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        logger.error(f"Error in command {ctx.command.name}:\n{error_trace}")
        
        embed = nextcord.Embed(
            title="Error",
            description="An unexpected error occurred while processing your command.", 
            color=nextcord.Color.red()
        )
        
        if isinstance(error, nextcord.HTTPException):
            embed.add_field(name="HTTP Error", value=f"Status code: {error.status}\nReason: {error.text}")
        elif isinstance(error, Exception):
            embed.add_field(name="Error Type", value=type(error).__name__)
            embed.add_field(name="Error Message", value=str(error)[:1024])
        
        await ctx.send(embed=embed)

    def user_in_voice(self, ctx):
        """
        Check if the user is in a voice channel.
        
        Args:
            ctx: The command context
            
        Returns:
            True if the user is in a voice channel, False otherwise
        """
        if not ctx.author.voice:
            return False
        return True
    
    def bot_in_voice(self, ctx):
        """
        Check if the bot is in a voice channel.
        
        Args:
            ctx: The command context
            
        Returns:
            True if the bot is in a voice channel, False otherwise
        """
        if not ctx.guild.voice_client:
            return False
        return True
    
    async def ensure_voice_connection(self, ctx):
        """
        Ensure that the bot is connected to the user's voice channel.
        
        Args:
            ctx: The command context
            
        Returns:
            The voice client if connected, None if connection failed
            
        Raises:
            commands.CheckFailure: If the user is not in a voice channel
        """
        if not self.user_in_voice(ctx):
            await ctx.send("You need to be in a voice channel to use this command.")
            return None
        
        user_voice = ctx.author.voice.channel
        
        if self.bot_in_voice(ctx):
            # Bot is in a voice channel
            voice_client = ctx.guild.voice_client
            
            # Check if the bot is in a different channel than the user
            if voice_client.channel != user_voice:
                await ctx.send("I'm already in a different voice channel. "
                              "Please join my channel or use the stop command first.")
                return None
            
            return voice_client
        else:
            # Bot is not in a voice channel, connect to the user's channel
            try:
                from mafic import Player
                return await user_voice.connect(cls=Player)
            except Exception as e:
                logger.error(f"Failed to connect to voice channel: {e}")
                await ctx.send(f"Failed to connect to voice channel: {e}")
                return None