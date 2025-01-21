from typing import Dict

import stripe
from fastapi import HTTPException

from app.core.config import settings

stripe.api_key = settings.stripe_secret_key
stripe.api_version = "2024-09-30.acacia"

def create_stripe_payment_link(order_data: Dict, user_id: str, session_id: str) -> Dict[str, str]:
    """
    Build the line items for the order, create Stripe Products/Prices
    and generate a Payment Link.
    """
    try:
        line_items = []

        for dish in order_data["dishes"]:
            # Crear producto principal y precio
            product = stripe.Product.create(name=dish["name"])
            price = stripe.Price.create(
                unit_amount=int(dish["price"] * 100),
                currency="eur",
                product=product.id
            )
            line_items.append({
                "price": price.id,
                "quantity": dish.get("quantity", 1)
            })

            # Procesar extras
            for extra in dish["extras"]:
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
            for exclusion in dish["exclusions"]:
                exclusion_product = stripe.Product.create(
                    name=f"{dish['name']} - Sin {exclusion['name']}",
                )
                exclusion_price = stripe.Price.create(
                    unit_amount=0,
                    currency="eur",
                    product=exclusion_product.id
                )
                line_items.append({
                    "price": exclusion_price.id,
                    "quantity": 1
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
