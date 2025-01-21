from typing import Dict

import stripe
from fastapi import APIRouter, HTTPException, Request

from app.core.config import settings
from app.services.payment_service import create_stripe_payment_link
from app.services.session_service import session_manager
from app.services.twilio_service import TwilioService

router = APIRouter(prefix="/payment", tags=["Stripe"])

@router.post("/create-payment-link")
def create_payment_link(request: Dict, user_id: str, session_id: str) -> Dict[str, str]:
    """
    Crea un link de pago para un pedido con los productos, cantidades, extras y exclusiones especificados.
    """
    return create_stripe_payment_link(request, user_id, session_id)


@router.post("/webhook")
async def stripe_webhook(request: Request) -> Dict[str, str]:
    """
    Handle Stripe webhook events such as payment completion.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    endpoint_secret = settings.stripe_endpoint_secret

    try:
        event = create_stripe_event(payload, sig_header, endpoint_secret)  # ver más abajo
        handle_stripe_event(event)
        return {"status": "success"}

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid signature")


def create_stripe_event(payload: bytes, sig_header: str, endpoint_secret: str):
    """
    Construye el evento usando la firma de Stripe.
    """
    return stripe.Webhook.construct_event(
        payload, sig_header, endpoint_secret
    )


def handle_stripe_event(event) -> None:
    """
    Maneja la lógica principal de Stripe Webhook.
    """
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        session_id = session.get("metadata", {}).get("session_id")
        user_id = session.get("metadata", {}).get("user_id")

        # Enviar mensaje de confirmación
        TwilioService().send_whatsapp_message(user_id, "¡Gracias por tu pedido! 🎉 Tu pago se ha completado.")
        session_manager.clear_session(session_id)
        
    else:
        # Manejar otros tipos de eventos si lo necesitas
        print(f"Evento de Stripe no manejado: {event['type']}")
