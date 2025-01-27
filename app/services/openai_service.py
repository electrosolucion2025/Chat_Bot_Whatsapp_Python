import os
import time
import openai
import requests
import logging

from typing import Dict, Optional
from urllib.parse import urlencode
from fastapi import HTTPException
from requests.auth import HTTPBasicAuth

from app.core.config import settings
from app.routes.payment_routes import create_payment_link
from app.services.order_parser_service import parse_bot_message_redsys
from app.services.session_service import session_manager
from app.services.twilio_service import TwilioService

openai.api_key = settings.openai_api_key
client = openai.Client(
    api_key=settings.openai_api_key,
)

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
    try:
        # Get the active session ID or create a new one
        active_session_id = session_id or session_manager.get_session_by_user(user_id)
        if not active_session_id:
            active_session_id = session_manager.create_session(user_id)
        
        # Check if the user is within the message limit
        within_limit, message_count = session_manager.is_within_limit(user_id)
        
        # Validate the session history
        history = session_manager.get_session(active_session_id)
        if not validate_history(history):
            raise HTTPException(status_code=400, detail="Invalid session history")
        
        # Initialize the payment link
        payment_url = None

        # Build the prompt and generate the response
        prompt = build_prompt(history, message)
        bot_response = generate_response(prompt)
        
        # Check if the bot response contains the order summary
        if "Resumen del Pedido:" in bot_response:
            # Parse the order data from the bot response
            order_data = parse_bot_message_redsys(bot_response)
            
            # Add user phone number to the order data
            order_data["user_id"] = user_id
            
            # Add the order data to the session
            session_manager.add_order_data(active_session_id, order_data)
            
            # Extract the order ID and total
            order_id = order_data.get("order_id")  # Extrae el ID del pedido
            amount = float(order_data.get("total", 0))  # Extrae el total, asegurándose de que sea float

            # Params for the payment link
            params = {
                "order_id": order_id,
                "amount": amount,
                "user_id": user_id
            }
            
            # Generate the payment link
            base_url = f"{settings.url_local.rstrip('/')}/payment/payment-form"
            query_string = urlencode(params)      
            payment_url = f"{base_url}?{query_string}"
            
        try:
            TwilioService().send_whatsapp_message(user_id, bot_response)
            
            # Check if the user has less than 10 messages left
            if message_count >= session_manager.max_messages_per_hour - 5:
                warning_message = f"Te quedan {session_manager.max_messages_per_hour - message_count} mensajes antes de alcanzar el límite. El limite se puede reestablecer finalizando una compra o en el lapso de una hora."
                TwilioService().send_whatsapp_message(user_id, warning_message)
            
            if payment_url is not None:
                payment_message = f"Puedes pagar tu pedido en el siguiente enlace: \n\n{payment_url}"
                try:
                    TwilioService().send_whatsapp_message(user_id, payment_message)
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Error sending payment link: {e}")
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error sending message: {e}")

        try:
            # Add the message to the session
            session_manager.add_to_session(active_session_id, user_id, message, bot_response)
        except ValueError as e:
            # Send an error message to the user via Twilio
            error_message = str(e)
            try:
                TwilioService().send_whatsapp_message(user_id, error_message)
                
            except Exception as twilio_error:
                raise HTTPException(status_code=500, detail=f"Error sending error message: {twilio_error}")
            
            raise HTTPException(status_code=400, detail=str(e))

        # Return the session ID and the bot response
        return {
            "session_id": active_session_id,
            "bot": bot_response
        }
        
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
    
def manage_payment_link_stripe(bot_response: str, session_id: str, order_data: dict, user_id: str) -> str:
    """
    Manage the payment link in the bot response
    """
    # Verificar si ya hay un enlace de pago en el bot_response
    payment_link_prefix = "https://buy.stripe.com/"
    lines = bot_response.split("\n")
    bot_response = "\n".join([line for line in lines if payment_link_prefix not in line])

    # Obtener el enlace existente en la sesión
    existing_payment_link = session_manager.get_payment_link(session_id)
    if existing_payment_link:
        session_manager.clear_payment_link(session_id)

    # Crear un nuevo enlace de pago
    payment_link_response = create_payment_link(order_data, user_id, session_id)
    session_manager.add_payment_link(session_id, payment_link_response["url"])

    # Agregar el nuevo enlace al bot_response
    bot_response += f"\n\nPuedes pagar tu pedido en el siguiente enlace: {payment_link_response['url']}"
    
    return bot_response

async def download_audio_from_twilio(media_url: str, user_id: str) -> str:
    """
    Downloads an audio file from Twilio's MediaUrl and saves it in a specific directory within the project.
    :param media_url: URL of the audio file.
    :return: Path to the downloaded file.
    """
    try:
        response = requests.get(
            media_url,
            auth=HTTPBasicAuth(settings.twilio_account_sid, settings.twilio_auth_token)
        )
        response.raise_for_status()
        
        # Define the directory to save the audio files
        audio_dir = os.path.join(os.path.dirname(__file__), 'audio_files')
        os.makedirs(audio_dir, exist_ok=True)
        
        # Define the file path
        user_id_just_numbers = user_id.replace("whatsapp:+", "")
        unique_filename = f"downloaded_audio_{user_id_just_numbers}_{int(time.time())}.mp3"
        file_path = os.path.join(audio_dir, unique_filename)
        
        try:
            # Save the file
            with open(file_path, 'wb') as audio_file:
                audio_file.write(response.content)
            
            return file_path
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error saving audio file: {e}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading audio from twilio: {e}")
        
async def transcribe_audio_with_whisper(audio_path: str) -> str:
    """
    Transcribe the audio file using OpenAI's Whisper API.
    :param audio_path: Path to the audio file.
    :return: Transcribed text.
    """
    try:
        # Open the audio file
        with open(audio_path, "rb") as audio_file:
            # Prepare the data for the Whisper API
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
            )
            
            # Return the transcribed text
            transcribed_text = response.text
            
            return transcribed_text
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error transcribing audio: {e}")