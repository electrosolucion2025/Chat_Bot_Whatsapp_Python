from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ValidationError

from app.services.openai_service import (process_incoming_message)
from app.services.session_service import session_manager

router = APIRouter(prefix="/openai", tags=["OpenAI"])

class MessageRequest(BaseModel):
    user_id: str  # Twilio's "From"
    message: str  # Twilio's "Body"
    session_id: Optional[str] = None  # Optional session ID

@router.post("/message")
async def get_openai_response(request: Request) -> dict:
    """
    Handles the complete message flow for incoming Twilio messages.
    """
    try:
        # Process the data sent in the form
        form_data = await request.form()
        data = dict(form_data)

        # Map the data to the MessageRequest model
        message_request = MessageRequest(
            user_id = data.get("From"), # Twilio's "From"
            message = data.get("Body"), # Twilio's "Body"
            session_id = None  # Optional session ID
        )
        
        response_data = process_incoming_message(
            user_id = message_request.user_id,
            message = message_request.message,
            session_id =message_request.session_id
        )
        
        return response_data
    
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/session/{session_id}/history")
def get_session_history(session_id: str) -> dict:
    """
    Get the session history for a given session ID
    """
    # Get the session history
    history = session_manager.get_session(session_id)
    
    # Check if the session exists
    if not history:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "history": history
    }