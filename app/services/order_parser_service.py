import re
from datetime import datetime
import uuid

def parse_bot_message_stripe(message: str) -> dict:
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

def parse_bot_message_redsys(message: str) -> dict:
    """
    Analiza el mensaje del bot para extraer número de mesa, platos, bebidas, extras, exclusiones y cantidades.
    Calcula el total automáticamente y genera un número de pedido único (máximo 12 caracteres).
    """
    # Expresiones regulares para capturar datos relevantes
    table_number_pattern = r"- \*N(?:ú|u)mero de Mesa\*: (\d+)"
    dish_pattern = r"- \*Plato \d+\*: (.+?) - ([\d.]+)€ x(\d+)"
    drink_pattern = r"- \*Bebida\*: (.+?) - ([\d.]+)€ x(\d+)"

    # Buscar número de mesa
    table_match = re.search(table_number_pattern, message)
    table_number = int(table_match.group(1)) if table_match else None

    # Dividir el mensaje en líneas para procesar extras y exclusiones por contexto
    lines = message.splitlines()

    # Procesar platos y sus extras/exclusiones
    dishes = []
    current_dish = None
    total_price = 0.0  # Para calcular el total

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
            # Añadir el costo del plato al total
            total_price += float(dish_price) * int(quantity)

        # Detectar un extra para el plato actual
        extra_match = re.match(r"--> \*Extra\*: \*?(.+?)\*? - ([\d.]+)€ x(\d+)", line)
        if extra_match and current_dish:
            extra_name, extra_price, extra_quantity = extra_match.groups()
            current_dish["extras"].append({
                "name": extra_name.strip(),
                "price": float(extra_price),
                "quantity": int(extra_quantity),
            })
            # Añadir el costo del extra al total
            total_price += float(extra_price) * int(extra_quantity)

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
    drinks = []
    for drink_name, drink_price, quantity in drinks_matches:
        drinks.append({
            "name": drink_name.strip(),
            "price": float(drink_price),
            "quantity": int(quantity),
        })
        # Añadir el costo de la bebida al total
        total_price += float(drink_price) * int(quantity)

    # Generar un timestamp reducido (8 caracteres)
    now = datetime.now()
    timestamp = now.strftime("%y%m%d%H")  # Año, mes, día, hora (8 caracteres)

    # Generar un número único a partir de UUID
    uuid_numeric = int(uuid.uuid4().int)  # Convertir UUID a un entero
    uuid_suffix = str(uuid_numeric)[-4:]  # Tomar los últimos 4 dígitos

    # Combinar timestamp reducido y sufijo
    order_id = timestamp + uuid_suffix

    # Retornar los datos parseados
    return {
        "order_id": order_id,
        "table_number": table_number,
        "dishes": dishes,
        "drinks": drinks,
        "total": round(total_price, 2),  # Redondear el total a 2 decimales
    }