def format_duration(duration_ms):
    """
    Format a duration in milliseconds to a readable string.
    
    Args:
        duration_ms: Duration in milliseconds
        
    Returns:
        Formatted string like "3:45" or "1:23:45"
    """
    seconds = int(duration_ms / 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"

def create_now_playing_embed(track, position=0, replay_enabled=False):
    """
    Create an embed for the now playing command.
    
    Args:
        track: The track that is currently playing
        position: Current position in the track in milliseconds
        replay_enabled: Whether replay is enabled for this track
        
    Returns:
        A nextcord.Embed object
    """
    import nextcord
    
    duration = track.length if hasattr(track, 'length') else 0
    
    # Format strings for position and duration
    position_str = format_duration(position)
    duration_str = format_duration(duration)
    
    # Create progress bar
    bar_length = 20
    progress = position / duration if duration > 0 else 0
    filled_bars = int(bar_length * progress)
    bar = "▓" * filled_bars + "░" * (bar_length - filled_bars)
    
    # Create the embed
    embed = nextcord.Embed(
        title="Now Playing" + (" 🔄" if replay_enabled else ""),
        description=f"**{track.title}**",
        color=nextcord.Color.blue()
    )
    
    # Add track information
    embed.add_field(name="Artist", value=track.author or "Unknown", inline=True)
    embed.add_field(name="Duration", value=duration_str, inline=True)
    
    if replay_enabled:
        embed.add_field(name="Replay", value="Enabled 🔄", inline=True)
    
    # Add progress bar
    embed.add_field(
        name="Progress", 
        value=f"{position_str} {bar} {duration_str}", 
        inline=False
    )
    
    # Add thumbnail if available
    if hasattr(track, 'thumbnail'):
        embed.set_thumbnail(url=track.thumbnail)
    
    return embed