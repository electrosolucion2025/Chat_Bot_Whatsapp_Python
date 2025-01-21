import re


def parse_bot_message(message: str) -> dict:
    """
    Analiza el mensaje del bot para extraer número de mesa, platos con sus extras, exclusiones, cantidades y total.
    """
    # Expresiones regulares para capturar datos relevantes
    table_number_pattern = r"- \*N(?:ú|u)mero de Mesa\*: (\d+)"
    dish_pattern = r"- \*Plato \d+\*: (.+?) - ([\d.]+)€ x(\d+)"
    extra_pattern = r"--> \*Extra\*: \*?(.+?)\*? - ([\d.]+)€ x(\d+)"
    exclusion_pattern = r"--> \*Sin\*: (.+)"
    total_pattern = r"- \*Total\*: ([\d.]+)€"

    # Buscar número de mesa
    table_match = re.search(table_number_pattern, message)
    table_number = int(table_match.group(1)) if table_match else None

    # Buscar platos
    dishes_matches = re.findall(dish_pattern, message)
    dishes = []

    for dish_name, dish_price, quantity in dishes_matches:
        # Manejar la cantidad
        quantity = int(quantity)

        # Buscar extras asociados al plato actual
        extras_raw = re.findall(extra_pattern, message)
        extras = [
            {"name": name.strip(), "price": float(price), "quantity": int(extra_quantity)}
            for name, price, extra_quantity in extras_raw
        ]

        # Buscar exclusiones asociadas al plato actual
        exclusions_raw = re.findall(exclusion_pattern, message)
        exclusions = [{"name": exclusion.strip()} for exclusion in exclusions_raw]

        # Agregar el plato con sus extras y exclusiones
        dishes.append({
            "name": dish_name.strip(),
            "price": float(dish_price),
            "quantity": quantity,
            "extras": extras,
            "exclusions": exclusions,
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
