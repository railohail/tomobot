"""
Concurrency control utilities.

This module provides utilities for thread safety and concurrency control.
"""

import asyncio
from typing import Dict, Any

class LockManager:
    """
    Manages locks for different resources to prevent race conditions.
    
    This class provides a way to get and manage locks for different resources
    identified by a key, ensuring thread safety when accessing shared resources.
    """
    
    def __init__(self):
        """Initialize an empty lock dictionary."""
        self.locks: Dict[Any, asyncio.Lock] = {}
    
    def get_lock(self, key: Any) -> asyncio.Lock:
        """
        Get a lock for a specific key.
        
        If the lock doesn't exist yet, it's created.
        
        Args:
            key: The resource identifier for which to get a lock
            
        Returns:
            An asyncio.Lock instance for the specified key
        """
        if key not in self.locks:
            self.locks[key] = asyncio.Lock()
        return self.locks[key]
    
    async def with_lock(self, key: Any, func, *args, **kwargs):
        """
        Execute a function with a lock for the given key.
        
        Args:
            key: The resource identifier to lock
            func: The async function to execute while the lock is held
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The result of the function call
        """
        lock = self.get_lock(key)
        async with lock:
            return await func(*args, **kwargs)
    
    def cleanup(self, key: Any) -> bool:
        """
        Remove a lock for a specific key if it exists.
        
        Args:
            key: The resource identifier for which to remove the lock
            
        Returns:
            True if the lock was removed, False if it didn't exist
        """
        if key in self.locks:
            del self.locks[key]
            return True
        return False

class AsyncResource:
    """
    A resource with built-in locking to ensure thread safety.
    
    This class provides a base for resources that need thread safety,
    with methods that automatically acquire and release a lock.
    """
    
    def __init__(self):
        """Initialize the lock for this resource."""
        self.lock = asyncio.Lock()
    
    async def with_lock(self, func, *args, **kwargs):
        """
        Execute a function with the resource lock held.
        
        Args:
            func: The async function to execute while the lock is held
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The result of the function call
        """
        async with self.lock:
            return await func(*args, **kwargs)