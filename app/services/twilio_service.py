from twilio.rest import Client
from app.core.config import settings

class TwilioService:
    def __init__(self):
        # Init Twilio client with credentials
        self.client = Client(settings.twilio_account_sid, settings.twilio_auth_token) # Twilio client
        self.from_phone = f"whatsapp:{settings.twilio_phone_number}" # Twilio phone number
        
    def send_whatsapp_message(self, to_phone: str, message: str):
        # Send message to phone number
        try:
            message = self.client.messages.create(
                body = message,
                from_ = self.from_phone,
                to = to_phone
            )
            
            return {
                "sid": message.sid,
                "status": message.status,
                "to": message.to,
                "body": message.body
            }
        
        except Exception as e:
            raise Exception(f"Error sending message: {e}")