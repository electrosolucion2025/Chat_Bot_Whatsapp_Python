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
def create_payment_link(request: Dict, user_id: str, session_id: str):
    """
    Crea un link de pago para un pedido con los productos, cantidades, extras y exclusiones especificados.
    """
    try:
        line_items = []

        # Iterar sobre cada producto en el pedido
        for dish in request["dishes"]:
            # Crear el producto principal
            product = stripe.Product.create(
                name=dish["name"],
            )

            # Crear el precio para el plato principal
            price = stripe.Price.create(
                unit_amount=int(dish["price"] * 100),  # Convertir a céntimos
                currency="eur",
                product=product.id  # Asociar el precio al producto
            )

            # Añadir el plato principal a los line items
            line_items.append({
                "price": price.id,  # Usar el ID del precio del plato principal
                "quantity": dish.get("quantity", 1)  # Usar la cantidad si está especificada, por defecto 1
            })
            
            # Iterar sobre cada extra en el plato
            for extra in dish["extras"]:
                # Crear un producto para el extra
                extra_product = stripe.Product.create(
                    name=f"{dish['name']} - {extra['name']}",
                )
                
                extra_price = stripe.Price.create(
                    unit_amount=int(extra["price"] * 100),  # Convertir a céntimos
                    currency="eur",
                    product=extra_product.id  # Asociar el precio al producto
                )

                # Añadir el extra a los line items
                line_items.append({
                    "price": extra_price.id,  # Usar el ID del precio del extra
                    "quantity": extra.get("quantity", 1)  # Usar la cantidad si está especificada, por defecto 1
                })

            # Iterar sobre cada exclusión en el plato
            for exclusion in dish["exclusions"]:
                # Crear un producto para la exclusión
                exclusion_product = stripe.Product.create(
                    name=f"{dish['name']} - Sin {exclusion['name']}",
                )
                
                # Crear un precio con costo 0 para la exclusión
                exclusion_price = stripe.Price.create(
                    unit_amount=0,  # Precio 0 para exclusiones
                    currency="eur",
                    product=exclusion_product.id  # Asociar el precio al producto
                )

                # Añadir la exclusión a los line items
                line_items.append({
                    "price": exclusion_price.id,  # Usar el ID del precio de la exclusión
                    "quantity": 1  # Siempre una exclusión
                })

        # Crear el link de pago
        payment_link = stripe.PaymentLink.create(
            line_items=line_items,
            metadata={
                "user_id": user_id,
                "session_id": session_id
            }
        )
        
        # Retornar la URL del link de pago
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

            session_id = session.get("metadata", {}).get("session_id")  # Usa la metadata para obtener el ID de la sesión
            user_id = session.get("metadata", {}).get("user_id")  # Usa la metadata para obtener el ID del usuario

            print("Enviando mensaje de WhatsApp al usuario...")
            twilio_service = TwilioService()    
            twilio_service.send_whatsapp_message(user_id, "¡Gracias por tu pedido! 🎉 Ya quedó el pago completado.")
            
            print(f"Limpiando la sesión del usuario... {session_id}")
            session_manager.clear_session(session_id)

        # Retornar un status 200 para confirmar que el webhook fue recibido correctamente
        return {"status": "success"}

    except ValueError as e:
        # Si no es un evento válido de Stripe
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        # Si la firma no es válida
        raise HTTPException(status_code=400, detail="Invalid signature")