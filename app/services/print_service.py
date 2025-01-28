from typing import Dict

def generate_ticket_text(order_data: Dict) -> str:
    """
    Genera el texto del ticket en formato string mejorado.

    Args:
        order_data (Dict): Datos del pedido, incluyendo ID, número de mesa, platos, bebidas y total.

    Returns:
        str: Texto formateado del ticket.
    """
    ticket = []

    # Cabecera del ticket
    ticket.append("     Restaurante El Mundo del Campero\n")
    ticket.append("          ¡Gracias por tu compra!\n")
    ticket.append("================================\n")

    # Información del pedido
    ticket.append(f"Pedido ID: {order_data['order_id']}\n")
    ticket.append(f"Mesa: {order_data['table_number']}\n")
    ticket.append("================================\n")

    # Platos
    if 'dishes' in order_data and order_data['dishes']:
        ticket.append("🟢 Platos:\n")
        for dish in order_data['dishes']:
            ticket.append(f" • {dish['name']} x{dish['quantity']}\n")
            ticket.append(f"   Precio: ${dish['price']:.2f}\n")
            if 'extras' in dish and dish['extras']:
                ticket.append("   Extras:\n")
                for extra in dish['extras']:
                    ticket.append(f"     → {extra['name']} x{extra['quantity']} - ${extra['price']:.2f}\n")
            if 'exclusions' in dish and dish['exclusions']:
                ticket.append("   Sin:\n")
                for exclusion in dish['exclusions']:
                    ticket.append(f"     × {exclusion['name']}\n")

    # Bebidas
    if 'drinks' in order_data and order_data['drinks']:
        ticket.append("================================\n")
        ticket.append("🟡 Bebidas:\n")
        for drink in order_data['drinks']:
            ticket.append(f" • {drink['name']} x{drink['quantity']}\n")
            ticket.append(f"   Precio: ${drink['price']:.2f}\n")

    # Total
    ticket.append("================================\n")
    ticket.append(f"🔵 Total: ${order_data['total']:.2f}\n")

    # Mensaje de despedida
    ticket.append("================================\n")
    ticket.append("  ¡Esperamos verte pronto!\n")
    ticket.append("\n\n\n")  # Espacios para corte automático
    
    # Comando de corte
    ticket.append("\x1D\x56\x42\x00")  # ESC/POS: Comando para cortar el papel

    return ''.join(ticket)
