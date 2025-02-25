import nextcord
from nextcord.ext import commands
from nextcord import SlashOption
import mafic
from utils.formatters import format_duration, create_now_playing_embed
from utils.validators import is_youtube_url
import config
import logging

class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger('music_bot')
    
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
    
    @nextcord.slash_command(description="Play music or search for tracks", dm_permission=False)
    async def play(self, inter: nextcord.Interaction, query: str):
        """Play a track or add it to the queue."""
        await self._handle_play_command(inter, query, to_front=False)
    
    @nextcord.slash_command(description="Play music or search for tracks (add to front of queue)", dm_permission=False)
    async def playnext(self, inter: nextcord.Interaction, query: str):
        """Play a track next or add it to the front of the queue."""
        await self._handle_play_command(inter, query, to_front=True)
    
    async def _handle_play_command(self, inter: nextcord.Interaction, query: str, to_front: bool = False):
        """Common handler for play and playnext commands."""
        if not inter.user.voice:
            embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
            embed.add_field(name="Message", value="You need to be in a voice channel!", inline=False)
            return await inter.send(embed=embed)
        
        if inter.guild.voice_client and inter.guild.voice_client.channel != inter.user.voice.channel:
            embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
            embed.add_field(name="Message", value="I'm already in a different voice channel. Please join my channel or use the stop command first.", inline=False)
            return await inter.send(embed=embed)
        
        # Store the text channel for later use
        self.bot.music_queue.text_channels[inter.guild_id] = inter.channel
        
        # Get or create the player
        if not inter.guild.voice_client:
            try:
                player = await inter.user.voice.channel.connect(cls=mafic.Player)
            except Exception as e:
                embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
                embed.add_field(name="Message", value=f"Failed to connect to voice channel: {str(e)}", inline=False)
                return await inter.send(embed=embed)
        else:
            player = inter.guild.voice_client
        
        # Fetch tracks
        try:
            if is_youtube_url(query):
                results = await player.fetch_tracks(query)
            else:
                results = await player.fetch_tracks(query, search_type=mafic.SearchType.YOUTUBE)
        except Exception as e:
            embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
            embed.add_field(name="Message", value=f"An error occurred while fetching tracks: {str(e)}", inline=False)
            return await inter.send(embed=embed)
        
        if not results:
            embed = nextcord.Embed(title="No Results", color=nextcord.Color.yellow())
            embed.add_field(name="Message", value="No tracks found.", inline=False)
            return await inter.send(embed=embed)
        
        # Handle playlist results
        if isinstance(results, mafic.Playlist):
            position_text = "Next in queue" if to_front else "Added to queue"
            await self.bot.music_queue.add_playlist(inter.guild_id, results.tracks, to_front)
            
            embed = nextcord.Embed(title="Playlist Added", color=nextcord.Color.green())
            embed.add_field(name="Playlist Name", value=results.name, inline=False)
            embed.add_field(name="Tracks Added", value=str(len(results.tracks)), inline=False)
            embed.add_field(name="Position", value=position_text, inline=False)
            await inter.send(embed=embed)
            
            # Start playing if nothing is playing
            if inter.guild_id not in self.bot.music_queue.current_songs:
                await self._play_next(player)
        
        # Handle direct URLs or single result
        elif is_youtube_url(query) or len(results) == 1:
            track = results[0]
            await self.bot.music_queue.add_track(inter.guild_id, track, to_front)
            
            position_text = "Next in queue" if to_front else "Added to queue"
            embed = nextcord.Embed(title="Track Added", color=nextcord.Color.green())
            embed.add_field(name="Title", value=track.title, inline=False)
            embed.add_field(name="Author", value=track.author, inline=False)
            embed.add_field(name="Position", value=position_text, inline=False)
            await inter.send(embed=embed)
            
            # Start playing if nothing is playing
            if inter.guild_id not in self.bot.music_queue.current_songs:
                await self._play_next(player)
        
        # Handle multiple results with selection menu
        else:
            options = [
                nextcord.SelectOption(
                    label=f"{i+1}. {track.title[:50]}", 
                    description=f"By {track.author[:50]}", 
                    value=str(i)
                ) 
                for i, track in enumerate(results[:10])
            ]
            
            select = nextcord.ui.Select(placeholder="Choose a track...", options=options)
            
            async def select_callback(interaction: nextcord.Interaction):
                selected_index = int(select.values[0])
                selected_track = results[selected_index]
                await self.bot.music_queue.add_track(interaction.guild_id, selected_track, to_front)
                
                position_text = "Next in queue" if to_front else "Added to queue"
                embed = nextcord.Embed(title="Track Added", color=nextcord.Color.green())
                embed.add_field(name="Title", value=selected_track.title, inline=False)
                embed.add_field(name="Author", value=selected_track.author, inline=False)
                embed.add_field(name="Position", value=position_text, inline=False)
                await interaction.response.send_message(embed=embed)
                
                # Start playing if nothing is playing
                if interaction.guild_id not in self.bot.music_queue.current_songs:
                    await self._play_next(player)
            
            select.callback = select_callback
            view = nextcord.ui.View(timeout=60)
            view.add_item(select)
            
            async def on_timeout():
                # Check if the player is still in use
                if player.connected and not player.current:
                    guild_id = inter.guild_id
                    queue_items = await self.bot.music_queue.get_queue_items(guild_id)
                    if not queue_items:
                        await player.disconnect()
                        text_channel = self.bot.music_queue.text_channels.get(guild_id)
                        if text_channel:
                            await text_channel.send("Search timed out. Disconnected from the voice channel.")
            
            view.on_timeout = on_timeout
            
            embed = nextcord.Embed(title="Track Selection", color=nextcord.Color.blue())
            embed.add_field(name="Action", value="Please select a track to add to the queue:", inline=False)
            await inter.send(embed=embed, view=view)
    
    @nextcord.slash_command(description="Stop the music and clear the queue", dm_permission=False)
    async def stop(self, inter: nextcord.Interaction):
        """Stop the music, clear the queue, and disconnect."""
        if not inter.guild.voice_client or not isinstance(inter.guild.voice_client, mafic.Player):
            embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
            embed.add_field(name="Message", value="I'm not playing anything right now.", inline=False)
            return await inter.send(embed=embed)
        
        player = inter.guild.voice_client
        if player.connected:
            await self.bot.music_queue.clear_queue(inter.guild_id)
            self.bot.music_queue.clear_current_song(inter.guild_id)
            # Also clear the replay mode
            if hasattr(self.bot.music_queue, 'replay_enabled'):
                self.bot.music_queue.set_replay_status(inter.guild_id, False)
            await player.stop()
            await player.disconnect()
            
            embed = nextcord.Embed(title="Playback Stopped", color=nextcord.Color.blue())
            embed.add_field(name="Action", value="Stopped the music, cleared the queue, and disconnected from the voice channel.", inline=False)
            
            await inter.send(embed=embed)
        else:
            embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
            embed.add_field(name="Message", value="The player is not connected to a voice channel.", inline=False)
            await inter.send(embed=embed)
    
    @nextcord.slash_command(description="Pause the current track", dm_permission=False)
    async def pause(self, inter: nextcord.Interaction):
        """Pause the current track."""
        if not inter.guild.voice_client or not isinstance(inter.guild.voice_client, mafic.Player):
            return await inter.send("I'm not playing anything right now.")
        
        player = inter.guild.voice_client
        if player.connected and player.current:
            if player.paused:
                return await inter.send("The player is already paused.")
            await player.pause()
            await inter.send("Paused the current track.")
        else:
            await inter.send("Unable to pause. No track is currently playing.")
    
    @nextcord.slash_command(description="Resume the paused track", dm_permission=False)
    async def resume(self, inter: nextcord.Interaction):
        """Resume the paused track."""
        if not inter.guild.voice_client or not isinstance(inter.guild.voice_client, mafic.Player):
            return await inter.send("I'm not playing anything right now.")
        
        player = inter.guild.voice_client
        if player.connected and player.current:
            if not player.paused:
                return await inter.send("The player is not paused.")
            await player.resume()
            await inter.send("Resumed the current track.")
        else:
            await inter.send("Unable to resume. No track is currently playing.")
    
    @nextcord.slash_command(description="Skip the current track", dm_permission=False)
    async def skip(self, inter: nextcord.Interaction):
        """Skip the current track."""
        if not inter.guild.voice_client or not isinstance(inter.guild.voice_client, mafic.Player):
            return await inter.send("I'm not playing anything right now.")
        
        player = inter.guild.voice_client
        if player.current:
            # Get the current song before skipping
            current_song = self.bot.music_queue.get_current_song(inter.guild_id)
            
            # Get replay status (we don't disable it, just skipping the current iteration)
            replay_enabled = False
            if hasattr(self.bot.music_queue, 'replay_enabled'):
                replay_enabled = self.bot.music_queue.get_replay_status(inter.guild_id)
            
            # Skip the song
            await player.stop()
            
            # Prepare response based on replay status
            if replay_enabled:
                message = f"Skipped **{current_song.title}** (Replay mode is still enabled 🔄)"
            else:
                message = f"Skipped **{current_song.title}**"
            
            await inter.send(message)
        else:
            await inter.send("No track is currently playing.")
    
    @nextcord.slash_command(description="Show the current queue", dm_permission=False)
    async def queue(self, inter: nextcord.Interaction):
        """Show the current queue."""
        queue_items = await self.bot.music_queue.get_queue_items(inter.guild_id)
        current_track = self.bot.music_queue.current_songs.get(inter.guild_id)
        
        if not queue_items and not current_track:
            return await inter.send("The queue is empty and no song is currently playing.")
        
        embed = nextcord.Embed(title="Current Queue", color=nextcord.Color.blue())
        
        # Add current track information
        if current_track:
            player = inter.guild.voice_client
            if player and isinstance(player, mafic.Player):
                current_position = format_duration(player.position)
                current_duration = format_duration(current_track.length)
                
                # Check if replay is enabled
                replay_status = ""
                if hasattr(self.bot.music_queue, 'replay_enabled'):
                    if self.bot.music_queue.get_replay_status(inter.guild_id):
                        replay_status = " 🔄"
                
                embed.add_field(name=f"Now Playing{replay_status}", 
                               value=f"{current_track.title} - {current_track.author}\n"
                                     f"Duration: {current_position} / {current_duration}", inline=False)
        
        # Add queued tracks
        track_list = []
        total_duration = 0
        for i, track in enumerate(queue_items):
            duration = format_duration(track.length)
            if i < 10:  # Show only first 10 tracks
                track_list.append(f"{i+1}. {track.title} - {track.author} ({duration})")
            total_duration += track.length
        
        if track_list:
            embed.add_field(name="Next in Queue", value="\n".join(track_list), inline=False)
            if len(queue_items) > 10:
                embed.add_field(name="", value=f"And {len(queue_items) - 10} more...", inline=False)
        else:
            embed.add_field(name="Next in Queue", value="No tracks in queue", inline=False)
        
        # Add total queue information
        total_tracks = len(queue_items)
        total_duration_formatted = format_duration(total_duration)
        embed.add_field(name="Queue Info", value=f"Total tracks in queue: {total_tracks}\n"
                                                f"Total duration of queue: {total_duration_formatted}", inline=False)
        
        await inter.send(embed=embed)
    
    @nextcord.slash_command(description="Shuffle the current queue", dm_permission=False)
    async def shuffle(self, inter: nextcord.Interaction):
        """Shuffle the current queue."""
        queue_items = await self.bot.music_queue.get_queue_items(inter.guild_id)
        if len(queue_items) < 2:
            return await inter.send("The queue needs at least two tracks to shuffle.")
        
        await self.bot.music_queue.shuffle_queue(inter.guild_id)
        
        # Get the updated queue
        shuffled_queue = await self.bot.music_queue.get_queue_items(inter.guild_id)
        
        # Create an embed to display the shuffled queue
        embed = nextcord.Embed(title="Queue Shuffled", color=nextcord.Color.green())
        
        # Display the current track (if any) and the first 10 tracks of the shuffled queue
        track_list = []
        current_track = self.bot.music_queue.current_songs.get(inter.guild_id)
        if current_track:
            # Check if replay is enabled
            replay_status = ""
            if hasattr(self.bot.music_queue, 'replay_enabled'):
                if self.bot.music_queue.get_replay_status(inter.guild_id):
                    replay_status = " 🔄"
            
            track_list.append(f"Currently playing{replay_status}: {current_track.title} - {current_track.author}")
        
        for i, track in enumerate(shuffled_queue):
            if i < 10:  # Show up to 10 tracks from the queue
                duration = format_duration(track.length)
                track_list.append(f"{i+1}. {track.title} - {track.author} ({duration})")
            else:
                break
        
        if track_list:
            embed.add_field(name="Current Track and Queue", value="\n".join(track_list), inline=False)
            if len(shuffled_queue) > 10:
                embed.add_field(name="", value=f"And {len(shuffled_queue) - 10} more...", inline=False)
        
        total_tracks = len(shuffled_queue) + (1 if current_track else 0)
        embed.add_field(name="Queue Info", value=f"Total tracks: {total_tracks}\n"
                                                f"Tracks shuffled: {len(shuffled_queue)}", inline=False)
        
        await inter.send(embed=embed)
    
    @nextcord.slash_command(description="Clear the queue without stopping the current track", dm_permission=False)
    async def clear(self, inter: nextcord.Interaction):
        """Clear the queue without stopping the current track."""
        queue_items = await self.bot.music_queue.get_queue_items(inter.guild_id)
        if not queue_items:
            embed = nextcord.Embed(title="Queue Status", color=nextcord.Color.blue())
            embed.add_field(name="Message", value="The queue is already empty.", inline=False)
            return await inter.send(embed=embed)
        
        await self.bot.music_queue.clear_queue(inter.guild_id)
        
        embed = nextcord.Embed(title="Queue Cleared", color=nextcord.Color.green())
        embed.add_field(name="Action", value="Cleared the queue. The current track (if any) will continue playing.", inline=False)
        
        await inter.send(embed=embed)
    
    @nextcord.slash_command(description="Set the volume of the player", dm_permission=False)
    async def volume(self, inter: nextcord.Interaction, volume: int = SlashOption(description="Volume level (0-1000)", required=True)):
        """Set the volume of the player."""
        if not inter.guild.voice_client or not isinstance(inter.guild.voice_client, mafic.Player):
            return await inter.send("I'm not playing anything right now.")
        
        player = inter.guild.voice_client
        if 0 <= volume <= 1000:
            await player.set_volume(volume)
            await inter.send(f"Set the volume to {volume}%")
        else:
            await inter.send("Volume must be between 0 and 1000")
    
    @nextcord.slash_command(description="Show information about the currently playing track", dm_permission=False)
    async def now_playing(self, inter: nextcord.Interaction):
        """Show information about the currently playing track."""
        if not inter.guild.voice_client or not isinstance(inter.guild.voice_client, mafic.Player):
            return await inter.send("I'm not playing anything right now.")
        
        player = inter.guild.voice_client
        if not player.current:
            return await inter.send("No track is currently playing.")
        
        # Check if replay is enabled
        replay_enabled = False
        if hasattr(self.bot.music_queue, 'replay_enabled'):
            replay_enabled = self.bot.music_queue.get_replay_status(inter.guild_id)
        
        embed = create_now_playing_embed(player.current, player.position, replay_enabled)
        await inter.send(embed=embed)
    
    @nextcord.slash_command(description="Toggle replay mode for the current song", dm_permission=False)
    async def replay(self, inter: nextcord.Interaction):
        """Toggle replay mode for the current song."""
        if not inter.guild.voice_client or not isinstance(inter.guild.voice_client, mafic.Player):
            embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
            embed.add_field(name="Message", value="I'm not currently in a voice channel.", inline=False)
            return await inter.send(embed=embed)
        
        player = inter.guild.voice_client
        if not player.current:
            embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
            embed.add_field(name="Message", value="No song is currently playing.", inline=False)
            return await inter.send(embed=embed)
        
        # Make sure replay_enabled dict exists
        if not hasattr(self.bot.music_queue, 'replay_enabled'):
            self.bot.music_queue.replay_enabled = {}
        
        # Toggle replay mode
        current_status = self.bot.music_queue.get_replay_status(inter.guild_id)
        self.bot.music_queue.set_replay_status(inter.guild_id, not current_status)
        new_status = not current_status
        
        # Send response
        if new_status:
            embed = nextcord.Embed(
                title="🔄 Replay Mode Enabled",
                description=f"**{player.current.title}** will now replay continuously.",
                color=nextcord.Color.green()
            )
        else:
            embed = nextcord.Embed(
                title="▶️ Replay Mode Disabled",
                description="Songs will now play normally.",
                color=nextcord.Color.blue()
            )
        
        await inter.send(embed=embed)
    
    @nextcord.slash_command(description="Delete a specific track from the queue", dm_permission=False)
    async def delete_from_queue(self, inter: nextcord.Interaction):
        """Delete a specific track from the queue."""
        queue_items = await self.bot.music_queue.get_queue_items(inter.guild_id)
        if not queue_items:
            return await inter.send("The queue is empty.")
        
        options = [
            nextcord.SelectOption(
                label=f"{i+1}. {track.title[:50]}",
                description=f"By {track.author[:50]}",
                value=str(i)
            ) for i, track in enumerate(queue_items[:25])  # Discord has a limit of 25 options
        ]
        
        if len(queue_items) > 25:
            await inter.send("Only showing the first 25 tracks due to Discord limitations.")
        
        select = nextcord.ui.Select(
            placeholder="Choose a track to delete...",
            options=options
        )
        
        async def select_callback(interaction: nextcord.Interaction):
            selected_index = int(select.values[0])
            deleted_track = await self.bot.music_queue.remove_track(interaction.guild_id, selected_index)
            if deleted_track:
                await interaction.response.send_message(f"Removed '{deleted_track.title}' from the queue.")
            else:
                await interaction.response.send_message("Failed to remove the track. It may have been removed already.")
        
        select.callback = select_callback
        view = nextcord.ui.View(timeout=60)
        view.add_item(select)
        
        await inter.send("Select a track to remove from the queue:", view=view)
        
        async def on_timeout():
            await inter.edit_original_message(content="The selection timed out.", view=None)
        
        view.on_timeout = on_timeout
    
    @mafic.listen(mafic.TrackStartEvent)
    async def on_track_start(self, event: mafic.TrackStartEvent):
        """Handle track start events."""
        player = event.player
        track = event.track
        guild_id = player.guild.id
        
        # Store the current song
        self.bot.music_queue.set_current_song(guild_id, track)
        
        # Send now playing message
        text_channel = self.bot.music_queue.text_channels.get(guild_id)
        if text_channel:
            # Check if replay is enabled for now playing message
            replay_enabled = False
            if hasattr(self.bot.music_queue, 'replay_enabled'):
                replay_enabled = self.bot.music_queue.get_replay_status(guild_id)
            
            embed = create_now_playing_embed(track, replay_enabled=replay_enabled)
            await text_channel.send(embed=embed)
    
    @mafic.listen(mafic.TrackEndEvent)
    async def on_track_end(self, event: mafic.TrackEndEvent):
        """Handle track end events."""
        player = event.player
        guild_id = player.guild.id
        
        # Check if replay is enabled before clearing the current song
        replay_enabled = False
        current_song = self.bot.music_queue.get_current_song(guild_id)
        
        if hasattr(self.bot.music_queue, 'replay_enabled'):
            replay_enabled = self.bot.music_queue.get_replay_status(guild_id)
        
        if replay_enabled and current_song:
            # If replay is enabled, we'll replay the current song
            self.logger.info(f"Replay mode enabled, replaying '{current_song.title}' in guild {guild_id}")
            
            try:
                # Get the same track again to replay
                search_query = f"{current_song.title} {current_song.author}"
                results = await player.fetch_tracks(search_query, search_type=mafic.SearchType.YOUTUBE)
                
                if results and len(results) > 0:
                    # Use the first track to replay
                    replay_track = results[0]
                    await player.play(replay_track)
                    self.bot.music_queue.set_current_song(guild_id, replay_track)
                    return  # Return early since we're replaying
                else:
                    self.logger.warning(f"Failed to find track for replay: {current_song.title}")
                    # If we can't find the track, we'll proceed to normal playback
            except Exception as e:
                self.logger.error(f"Error replaying track: {e}")
                # If replaying fails, we'll proceed to normal playback
        
        # Normal end track behavior if not replaying
        self.bot.music_queue.clear_current_song(guild_id)
        await self._play_next(player)
    
    async def _play_next(self, player: mafic.Player):
        """Play the next track in the queue."""
        guild_id = player.guild.id
        if not player.connected:
            await self.bot.music_queue.clear_queue(guild_id)
            return
        
        next_track = await self.bot.music_queue.get_next_track(guild_id)
        if next_track:
            try:
                await player.play(next_track)
                self.bot.music_queue.set_current_song(guild_id, next_track)
                self.logger.info(f"Started playing: {next_track.title}")
            except Exception as e:
                self.logger.error(f"Error playing track: {e}")
                text_channel = self.bot.music_queue.text_channels.get(guild_id)
                if text_channel:
                    embed = nextcord.Embed(title="Playback Error", color=nextcord.Color.red())
                    embed.add_field(name="Error", value=f"Error playing track: {e}", inline=False)
                    await text_channel.send(embed=embed)
                
                # Try to play the next track
                await self._play_next(player)
        else:
            text_channel = self.bot.music_queue.text_channels.get(guild_id)
            if text_channel:
                embed = nextcord.Embed(title="Playback Finished", color=nextcord.Color.blue())
                embed.add_field(name="Message", value="Queue is empty. Playback finished.", inline=False)
                await text_channel.send(embed=embed)
            
            await player.disconnect()

async def setup(bot):
    await bot.add_cog(MusicCog(bot))