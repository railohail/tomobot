"""
Thread-safe music queue management.

This module provides a thread-safe implementation of a music queue system
that supports multiple guilds, play history tracking, and recommendation features.
"""

from collections import deque
from typing import Dict, Any, Optional, List, Tuple, Set, Callable
import random
from collections import Counter
from utils.locks import LockManager
import logging

logger = logging.getLogger('music_bot')

class MusicQueue:
    """
    Thread-safe music queue manager supporting multiple guilds.
    
    This class manages queues of tracks for different guilds, with additional
    features like play history tracking, recommendations, and thread safety.
    """
    
    def __init__(self, max_history_size: int = 100):
        """
        Initialize the MusicQueue.
        
        Args:
            max_history_size: Maximum number of items to keep in history
        """
        self.queues = {}  # guild_id -> deque of tracks
        self.lock_manager = LockManager()
        self.current_songs = {}  # guild_id -> current Track
        self.play_history = {}  # guild_id -> list of author names
        self.text_channels = {}  # guild_id -> text channel
        self.recommendation_enabled = {}  # guild_id -> bool
        self.recommendation_history = {}  # guild_id -> deque of (title, author) tuples
        self.replay_enabled = {}  # guild_id -> bool (NEW)
        self.max_history_size = max_history_size
    
    async def add_track(self, guild_id: int, track, to_front: bool = False) -> None:
        """
        Add a track to the queue with thread safety.
        
        Args:
            guild_id: The guild ID to add the track for
            track: The track object to add
            to_front: If True, add to the front of the queue
        """
        await self.lock_manager.with_lock(guild_id, self._add_track, guild_id, track, to_front)
    
    async def _add_track(self, guild_id: int, track, to_front: bool) -> None:
        """
        Internal method to add a track to the queue.
        
        Args:
            guild_id: The guild ID to add the track for
            track: The track object to add
            to_front: If True, add to the front of the queue
        """
        if guild_id not in self.queues:
            self.queues[guild_id] = deque()
        
        if to_front:
            self.queues[guild_id].appendleft(track)
        else:
            self.queues[guild_id].append(track)
    
    async def add_playlist(self, guild_id: int, tracks, to_front: bool = False) -> None:
        """
        Add multiple tracks to the queue with thread safety.
        
        Args:
            guild_id: The guild ID to add the tracks for
            tracks: List of track objects to add
            to_front: If True, add to the front of the queue
        """
        await self.lock_manager.with_lock(guild_id, self._add_playlist, guild_id, tracks, to_front)
    
    async def _add_playlist(self, guild_id: int, tracks, to_front: bool) -> None:
        """
        Internal method to add multiple tracks to the queue.
        
        Args:
            guild_id: The guild ID to add the tracks for
            tracks: List of track objects to add
            to_front: If True, add to the front of the queue
        """
        if guild_id not in self.queues:
            self.queues[guild_id] = deque()
        
        if to_front:
            # When adding to front, we need to maintain the original order
            # So we add them in reverse order to the front
            for track in reversed(tracks):
                self.queues[guild_id].appendleft(track)
        else:
            for track in tracks:
                self.queues[guild_id].append(track)
    
    async def get_next_track(self, guild_id: int) -> Optional[Any]:
        """
        Get and remove the next track from the queue.
        
        Args:
            guild_id: The guild ID to get the track for
            
        Returns:
            The next track, or None if the queue is empty
        """
        return await self.lock_manager.with_lock(guild_id, self._get_next_track, guild_id)
    
    async def _get_next_track(self, guild_id: int) -> Optional[Any]:
        """
        Internal method to get the next track.
        
        Args:
            guild_id: The guild ID to get the track for
            
        Returns:
            The next track, or None if the queue is empty
        """
        if guild_id not in self.queues or not self.queues[guild_id]:
            return None
        return self.queues[guild_id].popleft()
    
    async def peek_queue(self, guild_id: int, index: int = 0) -> Optional[Any]:
        """
        Peek at a track in the queue without removing it.
        
        Args:
            guild_id: The guild ID to peek at the queue for
            index: The index of the track to peek at (default: 0 for next track)
            
        Returns:
            The track at the specified position, or None if the index is invalid
        """
        return await self.lock_manager.with_lock(guild_id, self._peek_queue, guild_id, index)
    
    async def _peek_queue(self, guild_id: int, index: int) -> Optional[Any]:
        """
        Internal method to peek at a track in the queue.
        
        Args:
            guild_id: The guild ID to peek at the queue for
            index: The index of the track to peek at
            
        Returns:
            The track at the specified position, or None if the index is invalid
        """
        if guild_id not in self.queues or not self.queues[guild_id] or index >= len(self.queues[guild_id]):
            return None
        
        queue_list = list(self.queues[guild_id])
        return queue_list[index]
    
    async def clear_queue(self, guild_id: int) -> None:
        """
        Clear the queue for the specified guild.
        
        Args:
            guild_id: The guild ID to clear the queue for
        """
        await self.lock_manager.with_lock(guild_id, self._clear_queue, guild_id)
    
    async def _clear_queue(self, guild_id: int) -> None:
        """
        Internal method to clear the queue.
        
        Args:
            guild_id: The guild ID to clear the queue for
        """
        if guild_id in self.queues:
            self.queues[guild_id].clear()
    
    async def remove_track(self, guild_id: int, index: int) -> Optional[Any]:
        """
        Remove a track at a specific index.
        
        Args:
            guild_id: The guild ID to remove the track for
            index: The index of the track to remove
            
        Returns:
            The removed track, or None if the index is invalid
        """
        return await self.lock_manager.with_lock(guild_id, self._remove_track, guild_id, index)
    
    async def _remove_track(self, guild_id: int, index: int) -> Optional[Any]:
        """
        Internal method to remove a track at a specific index.
        
        Args:
            guild_id: The guild ID to remove the track for
            index: The index of the track to remove
            
        Returns:
            The removed track, or None if the index is invalid
        """
        if guild_id not in self.queues or not self.queues[guild_id] or index >= len(self.queues[guild_id]):
            return None
        
        # Convert to list, remove item, convert back to deque
        queue_list = list(self.queues[guild_id])
        removed_track = queue_list.pop(index)
        self.queues[guild_id] = deque(queue_list)
        return removed_track
    
    async def move_track(self, guild_id: int, old_index: int, new_index: int) -> bool:
        """
        Move a track from one position to another in the queue.
        
        Args:
            guild_id: The guild ID to move the track for
            old_index: The current index of the track
            new_index: The index to move the track to
            
        Returns:
            True if the track was moved, False if the indices are invalid
        """
        return await self.lock_manager.with_lock(guild_id, self._move_track, guild_id, old_index, new_index)
    
    async def _move_track(self, guild_id: int, old_index: int, new_index: int) -> bool:
        """
        Internal method to move a track in the queue.
        
        Args:
            guild_id: The guild ID to move the track for
            old_index: The current index of the track
            new_index: The index to move the track to
            
        Returns:
            True if the track was moved, False if the indices are invalid
        """
        if guild_id not in self.queues:
            return False
        
        queue_list = list(self.queues[guild_id])
        
        if old_index < 0 or old_index >= len(queue_list) or new_index < 0 or new_index >= len(queue_list):
            return False
        
        # Remove the track from the old position
        track = queue_list.pop(old_index)
        
        # Insert the track at the new position
        queue_list.insert(new_index, track)
        
        # Update the queue
        self.queues[guild_id] = deque(queue_list)
        return True
    
    async def shuffle_queue(self, guild_id: int) -> bool:
        """
        Shuffle the queue for the specified guild.
        
        Args:
            guild_id: The guild ID to shuffle the queue for
            
        Returns:
            True if the queue was shuffled, False if there weren't enough tracks to shuffle
        """
        return await self.lock_manager.with_lock(guild_id, self._shuffle_queue, guild_id)
    
    async def _shuffle_queue(self, guild_id: int) -> bool:
        """
        Internal method to shuffle the queue.
        
        Args:
            guild_id: The guild ID to shuffle the queue for
            
        Returns:
            True if the queue was shuffled, False if there weren't enough tracks to shuffle
        """
        if guild_id not in self.queues or len(self.queues[guild_id]) < 2:
            return False
        
        queue_list = list(self.queues[guild_id])
        random.shuffle(queue_list)
        self.queues[guild_id] = deque(queue_list)
        return True
    
    async def get_queue_items(self, guild_id: int) -> List[Any]:
        """
        Get all items in the queue.
        
        Args:
            guild_id: The guild ID to get the queue for
            
        Returns:
            A list of all tracks in the queue
        """
        return await self.lock_manager.with_lock(guild_id, self._get_queue_items, guild_id)
    
    async def _get_queue_items(self, guild_id: int) -> List[Any]:
        """
        Internal method to get all items in the queue.
        
        Args:
            guild_id: The guild ID to get the queue for
            
        Returns:
            A list of all tracks in the queue
        """
        if guild_id not in self.queues:
            return []
        return list(self.queues[guild_id])
    
    async def get_queue_length(self, guild_id: int) -> int:
        """
        Get the number of items in the queue.
        
        Args:
            guild_id: The guild ID to get the queue length for
            
        Returns:
            The number of tracks in the queue
        """
        return await self.lock_manager.with_lock(guild_id, self._get_queue_length, guild_id)
    
    async def _get_queue_length(self, guild_id: int) -> int:
        """
        Internal method to get the number of items in the queue.
        
        Args:
            guild_id: The guild ID to get the queue length for
            
        Returns:
            The number of tracks in the queue
        """
        if guild_id not in self.queues:
            return 0
        return len(self.queues[guild_id])
    
    async def get_total_duration(self, guild_id: int) -> int:
        """
        Get the total duration of all tracks in the queue.
        
        Args:
            guild_id: The guild ID to get the duration for
            
        Returns:
            Total duration in milliseconds
        """
        return await self.lock_manager.with_lock(guild_id, self._get_total_duration, guild_id)
    
    async def _get_total_duration(self, guild_id: int) -> int:
        """
        Internal method to get the total duration of all tracks in the queue.
        
        Args:
            guild_id: The guild ID to get the duration for
            
        Returns:
            Total duration in milliseconds
        """
        if guild_id not in self.queues:
            return 0
        
        total = 0
        for track in self.queues[guild_id]:
            if hasattr(track, 'length'):
                total += track.length
        
        return total
    
    async def find_track_index(self, guild_id: int, predicate: Callable) -> int:
        """
        Find the index of a track in the queue based on a predicate function.
        
        Args:
            guild_id: The guild ID to search the queue for
            predicate: A function that takes a track and returns True if it matches
            
        Returns:
            The index of the track, or -1 if not found
        """
        return await self.lock_manager.with_lock(guild_id, self._find_track_index, guild_id, predicate)
    
    async def _find_track_index(self, guild_id: int, predicate: Callable) -> int:
        """
        Internal method to find the index of a track in the queue.
        
        Args:
            guild_id: The guild ID to search the queue for
            predicate: A function that takes a track and returns True if it matches
            
        Returns:
            The index of the track, or -1 if not found
        """
        if guild_id not in self.queues:
            return -1
        
        for i, track in enumerate(self.queues[guild_id]):
            if predicate(track):
                return i
        
        return -1
    
    def set_current_song(self, guild_id: int, track) -> None:
        """
        Set the current playing song for a guild.
        
        Args:
            guild_id: The guild ID to set the current song for
            track: The track that is currently playing
        """
        self.current_songs[guild_id] = track
        
        # Update play history if the track has an author
        if track and hasattr(track, 'author') and track.author:
            if guild_id not in self.play_history:
                self.play_history[guild_id] = []
            
            self.play_history[guild_id].append(track.author)
            
            # Keep only the last max_history_size played tracks
            if len(self.play_history[guild_id]) > self.max_history_size:
                self.play_history[guild_id] = self.play_history[guild_id][-self.max_history_size:]
            
            logger.debug(f"Updated play history for guild {guild_id}, artist: {track.author}")
    
    def add_to_play_history(self, guild_id: int, author: str) -> None:
        """
        Explicitly add an author to the play history.
        
        This is useful when you want to add history data without setting a current song.
        
        Args:
            guild_id: The guild ID to add the history for
            author: The author name to add to the history
        """
        if guild_id not in self.play_history:
            self.play_history[guild_id] = []
        
        self.play_history[guild_id].append(author)
        
        # Keep only the last max_history_size played tracks
        if len(self.play_history[guild_id]) > self.max_history_size:
            self.play_history[guild_id] = self.play_history[guild_id][-self.max_history_size:]
    
    def get_play_history(self, guild_id: int, limit: int = None) -> List[str]:
        """
        Get the play history for a guild.
        
        Args:
            guild_id: The guild ID to get the history for
            limit: Maximum number of history items to return (None for all)
            
        Returns:
            A list of author names in the play history
        """
        if guild_id not in self.play_history:
            return []
        
        history = self.play_history[guild_id]
        if limit is not None:
            history = history[-limit:]
        
        return history.copy()
    
    def clear_current_song(self, guild_id: int) -> None:
        """
        Clear the current song for a guild.
        
        Args:
            guild_id: The guild ID to clear the current song for
        """
        if guild_id in self.current_songs:
            del self.current_songs[guild_id]
    
    def get_current_song(self, guild_id: int) -> Optional[Any]:
        """
        Get the current playing song for a guild.
        
        Args:
            guild_id: The guild ID to get the current song for
            
        Returns:
            The currently playing track, or None if nothing is playing
        """
        return self.current_songs.get(guild_id)
    
    async def get_recommendations(self, guild_id: int, limit: int = 5) -> List[str]:
        """
        Get author recommendations based on play history.
        
        Args:
            guild_id: The guild ID to get recommendations for
            limit: Maximum number of recommendations to return
            
        Returns:
            A list of recommended author names
        """
        return await self.lock_manager.with_lock(guild_id, self._get_recommendations, guild_id, limit)
    
    async def _get_recommendations(self, guild_id: int, limit: int) -> List[str]:
        """
        Internal method to get author recommendations based on play history.
        
        Args:
            guild_id: The guild ID to get recommendations for
            limit: Maximum number of recommendations to return
            
        Returns:
            A list of recommended author names
        """
        if guild_id not in self.play_history or not self.play_history[guild_id]:
            return []
        
        # Count occurrences of each author and get the most common ones
        author_counts = Counter(self.play_history[guild_id])
        common_authors = [author for author, _ in author_counts.most_common()]
        
        # Randomly select authors (or all if less than the limit)
        num_authors = min(limit, len(common_authors))
        if num_authors > 0:
            return random.sample(common_authors, num_authors)
        return []
    
    def is_track_in_history(self, guild_id: int, track) -> bool:
        """
        Check if a track is in the recommendation history.
        
        Args:
            guild_id: The guild ID to check the history for
            track: The track to check
            
        Returns:
            True if the track is in the history, False otherwise
        """
        if guild_id not in self.recommendation_history:
            return False
        
        # Create a unique identifier for the track
        track_id = self._create_track_id(track)
        return track_id in self.recommendation_history[guild_id]
    
    def add_to_recommendation_history(self, guild_id: int, track) -> None:
        """
        Add a track to the recommendation history.
        
        Args:
            guild_id: The guild ID to add the track for
            track: The track to add to the history
        """
        if guild_id not in self.recommendation_history:
            self.recommendation_history[guild_id] = deque(maxlen=self.max_history_size)
        
        # Create a unique identifier for the track
        track_id = self._create_track_id(track)
        self.recommendation_history[guild_id].append(track_id)
    
    def _create_track_id(self, track) -> Tuple[str, str]:
        """
        Create a unique identifier for a track.
        
        Args:
            track: The track to create an ID for
            
        Returns:
            A tuple of (title, author) that serves as a unique ID
        """
        # Safely get attributes with fallbacks for missing fields
        title = ""
        author = ""
        
        if hasattr(track, 'title'):
            title = track.title
        elif hasattr(track, 'name'):  # Some APIs use name instead of title
            title = track.name
        elif hasattr(track, 'info') and 'title' in track.info:  # Some wrap in info dict
            title = track.info['title']
        
        if hasattr(track, 'author'):
            author = track.author
        elif hasattr(track, 'artist'):  # Some APIs use artist instead of author
            author = track.artist
        elif hasattr(track, 'info') and 'author' in track.info:
            author = track.info['author']
        
        return (str(title), str(author))  # Ensure strings even if attributes have unexpected types
    
    def toggle_recommendations(self, guild_id: int) -> bool:
        """
        Toggle recommendations for a guild.
        
        Args:
            guild_id: The guild ID to toggle recommendations for
            
        Returns:
            The new recommendation status (True if enabled, False if disabled)
        """
        current_value = self.recommendation_enabled.get(guild_id, False)
        self.recommendation_enabled[guild_id] = not current_value
        return self.recommendation_enabled[guild_id]
    
    def get_recommendation_status(self, guild_id: int) -> bool:
        """
        Get the current recommendation status.
        
        Args:
            guild_id: The guild ID to get the status for
            
        Returns:
            True if recommendations are enabled, False otherwise
        """
        return self.recommendation_enabled.get(guild_id, False)
    
    def set_text_channel(self, guild_id: int, channel) -> None:
        """
        Set the text channel for a guild.
        
        Args:
            guild_id: The guild ID to set the channel for
            channel: The channel to set
        """
        self.text_channels[guild_id] = channel
    
    def get_text_channel(self, guild_id: int) -> Optional[Any]:
        """
        Get the text channel for a guild.
        
        Args:
            guild_id: The guild ID to get the channel for
            
        Returns:
            The text channel, or None if not set
        """
        return self.text_channels.get(guild_id)
    def set_replay_status(self, guild_id: int, enabled: bool) -> None:
        """
        Set the replay status for a guild.
        
        Args:
            guild_id: The guild ID to set the status for
            enabled: Whether to enable replay
        """
        if not hasattr(self, 'replay_enabled'):
            self.replay_enabled = {}
        
        self.replay_enabled[guild_id] = enabled
        logger.info(f"Replay mode set to {enabled} for guild {guild_id}")

    def get_replay_status(self, guild_id: int) -> bool:
        """
        Get the replay status for a guild.
        
        Args:
            guild_id: The guild ID to get the status for
            
        Returns:
            True if replay is enabled, False otherwise
        """
        if not hasattr(self, 'replay_enabled'):
            self.replay_enabled = {}
        
        return self.replay_enabled.get(guild_id, False)

    def toggle_replay(self, guild_id: int) -> bool:
        """
        Toggle replay mode for a guild.
        
        Args:
            guild_id: The guild ID to toggle replay for
            
        Returns:
            The new replay status
        """
        current_status = self.get_replay_status(guild_id)
        self.set_replay_status(guild_id, not current_status)
        return not current_status
    async def cleanup_guild(self, guild_id: int) -> None:
        """
        Clean up all data for a guild.
        
        Args:
            guild_id: The guild ID to clean up data for
        """
        # Lock first to ensure no other operations are in progress
        await self.lock_manager.with_lock(guild_id, self._cleanup_guild, guild_id)
    
    async def _cleanup_guild(self, guild_id: int) -> None:
        """
        Internal method to clean up all data for a guild.
        
        Args:
            guild_id: The guild ID to clean up data for
        """
        if guild_id in self.queues:
            del self.queues[guild_id]
        
        if guild_id in self.current_songs:
            del self.current_songs[guild_id]
        
        if guild_id in self.play_history:
            del self.play_history[guild_id]
        
        if guild_id in self.text_channels:
            del self.text_channels[guild_id]
        
        if guild_id in self.recommendation_enabled:
            del self.recommendation_enabled[guild_id]
        
        if guild_id in self.recommendation_history:
            del self.recommendation_history[guild_id]
        
        if guild_id in self.replay_enabled:  # NEW
            del self.replay_enabled[guild_id]
        
        # Clean up the lock last
        self.lock_manager.cleanup(guild_id)
        
        logger.info(f"Cleaned up all data for guild {guild_id}")