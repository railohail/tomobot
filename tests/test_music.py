"""
Tests for the music queue module.
"""

import unittest
import asyncio
from utils.music_queue import MusicQueue

class TestTrack:
    """Dummy track class for testing."""
    def __init__(self, title, author, length=60000):
        self.title = title
        self.author = author
        self.length = length

class TestMusicQueue(unittest.TestCase):
    """Test case for the MusicQueue class."""
    
    def setUp(self):
        self.queue = MusicQueue()
        self.guild_id = 123456789
        
        # Create some test tracks
        self.tracks = [
            TestTrack("Song 1", "Artist 1"),
            TestTrack("Song 2", "Artist 2"),
            TestTrack("Song 3", "Artist 1"),
            TestTrack("Song 4", "Artist 3")
        ]
    
    def run_async(self, coro):
        """Run an async function in the event loop."""
        return asyncio.get_event_loop().run_until_complete(coro)
    
    def test_add_and_get_track(self):
        """Test adding and getting tracks from the queue."""
        # Add a track
        self.run_async(self.queue.add_track(self.guild_id, self.tracks[0]))
        
        # Check queue length
        length = self.run_async(self.queue.get_queue_length(self.guild_id))
        self.assertEqual(length, 1)
        
        # Get the track
        track = self.run_async(self.queue.get_next_track(self.guild_id))
        self.assertEqual(track.title, "Song 1")
        self.assertEqual(track.author, "Artist 1")
        
        # Queue should now be empty
        length = self.run_async(self.queue.get_queue_length(self.guild_id))
        self.assertEqual(length, 0)
    
    def test_add_playlist(self):
        """Test adding multiple tracks at once."""
        # Add all tracks
        self.run_async(self.queue.add_playlist(self.guild_id, self.tracks))
        
        # Check queue length
        length = self.run_async(self.queue.get_queue_length(self.guild_id))
        self.assertEqual(length, 4)
        
        # Get items
        items = self.run_async(self.queue.get_queue_items(self.guild_id))
        self.assertEqual(len(items), 4)
        self.assertEqual(items[0].title, "Song 1")
        self.assertEqual(items[3].title, "Song 4")
    
    def test_clear_queue(self):
        """Test clearing the queue."""
        # Add tracks and then clear
        self.run_async(self.queue.add_playlist(self.guild_id, self.tracks))
        self.run_async(self.queue.clear_queue(self.guild_id))
        
        # Check queue length
        length = self.run_async(self.queue.get_queue_length(self.guild_id))
        self.assertEqual(length, 0)
    
    def test_remove_track(self):
        """Test removing a specific track."""
        # Add tracks
        self.run_async(self.queue.add_playlist(self.guild_id, self.tracks))
        
        # Remove the second track
        removed = self.run_async(self.queue.remove_track(self.guild_id, 1))
        self.assertEqual(removed.title, "Song 2")
        
        # Check queue
        items = self.run_async(self.queue.get_queue_items(self.guild_id))
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0].title, "Song 1")
        self.assertEqual(items[1].title, "Song 3")
    
    def test_play_history(self):
        """Test play history tracking."""
        # Set current songs
        self.queue.set_current_song(self.guild_id, self.tracks[0])
        self.queue.set_current_song(self.guild_id, self.tracks[1])
        self.queue.set_current_song(self.guild_id, self.tracks[2])
        
        # Check history
        history = self.queue.get_play_history(self.guild_id)
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0], "Artist 1")
        self.assertEqual(history[1], "Artist 2")
        self.assertEqual(history[2], "Artist 1")
    
    def test_recommendations(self):
        """Test recommendation system."""
        # Add some play history
        for _ in range(5):
            self.queue.add_to_play_history(self.guild_id, "Artist 1")
        
        for _ in range(3):
            self.queue.add_to_play_history(self.guild_id, "Artist 2")
        
        for _ in range(1):
            self.queue.add_to_play_history(self.guild_id, "Artist 3")
        
        # Get recommendations (with a fixed seed for deterministic testing)
        import random
        random.seed(42)
        
        recommendations = self.run_async(self.queue.get_recommendations(self.guild_id, limit=2))
        self.assertEqual(len(recommendations), 2)
        
        # Since we added Artist 1 the most, it should be in the recommendations
        # (Note: This is probabilistic due to random sampling, but with the seed it should be consistent)
        all_recommendations = self.run_async(self.queue.get_recommendations(self.guild_id, limit=3))
        self.assertEqual(len(all_recommendations), 3)
        self.assertIn("Artist 1", all_recommendations)
        
        # Test recommendation toggling
        self.assertFalse(self.queue.get_recommendation_status(self.guild_id))
        self.queue.toggle_recommendations(self.guild_id)
        self.assertTrue(self.queue.get_recommendation_status(self.guild_id))

if __name__ == '__main__':
    unittest.main()