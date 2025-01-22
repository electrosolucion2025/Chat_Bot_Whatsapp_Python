from typing import Dict

import stripe

from redsys.client import RedirectClient
from redsys.constants import EUR, STANDARD_PAYMENT
from decimal import Decimal as D, ROUND_HALF_UP

from fastapi import HTTPException

from app.core.config import settings

stripe.api_key = settings.stripe_secret_key
stripe.api_version = "2024-09-30.acacia"

def create_stripe_payment_link(order_data: Dict, user_id: str, session_id: str) -> Dict[str, str]:
    """
    Build the line items for the order, including dishes and drinks,
    create Stripe Products/Prices, and generate a Payment Link.
    """
    try:
        line_items = []

        # Procesar platos (dishes)
        for dish in order_data.get("dishes", []):
            # Crear producto principal y precio
            product = stripe.Product.create(name=dish["name"])
            price = stripe.Price.create(
                unit_amount=int(dish["price"] * 100),  # Convertir a céntimos
                currency="eur",
                product=product.id
            )
            line_items.append({
                "price": price.id,
                "quantity": dish.get("quantity", 1)
            })

            # Procesar extras
            for extra in dish.get("extras", []):
                extra_product = stripe.Product.create(name=f"{dish['name']} - {extra['name']}")
                extra_price = stripe.Price.create(
                    unit_amount=int(extra["price"] * 100),
                    currency="eur",
                    product=extra_product.id
                )
                line_items.append({
                    "price": extra_price.id,
                    "quantity": extra.get("quantity", 1)
                })

            # Procesar exclusiones
            for exclusion in dish.get("exclusions", []):
                exclusion_product = stripe.Product.create(
                    name=f"{dish['name']} - Sin {exclusion['name']}",
                )
                exclusion_price = stripe.Price.create(
                    unit_amount=0,  # Exclusiones sin costo
                    currency="eur",
                    product=exclusion_product.id
                )
                line_items.append({
                    "price": exclusion_price.id,
                    "quantity": 1
                })

        # Procesar bebidas (drinks)
        for drink in order_data.get("drinks", []):
            # Crear producto principal y precio
            product = stripe.Product.create(name=drink["name"])
            price = stripe.Price.create(
                unit_amount=int(drink["price"] * 100),  # Convertir a céntimos
                currency="eur",
                product=product.id
            )
            line_items.append({
                "price": price.id,
                "quantity": drink.get("quantity", 1)
            })

        # Crear el Payment Link
        payment_link = stripe.PaymentLink.create(
            line_items=line_items,
            metadata={
                "user_id": user_id,
                "session_id": session_id
            }
        )

        return {"url": payment_link.url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
class PaymentServiceRedsys:
    def __init__(self):
        self.client = RedirectClient(settings.redsys_secret_key)

    def prepare_payment_request(self, order_id: str, amount: float, user_id: str) -> dict:
            """
            Prepara los parámetros necesarios para Redsys.
            :param order_id: ID único del pedido.
            :param amount: Monto del pago (en euros, por ejemplo 10.50).
            :return: Diccionario con los parámetros necesarios para el formulario de pago.
            """
            parameters = {
                "merchant_code": settings.redsys_merchant_code,
                "terminal": "1",
                "transaction_type": STANDARD_PAYMENT,
                "currency": EUR,
                "order": order_id.zfill(12),  # Redsys requiere un ID de 12 caracteres
                "amount": D(amount).quantize(D(".01"), ROUND_HALF_UP),  # Convertimos el monto a dos decimales
                "merchant_url": settings.redsys_success_url,  # URL de notificación para Redsys
                "merchant_data": f"{user_id}",  # Datos adicionales para el comercio
                "merchant_name": "ElectroSolucion",
                "titular": "ElectroSolucion",
                "product_description": "Descripción de los productos",
            }
            
            # Prepara la solicitud
            prepared_request = self.client.prepare_request(parameters)
            
            # Decodifica los parámetros y firma
            prepared_request["Ds_MerchantParameters"] = prepared_request["Ds_MerchantParameters"].decode()
            prepared_request["Ds_Signature"] = prepared_request["Ds_Signature"].decode()
            
            # Prepara los argumentos para el formulario POST
            return prepared_request
        
    def validate_payment_response(self, signature: str, merchant_parameters: str):
        """
        Valida la respuesta recibida de Redsys.
        """
        try:
            # Crear la respuesta Redsys
            response = self.client.create_response(signature, merchant_parameters)
            # Retornar la respuesta si es válida
            return response
        except Exception as e:
            raise ValueError(f"Error al validar la respuesta: {e}")