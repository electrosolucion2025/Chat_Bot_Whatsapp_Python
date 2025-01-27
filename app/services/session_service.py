import redis
import json

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from app.core import config
from app.core.config import settings


class SessionManager:
    def __init__(self):
        ###### REDIS CLIENT ######
        # self.redis_client = redis.StrictRedis.from_url(settings.redis_url, decode_responses=True)
        # self.max_messages_per_hour = 25 # Max messages per hour
        ###### LOCAL REDIS CLIENT ######
        self.redis_client = redis.StrictRedis(
            host="localhost",
            port=6379,
            db=0,
            decode_responses=True
        )
        self.max_messages_per_hour = 25 # Max messages per hour

    def create_session(self, user_id: str) -> str:
        """Creates a new session and returns the session ID."""
        if self.redis_client.exists(f"user_session:{user_id}"):
            raise ValueError(f"User {user_id} already has an active session")
        
        session_id = str(uuid4())
        session_data = {
            "history": [{"bot": config.settings.INITIAL_PROMPT, "user_id": user_id}],
            "last_activity": datetime.now().isoformat()
        }
        
        self.redis_client.set(f"session:{session_id}", json.dumps(session_data))
        self.redis_client.set(f"user_session:{user_id}", session_id)
        
        if not self.redis_client.exists(f"user_limit:{user_id}"):
            user_limit = {
                "message_count": 0,
                "last_message_time": datetime.now().isoformat(),
                "blocked": False
            }
            self.redis_client.set(f"user_limit:{user_id}", json.dumps(user_limit))
            
        return session_id

    def is_within_limit(self, user_id: str) -> Tuple[bool, int]:
        """Check if the user is within the message limit and clear history if more than 5 minutes have passed."""
        user_limit_data = self.redis_client.get(f"user_limit:{user_id}")
        if user_limit_data:
            user_limit = json.loads(user_limit_data)
            last_message_time = datetime.fromisoformat(user_limit["last_message_time"])
            now = datetime.now()
            time_diff = now - last_message_time

            if time_diff > timedelta(minutes=5):
                session_id = self.get_session_by_user(user_id)
                if session_id:
                    self.clear_session(session_id)
                user_limit["last_message_time"] = now.isoformat()
                self.redis_client.set(f"user_limit:{user_id}", json.dumps(user_limit))

                if user_limit["blocked"]:
                    if time_diff > timedelta(hours=1):
                        user_limit["blocked"] = False
                        user_limit["message_count"] = 0
                        self.redis_client.set(f"user_limit:{user_id}", json.dumps(user_limit))
                    else:
                        raise ValueError("El camarero está muy ocupado y no podrá atenderle más por ahora. Por favor, inténtelo de nuevo más tarde.")
                else:
                    user_limit["message_count"] = 0
                    self.redis_client.set(f"user_limit:{user_id}", json.dumps(user_limit))

            if user_limit["blocked"]:
                if time_diff > timedelta(hours=1):
                    user_limit["blocked"] = False
                    user_limit["message_count"] = 0
                    user_limit["last_message_time"] = now.isoformat()
                    self.redis_client.set(f"user_limit:{user_id}", json.dumps(user_limit))
                else:
                    raise ValueError("El camarero está muy ocupado y no podrá atenderle más por ahora. Por favor, inténtelo de nuevo más tarde.")

            if user_limit["message_count"] < self.max_messages_per_hour:
                return True, user_limit["message_count"]

        return False, 0

    def increment_message_count(self, user_id: str):
        """Increment the message count for the user."""
        user_limit_data = self.redis_client.get(f"user_limit:{user_id}")
        if user_limit_data:
            user_limit = json.loads(user_limit_data)
            user_limit["message_count"] += 1
            user_limit["last_message_time"] = datetime.now().isoformat()
            if user_limit["message_count"] >= self.max_messages_per_hour:
                user_limit["blocked"] = True
            self.redis_client.set(f"user_limit:{user_id}", json.dumps(user_limit))

    def add_to_session(self, session_id: str, user_id: str, user_message: str, bot_response: str):
        """Adds a user message and bot response to the session."""
        if not self.is_within_limit(user_id)[0]:
            raise ValueError("Message limit exceeded or user is blocked")

        session_data = self.redis_client.get(f"session:{session_id}")
        if not session_data:
            raise ValueError(f"Invalid session id {session_id}")
        
        session = json.loads(session_data)
        session["history"].append({"user": user_message, "bot": bot_response, "user_id": user_id})
        session["last_activity"] = datetime.now().isoformat()
        
        self.redis_client.set(f"session:{session_id}", json.dumps(session))
        self.increment_message_count(user_id)

    def get_session(self, session_id: str) -> List[Dict[str, str]]:
        """Returns the session data for a given session ID."""
        session_data = self.redis_client.get(f"session:{session_id}")
        if not session_data:
            raise ValueError(f"Invalid session id {session_id}")
        
        session = json.loads(session_data)
        return session["history"]
    
    def get_session_by_user(self, user_id: str) -> Optional[str]:
        """Returns the session ID for a given user ID, if exists."""
        session_id = self.redis_client.get(f"user_session:{user_id}")
        return session_id if session_id else None
            
    def clear_session(self, session_id: str):
        """Clears the session data for a given session ID and resets the message count."""
        session_data = self.redis_client.get(f"session:{session_id}")
        if session_data:
            session = json.loads(session_data)
            user_id = session["history"][0]["user_id"]
            new_session_data = {
                "history": [{"bot": config.settings.INITIAL_PROMPT, "user_id": user_id}],
                "last_activity": datetime.now().isoformat()
            }
            self.redis_client.set(f"session:{session_id}", json.dumps(new_session_data))

            # Reset the message count for the user
            user_limit_data = self.redis_client.get(f"user_limit:{user_id}")
            if user_limit_data:
                user_limit = json.loads(user_limit_data)
                user_limit["message_count"] = 0
                user_limit["last_message_time"] = datetime.now().isoformat()
                self.redis_client.set(f"user_limit:{user_id}", json.dumps(user_limit))
            
    def add_payment_link(self, session_id: str, payment_link: str):
        """Adds a payment link to the session."""
        session_data = self.redis_client.get(f"session:{session_id}")
        if session_data:
            session = json.loads(session_data)
            session["payment_link"] = payment_link
            self.redis_client.set(f"session:{session_id}", json.dumps(session))
    
    def get_payment_link(self, session_id: str) -> Optional[str]:
        session_data = self.redis_client.get(f"session:{session_id}")
        if session_data:
            session = json.loads(session_data)
            return session.get("payment_link")
        return None
    
    def clear_payment_link(self, session_id: str):
        """Clear the payment link from the session."""
        session_data = self.redis_client.get(f"session:{session_id}")
        if session_data:
            session = json.loads(session_data)
            if "payment_link" in session:
                del session["payment_link"]
                self.redis_client.set(f"session:{session_id}", json.dumps(session))
            
    def add_order_data(self, session_id: str, order_data: Dict):
        """Adds the order data to the session."""
        session_data = self.redis_client.get(f"session:{session_id}")
        if not session_data:
            raise ValueError("Invalid session ID")
        
        session = json.loads(session_data)
        session["order_data"] = order_data
        self.redis_client.set(f"session:{session_id}", json.dumps(session))
        
    def get_order_data(self, session_id: str) -> Optional[Dict]:
        """Returns the order data for a given session ID."""
        session_data = self.redis_client.get(f"session:{session_id}")
        if session_data:
            session = json.loads(session_data)
            return session.get("order_data")
        return None
    
    def update_order_data(self, session_id: str, updated_data: Dict):
        """
        Updates the order data for a given session ID with new values.
        """
        # Obtener los datos de la sesión desde Redis
        session_data = self.redis_client.get(f"session:{session_id}")
        if not session_data:
            raise ValueError("Invalid session ID")
        
        # Cargar la sesión y los datos del pedido
        session = json.loads(session_data)
        order_data = session.get("order_data")
        if not order_data:
            raise ValueError("No order data found in the session")
        
        # Actualizar los campos del pedido con los datos nuevos
        order_data.update(updated_data)
        
        # Guardar la sesión actualizada en Redis
        session["order_data"] = order_data
        self.redis_client.set(f"session:{session_id}", json.dumps(session))
    
    def clear_order_data(self, session_id: str):
        """Clear the order data from the session."""
        session_data = self.redis_client.get(f"session:{session_id}")
        if session_data:
            session = json.loads(session_data)
            if "order_data" in session:
                del session["order_data"]
                self.redis_client.set(f"session:{session_id}", json.dumps(session))
            
# Global instance of the SessionManager
session_manager = SessionManager()
