from typing import Dict, Optional

import openai
from fastapi import HTTPException

from app.core.config import settings
from app.routes.payment_routes import create_payment_link
from app.services.order_parser_service import parse_bot_message
from app.services.session_service import session_manager
from app.services.twilio_service import TwilioService

openai.api_key = settings.openai_api_key

def build_prompt(history: list[dict], user_message: str) -> str:
    """
    # Build the prompt using the history and the user's message
    """
    lines = []
    for entry in history:
        # Verify if the entry has both user and bot messages
        if "user" in entry and "bot" in entry:
            lines.append(f"Usuario: {entry['user']}\nBot: {entry['bot']}")
        elif "bot" in entry:  # Only bot messages 
            lines.append(entry["bot"])

    # Add the user's message
    lines.append(f"Usuario: {user_message}\nBot:")
    return "\n".join(lines)

def validate_history(history: list[dict]) -> bool:
    """
    Validate if the history has the required format
    """
    for entry in history:
        if not isinstance(entry, dict):
            return False
        
        if "bot" not in entry and "user" not in entry:
            return False
    
    return True

def generate_response(prompt: str):
    """
    Generate a response from the OpenAI API
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
        )

        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"
    
def process_incoming_message(user_id: str, message: str, session_id: Optional[str] = None) -> Dict[str, str]:
    """
    Orchestrates the entire message flow:
    1. Obtain/create the session.
    2. Validate the history.
    3. Generate the response from OpenAI.
    4. Check if there is 'Order Summary:' and create a payment link.
    5. Send the message via Twilio.
    6. Return the necessary data for the endpoint.
    """
    # Get the active session ID or create a new one
    active_session_id = session_id or session_manager.get_session_by_user(user_id)
    if not active_session_id:
        active_session_id = session_manager.create_session(user_id)

    # VAlidate the session history
    history = session_manager.get_session(active_session_id)
    if not validate_history(history):
        raise HTTPException(status_code=400, detail="Invalid session history")

    # Build the prompt and generate the response
    prompt = build_prompt(history, message)
    bot_response = generate_response(prompt)

    # Check if the bot response contains the order summary
    if "Resumen del Pedido:" in bot_response:
        order_data = parse_bot_message(bot_response)

        existing_payment_link = session_manager.get_payment_link(active_session_id)
        if existing_payment_link:
            session_manager.clear_payment_link(active_session_id)

        payment_link_response = create_payment_link(order_data, user_id, active_session_id)

        # Add the payment link to the session
        session_manager.add_payment_link(active_session_id, payment_link_response["url"])
        bot_response += f"\n\nPuedes pagar tu pedido en el siguiente enlace: {payment_link_response['url']}"

    # Add the message to the session
    session_manager.add_to_session(active_session_id, user_id, message, bot_response)

    try:
        # Send the message via Twilio
        TwilioService().send_whatsapp_message(user_id, bot_response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending message: {e}")

    # Return the session ID and the bot response
    return {
        "session_id": active_session_id,
        "bot": bot_response
    }