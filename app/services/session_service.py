from typing import Dict, List
from uuid import uuid4

from app.core import config

class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, List[Dict[str, str]]] = {} # session_id -> [{"user": user_message, "bot": bot_response}]
        self.user_sessions: Dict[str, str] = {} # user_id -> session_id

    def create_session(self, user_id: str) -> str:
        """Creates a new session and returns the session ID."""
        if user_id in self.user_sessions:
            raise ValueError(f"User {user_id} already has an active session")
        
        session_id = str(uuid4())
        self.sessions[session_id] = [{"bot": config.settings.INITIAL_PROMPT}]
        self.user_sessions[user_id] = session_id
        return session_id
    
    def get_session(self, session_id: str) -> List[Dict[str, str]]:
        """Returns the session data for a given session ID."""
        session = self.sessions.get(session_id)
        
        if session is None:
            raise ValueError(f"Invalid session id {session_id}")
        
        return session
    
    def get_session_by_user(self, user_id: str) -> List[Dict[str, str]]:
        """Returns the session ID for a given user ID, if exists."""
        return self.user_sessions.get(user_id)
    
    def add_to_session(self, session_id: str, user_message: str, bot_response: str):
        """Adds a user message and bot response to the session."""
        if session_id not in self.sessions:
            raise ValueError(f"Invalid session id {session_id}")
        
        self.sessions[session_id].append({
            "user": user_message,
            "bot": bot_response
        })
    
    def clear_session(self, session_id: str):
        """Clears the session data for a given session ID."""
        if session_id not in self.sessions:
            raise ValueError(f"Invalid session id {session_id}")
        
        # Find and remove the session ID from the user sessions
        user_id = None
        for uid, sid in self.user_sessions.items():
            if sid == session_id:
                user_id = uid
                break
            
        if user_id:
            del self.user_sessions[user_id]
            
        del self.sessions[session_id]

# Global instance of the SessionManager
session_manager = SessionManager()
    