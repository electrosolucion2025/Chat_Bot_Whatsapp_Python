from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ValidationError
import stripe

from app.routes.payment_routes import create_payment_link
from app.services.openai_service import build_prompt, generate_response, validate_history
from app.services.order_parser_service import parse_bot_message
from app.services.session_service import session_manager
from app.services.twilio_service import TwilioService

router = APIRouter(prefix="/openai", tags=["OpenAI"])

class MessageRequest(BaseModel):
    user_id: str  # Twilio's "From"
    message: str  # Twilio's "Body"
    session_id: Optional[str] = None  # Optional session ID

@router.post("/message")
async def get_openai_response(request: Request):
    """
    Handles the complete message flow for incoming Twilio messages.
    """
    try:
        # Procesar los datos enviados en el formulario
        form_data = await request.form()
        data = dict(form_data)

        # Mapear los datos del formulario al modelo MessageRequest
        message_request = MessageRequest(
            user_id = data.get("From"),
            message = data.get("Body"),
            session_id = None  # Puedes manejarlo internamente si es opcional
        )
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Check if the user has an active session
    session_id = message_request.session_id or session_manager.get_session_by_user(message_request.user_id)
    print(f"Session ID: {session_id}")
    
    # If no session is found, create a new session
    if not session_id:
        session_id = session_manager.create_session(message_request.user_id)
    
    # Get the session's history
    history = session_manager.get_session(session_id)
    
    # Validate the history
    if not validate_history(history):
        raise HTTPException(status_code=400, detail="Invalid session history")
    
    # Build the prompt using the history and the user's message
    prompt = build_prompt(history, message_request.message)
    
    # Generate the response using OpenAI
    bot_response = generate_response(prompt)
    
    # Check if the bot response contains "Resumen del Pedido:"
    if "Resumen del Pedido:" in bot_response:
        # Parse the bot response to get the order summary
        order_data = parse_bot_message(bot_response)
        
        existing_payment_link = session_manager.get_payment_link(session_id)
        
        if existing_payment_link:
            session_manager.clear_payment_link(session_id)
            
        # Get link to payment
        payment_link_response = create_payment_link(order_data, message_request.user_id, session_id)
        
        # Save the payment link to the session
        session_manager.add_payment_link(session_id, payment_link_response["url"])
        
        # Add the payment link to the bot response
        bot_response += f"\n\nPuedes pagar tu pedido en el siguiente enlace: {payment_link_response['url']}"
    
    # Add the user message and bot response to the session
    session_manager.add_to_session(session_id, message_request.user_id, message_request.message, bot_response)
    
    # Send the response to the user via Twilio
    try:
        TwilioService().send_whatsapp_message(message_request.user_id, bot_response)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(f"Error sending message: {e}"))
    
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