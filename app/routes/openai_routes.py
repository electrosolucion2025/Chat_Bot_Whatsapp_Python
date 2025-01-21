from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.routes.payment_routes import create_payment_link
from app.services.openai_service import build_prompt, generate_response, validate_history
from app.services.order_parser_service import parse_bot_message
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
    session_id = request.session_id or session_manager.get_session_by_user(request.user_id)
    
    # If no session is found, create a new session
    if not session_id:
        session_id = session_manager.create_session(request.user_id)
    
    # Get the session's history
    history = session_manager.get_session(session_id)
    
    # Validate the history
    if not validate_history(history):
        raise HTTPException(status_code=400, detail="Invalid session history")
    
    # Build the prompt using the history and the user's message
    prompt = build_prompt(history, request.message)
    
    # Generate the response using OpenAI
    bot_response = generate_response(prompt)
    
    # Check if the bot response contains "Resumen del Pedido:"
    if "Resumen del Pedido:" in bot_response:
        # Parse the bot response to get the order summary
        order_data = parse_bot_message(bot_response)
        
        # Get link to payment
        payment_link_response = create_payment_link(order_data)
        
        # Add the payment link to the bot response
        bot_response += f"\n\nPuedes pagar tu pedido en el siguiente enlace: {payment_link_response['url']}"
    
    # Add the user message and bot response to the session
    session_manager.add_to_session(session_id, request.user_id, request.message, bot_response)
    
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