# utils.py - Shared Utilities
import html
import re
from typing import Optional

def clean_html(text: str) -> str:
    """Remove HTML tags and decode HTML entities"""
    if not text:
        return ""
    # Remove HTML tags
    cleaned = re.sub(r'<[^>]+>', '', text)
    # Decode HTML entities
    cleaned = html.unescape(cleaned)
    return cleaned.strip()

def color_german_word(word: str) -> str:
    """Add color formatting to German articles"""
    if not word:
        return word
    
    # Color mapping for German articles
    article_colors = {
        "der": "#5555ff",  # Blue for masculine
        "das": "#00aa00",  # Green for neuter  
        "die": "#ff55ff"   # Magenta for feminine
    }
    
    parts = word.split()
    if len(parts) >= 2 and parts[0].lower() in article_colors:
        color = article_colors[parts[0].lower()]
        return f'<span style="color: {color};">{word}</span>'
    
    return word

def format_error_message(error: Exception) -> str:
    """Format error message for user display"""
    error_msg = str(error)
    
    # Common error message mappings
    if "timeout" in error_msg.lower():
        return "Connection timeout - server is taking too long to respond"
    elif "connection" in error_msg.lower() or "network" in error_msg.lower():
        return "Network error - cannot reach server"
    elif "401" in error_msg or "unauthorized" in error_msg.lower():
        return "Authentication failed - check your API key"
    elif "404" in error_msg:
        return "Server endpoint not found - check server URL"
    elif "500" in error_msg:
        return "Server error - try again later"
    else:
        return f"Error: {error_msg}"

def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncate text with ellipsis if too long"""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def validate_url(url: str) -> bool:
    """Basic URL validation"""
    if not url:
        return False
    url = url.strip()
    return bool(re.match(r'^https?://.+', url))

def ensure_protocol(url: str, default_protocol: str = "http") -> str:
    """Ensure URL has a protocol"""
    if not url:
        return ""
    
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        return f"{default_protocol}://{url}"
    return url