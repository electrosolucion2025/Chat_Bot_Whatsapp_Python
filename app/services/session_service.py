from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import uuid4

from app.core import config


class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, List[Dict[str, str]]] = {} # session_id -> [{"user": user_message, "bot": bot_response}]
        self.user_sessions: Dict[str, str] = {} # user_id -> session_id
        self.user_limits: Dict[str, int] = {} # user_id -> limit
        self.max_messages_per_hour = 30 # Max messages per hour

    def create_session(self, user_id: str) -> str:
        """Creates a new session and returns the session ID."""
        if user_id in self.user_sessions:
            raise ValueError(f"User {user_id} already has an active session")
        
        session_id = str(uuid4())
        
        self.sessions[session_id] = {
            "history": [{"bot": config.settings.INITIAL_PROMPT, "user_id": user_id}],
            "last_activity": datetime.now()
        }
        
        if user_id not in self.user_limits:
            self.user_limits[user_id] = {
                "message_count": 0,
                "last_message_time": datetime.now()
            }
            
        return session_id
    
    def get_session(self, session_id: str) -> List[Dict[str, str]]:
        """Returns the session data for a given session ID."""
        session = self.sessions.get(session_id, {}).get("history", [])
        
        if session is None:
            raise ValueError(f"Invalid session id {session_id}")
        
        return session
    
    def get_session_by_user(self, user_id: str) -> List[Dict[str, str]]:
        """Returns the session ID for a given user ID, if exists."""
        for session_id, session in self.sessions.items():
            if session["history"][0].get("user_id") == user_id:
                return session_id
        
        return None
    
    def add_to_session(self, session_id: str, user_id: str, user_message: str, bot_response: str):
        """Adds a user message and bot response to the session."""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError("Invalid session ID")
        
        # TODO: VOLVER A ACTIVAR ESTO PARA LIMITAR LOS MENSAJES
        # Verify the user ID
        # if not self.check_message_limit(user_id):
        #     raise ValueError("Message limit exceeded. Please try again later.")
        
        # Update the session data
        session["history"].append({"user": user_message, "bot": bot_response})
        session["last_activity"] = datetime.now()
        
        # Increment the message count
        self.user_limits[user_id]["message_count"] += 1
        
    def check_message_limit(self, user_id: str) -> bool:
        """Checks if the user has exceeded the message limit."""
        user_limit = self.user_limits.get(user_id)
        if not user_limit:
            return True # No limit set for the user
        
        # Check if the user has exceeded the message limit
        now = datetime.now()
        time_diff = now - user_limit["last_message_time"]
        
        if time_diff > timedelta(hours=1):
            # Reset the message count if the last message was sent over an hour ago
            self.user_limits[user_id]["message_count"] = 0
            self.user_limits[user_id]["last_message_time"] = now
        
        # Ok if the message count is less than the limit
        if self.user_limits[user_id]["message_count"] < self.max_messages_per_hour:
            return True
        
        # Block the user if the message count exceeds the limit
        return False
            
    def clear_session(self, session_id: str):
        """Clears the session data for a given session ID."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            
    def add_payment_link(self, session_id: str, payment_link: str):
        """Adds a payment link to the session."""
        if session_id in self.sessions:
            self.sessions[session_id]["payment_link"] = payment_link
    
    def get_payment_link(self, session: str):
        return self.sessions.get(session, {}).get("payment_link")
    
    def clear_payment_link(self, session_id: str):
        """Clear the payment link from the session."""
        if session_id in self.sessions and "payment_link" in self.sessions[session_id]:
            del self.sessions[session_id]["payment_link"]
            
    def add_order_data(self, session_id: str, order_data: Dict):
        """Adds the order data to the session."""
        if session_id not in self.sessions:
            raise ValueError("Invalid session ID")
        
        self.sessions[session_id]["order_data"] = order_data
        
    def get_order_data(self, session_id: str) -> Optional[Dict]:
        """Returns the order data for a given session ID."""
        return self.sessions.get(session_id, {}).get("order_data")
    
    def clear_order_data(self, session_id: str):
        """Clear the order data from the session."""
        if session_id in self.sessions and "order_data" in self.sessions[session_id]:
            del self.sessions[session_id]["order_data"]
            
# Global instance of the SessionManager
session_manager = SessionManager()
    