import re

def parse_bot_message(message: str) -> dict:
    """
    Analiza el mensaje del bot para extraer número de mesa, platos con sus extras, cantidades y total.
    """
    # Regex patterns to match table number, dishes with extras, and total price
    dish_with_extras_pattern = r"- \*Plato \d+\*: (.+?) - ([\d.]+)€(?: x(\d+))?((?:\n--> .+? - [\d.]+€)*)"
    table_number_pattern = r"- \*N(?:ú|u)mero de Mesa\*: (\d+)"
    total_pattern = r"- \*Total\*: ([\d.]+)€"

    # Look for the table number
    table_match = re.search(table_number_pattern, message)
    table_number = int(table_match.group(1)) if table_match else None

    # Search for dishes with extras
    dishes_with_extras = re.findall(dish_with_extras_pattern, message)

    # Parse each dish with extras
    dishes = []
    for dish_name, dish_price, quantity, extras_raw in dishes_with_extras:
        # Handle the quantity
        quantity = int(quantity) if quantity else 1

        # Handle the extras
        extras = []
        if extras_raw:
            extra_pattern = r"--> \*Extra\*: (.+?) - ([\d.]+)€"
            extras = [
                {"name": name.strip(), "price": float(price)}
                for name, price in re.findall(extra_pattern, extras_raw)
            ]
        dishes.append({
            "name": dish_name.strip(),
            "price": float(dish_price),
            "quantity": quantity,
            "extras": extras,
        })

    # Look for the total price
    total_match = re.search(total_pattern, message)
    total_price = float(total_match.group(1)) if total_match else 0.0

    # Return the parsed data
    return {
        "table_number": table_number,
        "dishes": dishes,
        "total": total_price,
    }
