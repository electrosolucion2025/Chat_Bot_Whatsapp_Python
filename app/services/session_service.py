from typing import Dict, List
from uuid import uuid4

INITIAL_PROMPT = """
Eres un camarero virtual en un restaurante, te llamas Juan. Presentate. Tu trabajo es ayudar a los clientes con el menú y responder sus preguntas. Aquí está el menú en formato JSON:

{
    "menu": [
        {"name": "Pizza Margarita", "price": 8.5},
        {"name": "Ensalada César", "price": 7.0},
        {"name": "Spaghetti Carbonara", "price": 9.5}
    ]
}

Responde de manera cortés y profesional, y recuerda siempre referirte a los elementos del menú. No te inventes nada.
"""

class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, List[Dict[str, str]]] = {}

    def create_session(self) -> str:
        """_summary_
        Create a new session and return the session id
        Returns:
            str: _description_
        """
        session_id = str(uuid4())
        self.sessions[session_id] = [{"bot": INITIAL_PROMPT}]
        return session_id
    
    def get_session(self, session_id: str) -> List[Dict[str, str]]:
        """_summary_
        Get the session data for a given session id
        Args:
            session_id (str): _description_
        Returns:
            List[Dict[str, str]]: _description_
        """
        return self.sessions.get(session_id, [])
    
    def add_to_session(self, session_id: str, user_message: str, bot_response: str):
        """_summary_
        Add a user message and bot response to the session
        Args:
            session_id (str): _description_
            user_message (str): _description_
            bot_response (str): _description_
        """
        self.sessions[session_id].append({
            "user": user_message,
            "bot": bot_response
        })
    
    def clear_session(self, session_id: str):
        """_summary_
        Clear the session data for a given session id
        Args:
            session_id (str): _description_
        """
        self.sessions[session_id] = []

# Global instance of the SessionManager
session_manager = SessionManager()
    