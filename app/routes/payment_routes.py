import stripe
import base64
import json
import re
from typing import Dict
from urllib.parse import parse_qs, unquote

from fastapi.responses import HTMLResponse
from fastapi import APIRouter, HTTPException, Request

from app.core.config import settings
from app.services.payment_service import PaymentServiceRedsys, create_stripe_payment_link, send_payment_confirmation
from app.services.session_service import session_manager
from app.services.twilio_service import TwilioService

router = APIRouter(prefix="/payment", tags=["Stripe"])
payment_service_redsys = PaymentServiceRedsys()

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

@router.post("/start", response_class=HTMLResponse)
def start_payment(order_id: str, amount: float, user_id: str):
    """
    Genera el formulario de pago para Redsys.
    """
    try:
        # Aquí pasamos correctamente ambos parámetros a la función
        form_parameters =  payment_service_redsys.prepare_payment_request(order_id, amount, user_id)
        form_html = f"""
        <html>
            <head>
                <title>Redirigiendo al pago...</title>
            </head>
            <body onload="document.forms['redsysForm'].submit()">
                <p>Redirigiéndote a la pasarela de pago, por favor espera...</p>
                <form id="redsysForm" name="redsysForm" action="https://sis-t.redsys.es:25443/sis/realizarPago" method="post">
                    <input type="hidden" name="Ds_SignatureVersion" value="HMAC_SHA256_V1" />
                    <input type="hidden" name="Ds_MerchantParameters" value="{form_parameters['Ds_MerchantParameters']}" />
                    <input type="hidden" name="Ds_Signature" value="{form_parameters['Ds_Signature']}" />
                    <noscript>
                        <p>Si no eres redirigido automáticamente, haz clic en el botón:</p>
                        <button type="submit">Pagar</button>
                    </noscript>
                </form>
            </body>
        </html>
        """
        return form_html
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.post("/success")
async def payment_response(request: Request):
    """
    Maneja la respuesta de Redsys después del pago.
    """
    try:
        # Inspeccionar el contenido crudo de la solicitud
        body = await request.body()

        # Parsear los datos manualmente
        parsed_body = parse_qs(body.decode("utf-8"))

        # Extraer parámetros
        Ds_MerchantParameters = parsed_body.get("Ds_MerchantParameters", [None])[0]
        Ds_Signature = parsed_body.get("Ds_Signature", [None])[0]

        # Validar que los parámetros estén presentes
        if not Ds_MerchantParameters or not Ds_Signature:
            raise HTTPException(status_code=400, detail="Missing required parameters")

        # Decodificar Ds_MerchantParameters de Base64 a JSON
        try:
            decoded_parameters = base64.b64decode(Ds_MerchantParameters).decode("utf-8")
            parameters = json.loads(decoded_parameters)
            
        except Exception as decode_error:
            raise HTTPException(status_code=400, detail=f"Error decodificando Ds_MerchantParameters: {decode_error}")

        # Extraer el campo Ds_MerchantData
        merchant_data = parameters.get("Ds_MerchantData")
        if not merchant_data:
            raise HTTPException(status_code=400, detail="Ds_MerchantData no encontrado")

        # Decodificar Ds_MerchantData si está en URL-encoded
        decoded_merchant_data = unquote(merchant_data)

        # Extraer el número de WhatsApp usando regex
        match = re.search(r"\+?\d+", decoded_merchant_data)
        whatsapp_number = match.group() if match else None
        
        if not whatsapp_number:
            raise HTTPException(status_code=400, detail="No se encontró un número de WhatsApp")
        
        # Obtener la sesión del usuario
        session_id = session_manager.get_session_by_user(f"whatsapp:{whatsapp_number}")
        
        # Enviar email de confirmación a la empresa 
        order_data = session_manager.get_order_data(session_id) 
        
        # Enviar email de confirmación a la empresa
        send_payment_confirmation(settings.email_company, order_data) 
        
        # Limpiar los datos del pedido
        session_manager.clear_order_data(session_id)

        # Enviar mensaje de confirmación vía Twilio
        try:
            TwilioService().send_whatsapp_message(f"whatsapp:{whatsapp_number}", "¡Gracias por tu pedido! 🎉 Tu pago se ha completado.")
        except Exception as twilio_error:
            raise HTTPException(status_code=500, detail=f"Error enviando mensaje por WhatsApp: {twilio_error}")

        # Limpiar la sesión del usuario
        session_id = session_manager.get_session_by_user(f"whatsapp:{whatsapp_number}")
        session_manager.clear_session(session_id)

        return {"status": "success", "message": "Pago realizado con éxito"}

    except Exception as e:
        print(f"Error procesando la respuesta: {e}")  # Log del error
        raise HTTPException(status_code=400, detail=f"Error procesando la respuesta: {str(e)}")
    
@router.get("/payment-form", response_class=HTMLResponse)
def render_payment_form(order_id: str, amount: float, user_id: str):
    """
    Renderiza el formulario de pago generado por Redsys.
    """
    try:
        # Llama a `start_payment` para generar el formulario
        form_html = start_payment(order_id, amount, user_id)
        return HTMLResponse(content=form_html, status_code=200)
    except Exception as e:
        return HTMLResponse(content=f"<h1>Error generando el formulario: {str(e)}</h1>", status_code=500)