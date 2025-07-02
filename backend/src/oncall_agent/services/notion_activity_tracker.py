"""Track and log all Notion operations performed by the agent."""

import asyncio
import json
from collections import defaultdict
from datetime import datetime
from typing import Any

from src.oncall_agent.utils import get_logger

logger = get_logger(__name__)


class NotionActivityTracker:
    """Track all Notion read/write operations."""

    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NotionActivityTracker, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.activities = []
        self.read_pages = set()  # Track which pages have been read
        self.created_pages = set()  # Track pages created
        self.operation_counts = defaultdict(int)
        self.last_activity = None
        self._initialized = True
        logger.info("Notion Activity Tracker initialized")

    async def log_operation(self, operation: str, details: dict[str, Any]) -> None:
        """Log a Notion operation."""
        async with self._lock:
            activity = {
                "timestamp": datetime.utcnow().isoformat(),
                "operation": operation,
                "details": details,
                "success": details.get("success", True)
            }

            self.activities.append(activity)
            self.operation_counts[operation] += 1
            self.last_activity = activity

            # Track specific operations
            if operation == "read_page" and details.get("page_id"):
                self.read_pages.add(details["page_id"])
            elif operation == "create_page" and details.get("page_id"):
                self.created_pages.add(details["page_id"])

            # Log to file for persistence
            logger.info(f"Notion {operation}: {json.dumps(details, default=str)}")

            # Keep only last 1000 activities in memory
            if len(self.activities) > 1000:
                self.activities = self.activities[-1000:]

    async def get_activity_summary(self) -> dict[str, Any]:
        """Get a summary of all Notion activities."""
        async with self._lock:
            return {
                "total_operations": sum(self.operation_counts.values()),
                "operation_breakdown": dict(self.operation_counts),
                "pages_read": len(self.read_pages),
                "pages_created": len(self.created_pages),
                "last_activity": self.last_activity,
                "recent_activities": self.activities[-10:],  # Last 10 activities
                "tracked_since": self.activities[0]["timestamp"] if self.activities else None
            }

    async def get_page_history(self, page_id: str) -> list[dict[str, Any]]:
        """Get all activities related to a specific page."""
        async with self._lock:
            return [
                activity for activity in self.activities
                if activity.get("details", {}).get("page_id") == page_id
            ]

    async def verify_page_read(self, page_id: str) -> dict[str, Any]:
        """Verify if a specific page has been read."""
        async with self._lock:
            was_read = page_id in self.read_pages

            # Find when it was read
            read_activities = [
                a for a in self.activities
                if a["operation"] == "read_page" and
                a.get("details", {}).get("page_id") == page_id
            ]

            return {
                "page_id": page_id,
                "was_read": was_read,
                "read_count": len(read_activities),
                "read_times": [a["timestamp"] for a in read_activities],
                "last_read": read_activities[-1]["timestamp"] if read_activities else None
            }

    async def get_recent_reads(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get the most recent page reads."""
        async with self._lock:
            read_activities = [
                a for a in self.activities
                if a["operation"] in ["read_page", "query_database", "search_pages"]
            ]
            return read_activities[-limit:]

    async def get_recent_writes(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get the most recent page writes."""
        async with self._lock:
            write_activities = [
                a for a in self.activities
                if a["operation"] in ["create_page", "update_page", "append_to_page"]
            ]
            return write_activities[-limit:]

    async def clear_history(self) -> None:
        """Clear all tracked activities."""
        async with self._lock:
            self.activities.clear()
            self.read_pages.clear()
            self.created_pages.clear()
            self.operation_counts.clear()
            self.last_activity = None
            logger.info("Notion activity history cleared")


# Global tracker instance
notion_tracker = NotionActivityTracker()


# Decorator to automatically track Notion operations
def track_notion_operation(operation_name: str):
    """Decorator to track Notion operations."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract relevant details from arguments
            details = {
                "function": func.__name__,
                "args": str(args)[:200],  # Truncate long args
                "kwargs": str(kwargs)[:200]
            }

            # Try to extract page_id if present
            if "page_id" in kwargs:
                details["page_id"] = kwargs["page_id"]
            elif len(args) > 1 and isinstance(args[1], str):
                details["page_id"] = args[1]

            try:
                # Execute the function
                result = await func(*args, **kwargs)

                # Track successful operation
                details["success"] = True
                if isinstance(result, dict):
                    if "id" in result:
                        details["page_id"] = result["id"]
                    if "url" in result:
                        details["page_url"] = result["url"]

                await notion_tracker.log_operation(operation_name, details)
                return result

            except Exception as e:
                # Track failed operation
                details["success"] = False
                details["error"] = str(e)
                await notion_tracker.log_operation(operation_name, details)
                raise

        return wrapper
    return decorator
