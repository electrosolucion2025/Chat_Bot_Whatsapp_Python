import re

def parse_bot_message(message: str) -> dict:
    """
    Analiza el mensaje del bot para extraer número de mesa, platos, bebidas, extras, exclusiones, cantidades y total.
    """
    # Expresiones regulares para capturar datos relevantes
    table_number_pattern = r"- \*N(?:ú|u)mero de Mesa\*: (\d+)"
    dish_pattern = r"- \*Plato \d+\*: (.+?) - ([\d.]+)€ x(\d+)"
    drink_pattern = r"- \*Bebida\*: (.+?) - ([\d.]+)€ x(\d+)"
    total_pattern = r"- \*Total\*: ([\d.]+)€"

    # Buscar número de mesa
    table_match = re.search(table_number_pattern, message)
    table_number = int(table_match.group(1)) if table_match else None

    # Dividir el mensaje en líneas para procesar extras y exclusiones por contexto
    lines = message.splitlines()

    # Procesar platos y sus extras/exclusiones
    dishes = []
    current_dish = None
    for line in lines:
        # Detectar un plato
        dish_match = re.match(dish_pattern, line)
        if dish_match:
            # Si ya hay un plato actual, agregarlo a la lista antes de procesar el siguiente
            if current_dish:
                dishes.append(current_dish)

            # Crear un nuevo plato
            dish_name, dish_price, quantity = dish_match.groups()
            current_dish = {
                "name": dish_name.strip(),
                "price": float(dish_price),
                "quantity": int(quantity),
                "extras": [],
                "exclusions": [],
            }

        # Detectar un extra para el plato actual
        extra_match = re.match(r"--> \*Extra\*: \*?(.+?)\*? - ([\d.]+)€ x(\d+)", line)
        if extra_match and current_dish:
            extra_name, extra_price, extra_quantity = extra_match.groups()
            current_dish["extras"].append({
                "name": extra_name.strip(),
                "price": float(extra_price),
                "quantity": int(extra_quantity),
            })

        # Detectar una exclusión para el plato actual
        exclusion_match = re.match(r"--> \*Sin\*: (.+)", line)
        if exclusion_match and current_dish:
            exclusion_name = exclusion_match.group(1)
            current_dish["exclusions"].append({"name": exclusion_name.strip()})

    # Agregar el último plato procesado
    if current_dish:
        dishes.append(current_dish)

    # Procesar bebidas
    drinks_matches = re.findall(drink_pattern, message)
    drinks = [
        {
            "name": drink_name.strip(),
            "price": float(drink_price),
            "quantity": int(quantity),
        }
        for drink_name, drink_price, quantity in drinks_matches
    ]

    # Buscar el precio total
    total_match = re.search(total_pattern, message)
    total_price = float(total_match.group(1)) if total_match else 0.0

    # Retornar los datos parseados
    return {
        "table_number": table_number,
        "dishes": dishes,
        "drinks": drinks,
        "total": total_price,
    }
