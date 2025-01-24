import os
import ssl
import certifi

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from app.core.config import settings


class EmailService:
    def __init__(self):
        self.api_key = settings.twilio_sendgrid_api_key
        
    def send_email(self, to_email: str, subject: str, html_content: str):
        """
        Sends an email using the SendGrid API.
        """
        os.environ['SSL_CERT_FILE'] = certifi.where()
        os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
        
        # Send the email using 8the SendGrid API
        message = Mail(
            from_email=settings.email_sender,
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )
        
        try:
            sg = SendGridAPIClient(self.api_key, )
            response = sg.send(message)
            
            return {
                "status_code": response.status_code,
                "message": f"Email sent to {to_email}",
                "headers": response.headers
            }
            
        except Exception as e:
            return {
                "status_code": 500,
                "message": f"Error sending email: {e}"
            }
            
# Instantiate the EmailService Global Object
email_service = EmailService()