import re

def parse_bot_message(message: str) -> dict:
    """
    Analiza el mensaje del bot para extraer número de mesa, platos con sus extras, cantidades y total.
    """
    # Expresión regular para capturar platos con extras y cantidades
    dish_with_extras_pattern = r"- \*Plato \d+\*: (.+?) - ([\d.]+)€ x(\d+)((?:\n--> \*Extra\*: \*?(.+?)\*? - ([\d.]+)€ x(\d+))*)"
    table_number_pattern = r"- \*N(?:ú|u)mero de Mesa\*: (\d+)"
    total_pattern = r"- \*Total\*: ([\d.]+)€"

    # Buscar número de mesa
    table_match = re.search(table_number_pattern, message)
    table_number = int(table_match.group(1)) if table_match else None

    # Buscar platos con extras
    dishes_with_extras = re.findall(dish_with_extras_pattern, message)

    # Procesar platos con extras
    dishes = []
    for dish_name, dish_price, quantity, extras_raw, extra_name, extra_price, extra_quantity in dishes_with_extras:
        # Manejar la cantidad
        quantity = int(quantity) if quantity else 1

        # Manejar los extras
        extras = []
        if extras_raw:
            # Capturar cada extra con nombre, precio y cantidad
            extras = [
                {"name": extra_name.strip(), "price": float(extra_price), "quantity": int(extra_quantity)}
                for extra_name, extra_price, extra_quantity in re.findall(r"--> \*Extra\*: \*?(.+?)\*? - ([\d.]+)€ x(\d+)", extras_raw)
            ]
        
        # Añadir plato con su cantidad y extras
        dishes.append({
            "name": dish_name.strip(),
            "price": float(dish_price),
            "quantity": quantity,
            "extras": extras,
        })

    # Buscar el precio total
    total_match = re.search(total_pattern, message)
    total_price = float(total_match.group(1)) if total_match else 0.0

    # Retornar los datos parseados
    return {
        "table_number": table_number,
        "dishes": dishes,
        "total": total_price,
    }