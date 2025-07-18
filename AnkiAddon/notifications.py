# notifications.py - Simple Notification System
from aqt.utils import tooltip, showInfo, showCritical
from .utils import format_error_message

class NotificationManager:
    """Simple notification manager for user feedback"""
    
    def __init__(self):
        pass
    
    def success(self, message: str, duration: int = 2000) -> None:
        """Show success notification"""
        tooltip(f"✅ {message}", period=duration)
    
    def error(self, error, title: str = "Error") -> None:
        """Show error notification"""
        if isinstance(error, Exception):
            message = format_error_message(error)
        else:
            message = str(error)
        
        tooltip(f"❌ {message}", period=3000)
    
    def info(self, message: str) -> None:
        """Show info dialog"""
        showInfo(message)
    
    def warning(self, message: str) -> None:
        """Show warning as critical dialog"""
        showCritical(message)
    
    def startup_complete(self, results: dict) -> None:
        """Show startup completion notification"""
        messages = []
        
        if results.get('imported'):
            messages.append(f"Imported {results['imported']} words")
        
        if results.get('uploaded'):
            messages.append(f"Uploaded {results['uploaded']} cards")
        
        if results.get('errors'):
            messages.append(f"{results['errors']} errors")
        
        if messages:
            combined = " | ".join(messages)
            if results.get('errors'):
                tooltip(f"⚠️ {combined}", period=3000)
            else:
                tooltip(f"✅ {combined}", period=2500)
        else:
            tooltip("✅ Startup complete", period=1500)