import stripe

from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter(prefix="/payment", tags=["Stripe"])

stripe.api_key = settings.stripe_secret_key
stripe.api_version = "2024-09-30.acacia"

class PaymentLinkRequest(BaseModel):
    product_name: str
    amount: float
    redirect_url: Optional[str] = "http://localhost:3000/success"
    
@router.post("/create-payment-link")
async def create_payment_link(request: PaymentLinkRequest):
    """
    Create a payment link for a product with the specified amount.
    """
    try:
        # Convert the amount to cents
        amount = int(request.amount * 100)
        
        # Create Price object
        price = stripe.Price.create(
            unit_amount=amount,
            currency="eur",
            product_data = {
                "name": request.product_name
            }
        )
        
        # Create a payment link using Stripe
        payment_link = stripe.PaymentLink.create(
            line_items = [
                {
                    "price": price.id,
                    "quantity": 1
                },
            ],
            after_completion = {
                "type": "redirect",
                "redirect": { "url": request.redirect_url }
            }
        )
        
        # Return the payment link
        return { "url": payment_link.url }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    endpoint_secret = "secret_key"

    try:
        # Verificar el evento
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )

        # Manejar diferentes tipos de eventos
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            print(f"Pago exitoso para: {session['id']}")
        elif event["type"] == "payment_intent.succeeded":
            intent = event["data"]["object"]
            print(f"PaymentIntent completado: {intent['id']}")

        return {"status": "success"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload")
    
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
