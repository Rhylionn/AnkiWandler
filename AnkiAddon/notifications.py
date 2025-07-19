# notifications.py - Simple Notification System (Fixed)
from aqt.utils import tooltip, showInfo, showCritical
from aqt.qt import QTimer
from .utils import format_error_message

class NotificationManager:
    """Simple notification manager for user feedback"""
    
    def __init__(self):
        self.active_timers = []  # Track all timers for cleanup
    
    def cleanup(self):
        """Clean up all active timers"""
        try:
            for timer in self.active_timers:
                if timer and timer.isActive():
                    timer.stop()
            self.active_timers.clear()
            print("NotificationManager cleanup completed")
        except Exception as e:
            print(f"Error during NotificationManager cleanup: {e}")
    
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
    
    def _create_timer(self, timeout_ms: int, callback) -> QTimer:
        """Create a timer with automatic cleanup tracking"""
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(callback)
        timer.timeout.connect(lambda: self._remove_timer(timer))  # Auto-cleanup
        self.active_timers.append(timer)
        timer.start(timeout_ms)
        return timer
    
    def _remove_timer(self, timer: QTimer) -> None:
        """Remove timer from tracking list"""
        try:
            if timer in self.active_timers:
                self.active_timers.remove(timer)
        except Exception as e:
            print(f"Error removing timer: {e}")