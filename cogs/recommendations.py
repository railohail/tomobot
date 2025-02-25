import nextcord
from nextcord.ext import commands
import mafic
from utils.formatters import create_now_playing_embed
import random

class RecommendationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @nextcord.slash_command(description="Toggle automatic song recommendations", dm_permission=False)
    async def recommend(self, inter: nextcord.Interaction):
        """Toggle automatic song recommendations."""
        guild_id = inter.guild_id
        new_status = self.bot.music_queue.toggle_recommendations(guild_id)
        status = "enabled" if new_status else "disabled"
        
        embed = nextcord.Embed(title="Recommendation Settings", color=nextcord.Color.blue())
        embed.add_field(name="Status", value=f"Automatic song recommendations are now {status}.", inline=False)
        
        await inter.send(embed=embed)
    
    @mafic.listen(mafic.TrackEndEvent)
    async def on_track_end_for_recommendations(self, event: mafic.TrackEndEvent):
        """Check for recommendations when a track ends."""
        player = event.player
        guild_id = player.guild.id
        
        # Check the queue size to see if we need to add recommendations
        queue_items = await self.bot.music_queue.get_queue_items(guild_id)
        if (self.bot.music_queue.get_recommendation_status(guild_id) and 
            len(queue_items) <= 1):
            await self.check_and_recommend(player, guild_id)
    
    async def check_and_recommend(self, player: mafic.Player, guild_id: int):
        """Add recommended tracks to the queue based on play history."""
        # Get recommended authors based on play history
        recommended_authors = await self.bot.music_queue.get_recommendations(guild_id, limit=10)
        if not recommended_authors:
            return
        
        recommended_tracks = 0
        added_tracks = set()  # To keep track of added tracks and avoid duplicates
        
        for author in recommended_authors:
            if recommended_tracks >= 5:  # Limit to 5 recommendations at a time
                break
            
            query = f"{author} music"
            try:
                results = await player.fetch_tracks(query, search_type=mafic.SearchType.YOUTUBE)
                if results:
                    for track in results:
                        track_id = (track.title, track.author)
                        # Check if the track is not in recommendation history and not in added_tracks
                        if (not self.bot.music_queue.is_track_in_history(guild_id, track) and
                            track_id not in added_tracks):
                            
                            # Add to queue
                            await self.bot.music_queue.add_track(guild_id, track)
                            
                            # Track that we've added this
                            added_tracks.add(track_id)
                            self.bot.music_queue.add_to_recommendation_history(guild_id, track)
                            recommended_tracks += 1
                            
                            # Send a message
                            text_channel = self.bot.music_queue.text_channels.get(guild_id)
                            if text_channel:
                                embed = nextcord.Embed(title="Recommended Track Added", color=nextcord.Color.green())
                                embed.add_field(name="Title", value=track.title, inline=False)
                                embed.add_field(name="Author", value=track.author, inline=False)
                                await text_channel.send(embed=embed)
                            break  # Move to the next author after adding one track
            except Exception as e:
                self.bot.logger.error(f"Error fetching recommendation for {author}: {e}")

async def setup(bot):
    await bot.add_cog(RecommendationCog(bot))