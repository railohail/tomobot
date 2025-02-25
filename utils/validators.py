import re

def is_youtube_url(url: str) -> bool:
    """Check if a URL is a valid YouTube URL."""
    patterns = [
        r'^https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
        r'^https?://(?:www\.)?youtu\.be/[\w-]+',
    ]
    return any(re.match(pattern, url) for pattern in patterns)

def contains_mention(message: str, user_id: str) -> bool:
    """Check if a message contains a mention of the specified user."""
    pattern = f'<@{user_id}>'
    return bool(re.search(pattern, message))

def remove_mention(message: str, user_id: str) -> str:
    """Remove mention of the specified user from the message."""
    pattern = f'<@{user_id}>\s*'
    return re.sub(pattern, '', message).strip()