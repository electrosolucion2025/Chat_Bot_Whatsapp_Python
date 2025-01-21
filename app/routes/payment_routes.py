import stripe

from typing import Dict
from fastapi import APIRouter, HTTPException, Request

from app.core.config import settings
from app.services.twilio_service import TwilioService
from app.services.session_service import session_manager

router = APIRouter(prefix="/payment", tags=["Stripe"])

stripe.api_key = settings.stripe_secret_key
stripe.api_version = "2024-09-30.acacia"

@router.post("/create-payment-link")
def create_payment_link(request: Dict, user_id: str):
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
            line_items = line_items,
            metadata = {
                "user_id": user_id
            }
        )
        
        # Return the URL of the payment link
        return {"url": payment_link.url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/webhook")
async def stripe_webhook(request: Request):
    # Crea el payload desde el cuerpo de la solicitud
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    endpoint_secret = settings.stripe_endpoint_secret  # Asegúrate de tener tu endpoint secreto aquí

    try:
        # Verificar el evento con la firma
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )

        # Manejar el evento
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            print(f"Pago exitoso para la sesión: {session['id']}")

            user_id = session.get("metadata", {}).get("user_id")  # Usa la metadata para obtener el ID del pedido
            if user_id:
                print(f"El user_id es: {user_id}")
            
            print("Enviando mensaje de WhatsApp al usuario...")
            twilio_service = TwilioService()    
            twilio_service.send_whatsapp_message(user_id, "¡Gracias por tu pedido! 🎉 Ya quedó el pago completado.")
            
            print("Limpiando la sesión del usuario...")
            session_manager.clear_session(user_id)

        # Retornar un status 200 para confirmar que el webhook fue recibido correctamente
        return {"status": "success"}

    except ValueError as e:
        # Si no es un evento válido de Stripe
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        # Si la firma no es válida
        raise HTTPException(status_code=400, detail="Invalid signature")