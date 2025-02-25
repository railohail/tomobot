"""
Event handlers for the Discord bot.

This module contains handlers for various Discord events such as guild joins,
errors, and other non-command interactions.
"""

import logging
import traceback
import nextcord
from nextcord.ext import commands

logger = logging.getLogger('music_bot')

class EventHandlers:
    """Handlers for various bot events."""
    
    def __init__(self, bot):
        self.bot = bot
        
        # Register event handlers
        self.register_events()
    
    def register_events(self):
        """Register all event handlers with the bot."""
        self.bot.event(self.on_command_error)
        self.bot.event(self.on_guild_join)
        self.bot.event(self.on_guild_remove)
        self.bot.event(self.on_voice_state_update)
    
    async def on_command_error(self, ctx, error):
        """Handle command errors."""
        if isinstance(error, commands.CommandNotFound):
            return
        
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument: {error.param.name}")
            return
        
        if isinstance(error, commands.BadArgument):
            await ctx.send(f"Bad argument: {error}")
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
        
        # For all other errors, log them and notify the user
        error_trace = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        logger.error(f"Command error in {ctx.command}:\n{error_trace}")
        
        await ctx.send("An error occurred while processing your command. The error has been logged.")
    
    async def on_guild_join(self, guild):
        """Handle when the bot joins a new guild."""
        logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")
        
        # Try to find a suitable channel to send a welcome message
        target_channel = None
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                target_channel = channel
                break
        
        if target_channel:
            embed = nextcord.Embed(
                title="Thanks for adding me!",
                description="I'm a music bot with character AI integration.",
                color=nextcord.Color.blue()
            )
            embed.add_field(
                name="Getting Started",
                value="Use `/play` to start playing music, and mention me for chatting!",
                inline=False
            )
            embed.add_field(
                name="Need Help?",
                value="Use `/help` to see all available commands.",
                inline=False
            )
            await target_channel.send(embed=embed)
    
    async def on_guild_remove(self, guild):
        """Handle when the bot is removed from a guild."""
        logger.info(f"Left guild: {guild.name} (ID: {guild.id})")
        
        # Clean up any stored data for this guild
        guild_id = guild.id
        
        # Clean up music queue data
        if hasattr(self.bot, 'music_queue'):
            if guild_id in self.bot.music_queue.queues:
                del self.bot.music_queue.queues[guild_id]
            if guild_id in self.bot.music_queue.locks:
                del self.bot.music_queue.locks[guild_id]
            if guild_id in self.bot.music_queue.current_songs:
                del self.bot.music_queue.current_songs[guild_id]
            if guild_id in self.bot.music_queue.play_history:
                del self.bot.music_queue.play_history[guild_id]
            if guild_id in self.bot.music_queue.text_channels:
                del self.bot.music_queue.text_channels[guild_id]
            if guild_id in self.bot.music_queue.recommendation_enabled:
                del self.bot.music_queue.recommendation_enabled[guild_id]
            if guild_id in self.bot.music_queue.recommendation_history:
                del self.bot.music_queue.recommendation_history[guild_id]
    
    async def on_voice_state_update(self, member, before, after):
        """Handle voice state changes."""
        # Auto-disconnect if the bot is left alone in a voice channel
        if member.id != self.bot.user.id:  # Not the bot's state changing
            if before.channel is not None and self.bot.user in before.channel.members:
                # Check if the bot is now alone in the voice channel
                if len([m for m in before.channel.members if not m.bot]) == 0:
                    # Find the voice client for this guild
                    voice_client = member.guild.voice_client
                    if voice_client and voice_client.is_connected():
                        # Check if there's an active player
                        is_playing = hasattr(voice_client, 'current') and voice_client.current is not None
                        
                        # Disconnect after a short delay to allow for quick reconnects
                        if not is_playing:
                            await voice_client.disconnect()
                            
                            # Send a notification if possible
                            guild_id = member.guild.id
                            if hasattr(self.bot, 'music_queue') and guild_id in self.bot.music_queue.text_channels:
                                text_channel = self.bot.music_queue.text_channels[guild_id]
                                await text_channel.send("Disconnected from voice channel because I was left alone.")