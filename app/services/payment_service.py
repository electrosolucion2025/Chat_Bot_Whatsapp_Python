from typing import Dict

import stripe

from redsys.client import RedirectClient
from redsys.constants import EUR, STANDARD_PAYMENT
from decimal import Decimal as D, ROUND_HALF_UP

from fastapi import HTTPException

from app.core.config import settings
from app.services.email_service import EmailService
from app.services.session_service import session_manager

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

        # Guardar el enlace de pago en la sesión
        session_manager.add_payment_link(session_id, payment_link.url)

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
            # Obtener la sesión del usuario
            # session = session_manager.get_session_by_user(user_id)
            
            # Obtener los datos del pedido
            # order_data = session_manager.get_order_data(session)
            
            # Generar la descripción de los productos
            # product_description = self.generate_product_description(order_data)
            
            # Parámetros para la solicitud de pago
            parameters = {
                "merchant_code": settings.redsys_merchant_code,
                "terminal": "1",
                "transaction_type": STANDARD_PAYMENT,
                "currency": EUR,
                "order": order_id.zfill(12),  # Redsys requiere un ID de 12 caracteres
                "amount": D(amount).quantize(D(".01"), ROUND_HALF_UP),  # Convertimos el monto a dos decimales
                "merchant_url": settings.redsys_notification_url,  # URL de notificación para Redsys
                "merchant_data": f"{user_id}",  # Datos adicionales para el comercio
                "merchant_name": "ElectroSolucion",
                "titular": "ElectroSolucion",
                "product_description": "Descripción de los productos...",
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
        
    def generate_product_description(order_data: dict, max_length: int = 200) -> str:
        """
        Genera una descripción de los productos para el campo product_description de Redsys.
        
        Args:
            order_data (dict): Datos del pedido que incluyen platos, bebidas y otros detalles.
            max_length (int): Longitud máxima permitida para la descripción.
        
        Returns:
            str: Descripción resumida de los productos con un límite de longitud.
        """
        description_parts = []

        # Procesar los platos
        dishes = order_data.get("dishes", [])
        for dish in dishes:
            dish_desc = dish.get("name", "Producto sin nombre")
            
            # Añadir extras si existen
            extras = dish.get("extras", [])
            if extras:
                extras_desc = ", ".join([f"{extra['name']} (+{extra['price']:.2f}€)" for extra in extras])
                dish_desc += f" (Extras: {extras_desc})"
            
            # Añadir exclusiones si existen
            exclusions = dish.get("exclusions", [])
            if exclusions:
                exclusions_desc = ", ".join([exclusion["name"] for exclusion in exclusions])
                dish_desc += f" (Sin: {exclusions_desc})"
            
            # Añadir cantidad y precio
            quantity = dish.get("quantity", 1)
            price = dish.get("price", 0.0)
            dish_desc += f" x{quantity} - {price:.2f}€"
            
            description_parts.append(dish_desc)

        # Procesar las bebidas
        drinks = order_data.get("drinks", [])
        for drink in drinks:
            drink_desc = drink.get("name", "Bebida sin nombre")
            quantity = drink.get("quantity", 1)
            price = drink.get("price", 0.0)
            drink_desc += f" x{quantity} - {price:.2f}€"
            description_parts.append(drink_desc)

        # Unir todos los productos en una única descripción
        product_description = "; ".join(description_parts)

        # Añadir puntos suspensivos si excede el límite de longitud
        if len(product_description) > max_length:
            product_description = product_description[:max_length - 3] + "..."
        
        return product_description

async def send_payment_confirmation(to_email: str, order_data: dict):
    """
    Sends a payment confirmation email to the user with a styled ticket-like format,
    including the table number and customer phone number formatted nicely.
    """
    def format_phone_number(phone: str) -> str:
        """
        Formats a phone number into a human-readable format.
        Example: "whatsapp:+34623288679" -> "+34 623 28 86 79"
        """
        # Elimina el prefijo "whatsapp:" si existe
        if phone.startswith("whatsapp:+"):
            phone = phone.replace("whatsapp:+", "")
        
        # Formatea el número
        if len(phone) > 3:
            return f"+{phone[0:2]} {phone[2:5]} {phone[5:7]} {phone[7:9]} {phone[9:]}"
        return phone  # Si no es un número estándar, lo devuelve como está

    subject = f"Confirmación de Pago - Pedido #{order_data.get('order_id')}"
    
    # Datos
    table_number = order_data.get("table_number", "N/A")  # Número de mesa
    raw_customer_phone = order_data.get("user_id", "N/A")  # Teléfono del cliente
    customer_phone = format_phone_number(raw_customer_phone)  # Formatear teléfono

    # HTML con estilo para el ticket
    html_content = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; border: 1px solid #ddd; border-radius: 8px; padding: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); position: relative;">
        <!-- Teléfono del cliente -->
        <p style="position: absolute; top: 16px; right: 16px; font-size: 0.9em; color: #555; margin: 0;">
            <strong style="color: #007BFF;">Teléfono cliente:</strong> {customer_phone}
        </p>

        <!-- Encabezado -->
        <h1 style="text-align: center; color: #007BFF;">¡Gracias por tu pedido!</h1>
        
        <!-- Número de mesa -->
        <p style="text-align: center; font-size: 1.2em; color: #555;">
            Mesa: <strong style="color: #333;">{table_number}</strong>
        </p>
        <p style="text-align: center;">Aquí tienes los detalles del pedido:</p>
        
        <!-- Tabla de productos -->
        <table style="width: 100%; border-collapse: collapse; margin-top: 16px;">
            <thead>
                <tr style="background-color: #f4f4f4; border-bottom: 1px solid #ddd;">
                    <th style="padding: 8px; text-align: left;">Producto</th>
                    <th style="padding: 8px; text-align: center;">Cantidad</th>
                    <th style="padding: 8px; text-align: right;">Precio</th>
                </tr>
            </thead>
            <tbody>
                {generate_table_rows_with_extras(order_data.get("dishes", []), order_data.get("drinks", []))}
            </tbody>
        </table>
        
        <!-- Total -->
        <p style="text-align: right; font-size: 1.2em; margin-top: 16px;">
            <strong>Total: {order_data.get("total", 0)} €</strong>
        </p>
        
        <!-- Pie de página -->
        <p style="text-align: center; margin-top: 32px; font-size: 0.9em; color: #555;">
            ¡Esperamos que estés contento!<br>
            Si tienes alguna pregunta, no dudes en contactarnos.
        </p>
    </div>
    """
    
    # Servicio de envío de email
    email_service = EmailService()
    email_service.send_email(to_email, subject, html_content)


def generate_table_rows_with_extras(dishes: list, drinks: list) -> str:
    """
    Generates HTML table rows for the dishes and drinks, including extras and exclusions.
    """
    rows = ""

    # Procesar los platos
    for dish in dishes:
        rows += f"""
        <tr>
            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{dish['name']}</td>
            <td style="padding: 8px; text-align: center; border-bottom: 1px solid #ddd;">{dish['quantity']}</td>
            <td style="padding: 8px; text-align: right; border-bottom: 1px solid #ddd;">{dish['price']} €</td>
        </tr>
        """

        # Procesar los extras si existen
        if "extras" in dish and dish["extras"]:
            extras = ", ".join(
                [f"{extra['name']} (+{extra['price']} €)" for extra in dish["extras"]]
            )
            rows += f"""
            <tr>
                <td colspan="3" style="padding: 4px 8px; font-size: 0.9em; color: #555; border-bottom: 1px solid #ddd;">
                    <em>Extras: {extras}</em>
                </td>
            </tr>
            """

        # Procesar las exclusiones si existen
        if "exclusions" in dish and dish["exclusions"]:
            exclusions = ", ".join([exclusion["name"] for exclusion in dish["exclusions"]])
            rows += f"""
            <tr>
                <td colspan="3" style="padding: 4px 8px; font-size: 0.9em; color: #555; border-bottom: 1px solid #ddd;">
                    <em>Sin: {exclusions}</em>
                </td>
            </tr>
            """

    # Procesar las bebidas
    for drink in drinks:
        rows += f"""
        <tr>
            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{drink['name']}</td>
            <td style="padding: 8px; text-align: center; border-bottom: 1px solid #ddd;">{drink['quantity']}</td>
            <td style="padding: 8px; text-align: right; border-bottom: 1px solid #ddd;">{drink['price']} €</td>
        </tr>
        """

    return rows