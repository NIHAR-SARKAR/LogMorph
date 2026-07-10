import os
import time
import threading
from datetime import datetime, timezone
from typing import Callable, Dict, Set

from app.core.logging import logger

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent, FileMovedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = object
    FileCreatedEvent = FileModifiedEvent = FileMovedEvent = None

class LogFileHandler(FileSystemEventHandler):
    """Handle filesystem events for log files."""

    def __init__(self, log_source_id: int, callback: Callable, file_pattern: str = "*.log"):
        self.log_source_id = log_source_id
        self.callback = callback
        self.file_pattern = file_pattern
        self._debounce_timers: Dict[str, threading.Timer] = {}

    def _is_log_file(self, path: str) -> bool:
        """Check if file matches log pattern."""
        import fnmatch
        filename = os.path.basename(path)
        return fnmatch.fnmatch(filename, self.file_pattern) or filename.endswith('.log') or filename.endswith('.txt')

    def _debounce(self, path: str, event_type: str):
        """Debounce rapid file changes."""
        key = f"{path}:{event_type}"
        if key in self._debounce_timers:
            self._debounce_timers[key].cancel()

        timer = threading.Timer(2.0, self._handle_event, args=[path, event_type])
        self._debounce_timers[key] = timer
        timer.start()

    def _handle_event(self, path: str, event_type: str):
        """Handle debounced event."""
        try:
            self.callback(self.log_source_id, path, event_type)
        except Exception as e:
            logger.error(f"Error handling file event: {e}")

    def on_created(self, event):
        if not event.is_directory and self._is_log_file(event.src_path):
            logger.info(f"Log file created: {event.src_path}")
            self._debounce(event.src_path, "created")

    def on_modified(self, event):
        if not event.is_directory and self._is_log_file(event.src_path):
            self._debounce(event.src_path, "modified")

    def on_moved(self, event):
        if not event.is_directory and self._is_log_file(event.dest_path):
            logger.info(f"Log file moved: {event.dest_path}")
            self._debounce(event.dest_path, "moved")

class FileWatcherService:
    """Service to watch log directories for changes."""

    def __init__(self):
        self.observers: Dict[int, Observer] = {}
        self.handlers: Dict[int, LogFileHandler] = {}
        self._lock = threading.Lock()
        self._callbacks: list = []

    def add_callback(self, callback: Callable):
        """Add a callback for file events."""
        self._callbacks.append(callback)

    def _notify(self, log_source_id: int, path: str, event_type: str):
        """Notify all callbacks."""
        for callback in self._callbacks:
            try:
                callback(log_source_id, path, event_type)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def start_watching(self, log_source_id: int, path: str, recursive: bool = True, file_pattern: str = "*.log"):
        """Start watching a log source directory."""
        if not WATCHDOG_AVAILABLE:
            logger.warning("watchdog is not installed; file watching is disabled")
            return False

        if not os.path.exists(path):
            logger.warning(f"Path does not exist: {path}")
            return False

        with self._lock:
            if log_source_id in self.observers:
                self.stop_watching(log_source_id)

            handler = LogFileHandler(log_source_id, self._notify, file_pattern)
            observer = Observer()

            watch_path = path if os.path.isdir(path) else os.path.dirname(path)
            observer.schedule(handler, watch_path, recursive=recursive)
            observer.start()

            self.observers[log_source_id] = observer
            self.handlers[log_source_id] = handler

            logger.info(f"Started watching {watch_path} for source {log_source_id}")
            return True

    def stop_watching(self, log_source_id: int):
        """Stop watching a log source."""
        with self._lock:
            if log_source_id in self.observers:
                self.observers[log_source_id].stop()
                self.observers[log_source_id].join()
                del self.observers[log_source_id]
                del self.handlers[log_source_id]
                logger.info(f"Stopped watching source {log_source_id}")

    def stop_all(self):
        """Stop all watchers."""
        if not WATCHDOG_AVAILABLE:
            return

        with self._lock:
            for log_source_id in list(self.observers.keys()):
                self.observers[log_source_id].stop()
                self.observers[log_source_id].join()
            self.observers.clear()
            self.handlers.clear()
            logger.info("Stopped all file watchers")

    def get_active_watches(self) -> Dict[int, str]:
        """Get list of active watches."""
        with self._lock:
            return {k: "active" for k in self.observers.keys()}

file_watcher = FileWatcherService()
