"""
Session state management for CLI app
"""
from typing import Optional
from pydantic import BaseModel


class SessionState(BaseModel):
    """Tracks current CLI session state"""

    current_world_id: Optional[int] = None
    current_world_name: Optional[str] = None

    def set_world(self, world_id: int, world_name: str):
        """Set the current world context"""
        self.current_world_id = world_id
        self.current_world_name = world_name

    def clear_world(self):
        """Clear world selection"""
        self.current_world_id = None
        self.current_world_name = None

    @property
    def has_world_selected(self) -> bool:
        """Check if a world is currently selected"""
        return self.current_world_id is not None


# Global state instance
state = SessionState()
