import stripe
from typing import Dict, List

from app.core import config

stripe.api_key = config.Settings().stripe_secret_key

def generate_stripe_line_items(order_data: Dict) -> List[Dict]:
    """
    Generate the line items for the Stripe payment link.
    """
    line_items = []
    
    # Add the dishes to the line items
    for dish in order_data["dishes"]:
        # Add the dish to the line items
        line_items.append({
            "price_data": {
                "currency": "eur",
                "product_data": {
                    "name": dish["name"]
                },
                "unit_amount": int(dish["price"] * 100)
            },
            "quantity": 1
        })
        
        # Add the extras to the line items
        for extra in dish["extras"]:
            line_items.append({
                "price_data": {
                    "currency": "eur",
                    "product_data": {
                        "name": f"{dish['name']} - {extra['name']}"
                    },
                    "unit_amount": int(extra["price"] * 100)
                },
                "quantity": 1
            })
            
    return line_items