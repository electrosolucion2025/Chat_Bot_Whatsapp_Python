from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.openai_service import build_prompt, generate_response, validate_history
from app.services.session_service import session_manager

router = APIRouter(prefix="/openai", tags=["OpenAI"])

class MessageRequest(BaseModel):
    user_id: str  # User ID (Twilio number)
    message: str  # User message
    session_id: str = None  # Optional session ID

@router.post("/message")
def get_openai_response(request: MessageRequest):
    """
    Handles the complete message flow.
    - Checks if the user has an active session.
    - Creates a session if it does not exist.
    - Handles the message and responds using OpenAI.
    """
    
    # Check if the user has an active session
    session_id = request.session_id
    
    # Validate the session ID, if not exists, create a new session
    if not session_id or session_id not in session_manager.sessions:
        session_id = session_manager.create_session()
    
    # Get the session's history
    history = session_manager.get_session(session_id)
    
    # Validate the history
    if not validate_history(history):
        raise HTTPException(status_code=400, detail="Invalid session history")
    
    # Build the prompt using the history and the user's message
    prompt = build_prompt(history, request.message)
    
    # Generate the response using OpenAI
    bot_response = generate_response(prompt)
    
    # Add the user message and bot response to the session
    session_manager.add_to_session(session_id, request.message, bot_response)
    
    return {
        "session_id": session_id,
        "bot": bot_response
    }

@router.get("/session/{session_id}/history")
def get_session_history(session_id: str):
    """
    Get the session history for a given session ID
    """
    history = session_manager.get_session(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "history": history
    }