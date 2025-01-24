import os
import shutil
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ValidationError

from app.services.openai_service import download_audio_from_twilio, process_incoming_message, transcribe_audio_with_whisper
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
        
        # Check if an audio file was sent in the form data
        media_url = data.get("MediaUrl0") # Twilio's "MediaUrl0"
        
        if media_url:
            # Audio processing flow
            temp_audio_path = None
            try:
                # Download the audio file
                temp_audio_path = await download_audio_from_twilio(media_url, data.get("From"))
                
                # Transcribe the audio file
                transcribed_text = await transcribe_audio_with_whisper(temp_audio_path)
                
                # Now you can use the transcribed text as the user message
                user_message = transcribed_text
                
            finally:
                # Clean up temporary files in the audio directory
                audio_dir = os.path.join(os.path.dirname(__file__), '../services/audio_files')
                if os.path.exists(audio_dir):
                    shutil.rmtree(audio_dir)
                    os.makedirs(audio_dir)
            
        else:
            # Text processing flow
            user_message = data.get("Body") # Twilio's "Body"

        # Map the data to the MessageRequest model
        message_request = MessageRequest(
            user_id = data.get("From"), # Twilio's "From"
            message = user_message, # Twilio's "Body"
            session_id = None  # Optional session ID
        )
        
        response_data = process_incoming_message(
            user_id = message_request.user_id,
            message = message_request.message,
            session_id = message_request.session_id
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