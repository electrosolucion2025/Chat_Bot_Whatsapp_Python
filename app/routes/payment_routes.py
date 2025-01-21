import stripe

from typing import Dict, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter(prefix="/payment", tags=["Stripe"])

stripe.api_key = settings.stripe_secret_key
stripe.api_version = "2024-09-30.acacia"

@router.post("/create-payment-link")
def create_payment_link(request: Dict):
    """
    Crea un link de pago para un pedido con los productos, cantidades y extras especificados.
    """
    try:
        line_items = []

        # Iterate over each product in the order
        for dish in request["dishes"]:
            # First, create the product for the main dish
            product = stripe.Product.create(
                name=dish["name"],
            )

            # Now create the price for the main dish
            price = stripe.Price.create(
                unit_amount=int(dish["price"] * 100),  # Convert to cents
                currency="eur",
                product=product.id  # Associate the price with the product
            )

            # Add the main dish to the line items
            line_items.append({
                "price": price.id,  # Use the ID of the main dish price
                "quantity": dish.get("quantity", 1)  # Use the quantity if provided, default to 1
            })
            
            # Iterate over each extra in the dish
            for extra in dish["extras"]:
                # Create a product for the extra
                extra_product = stripe.Product.create(
                    name=f"{dish['name']} - {extra['name']}",
                )
                
                extra_price = stripe.Price.create(
                    unit_amount=int(extra["price"] * 100),  # Convert to cents
                    currency="eur",
                    product=extra_product.id  # Associate the price with the product
                )

                # Add the extra to the line items
                line_items.append({
                    "price": extra_price.id,  # Use the ID of the extra price
                    "quantity": 1
                })

        # Create the payment link
        payment_link = stripe.PaymentLink.create(
            line_items=line_items
        )
        
        # Return the URL of the payment link
        return {"url": payment_link.url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    endpoint_secret = "whsec_9617e1eac9cf1e1da160d96caa93ddc1aefb95de15bab74d9803d8d4613b8d6d"

    try:
        # Verify the event by constructing it
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )

        # Handle the event
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
