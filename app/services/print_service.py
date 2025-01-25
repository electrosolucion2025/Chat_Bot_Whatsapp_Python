import socket
from escpos.printer import Network
from typing import List, Dict

# def print_ticket(order_data: Dict):
#     """
#     Imprime un ticket con los datos del pedido.

#     Args:
#         order_data (Dict): Datos del pedido, incluyendo ID, número de mesa, platos, bebidas y total.
#     """
#     try:
#         # Configura la conexión con la impresora térmica
#         printer = Network("192.168.1.149")  # Cambia la IP según la configuración de tu impresora

#         # Cabecera del ticket
#         printer.set(align='center', width=2, height=2)
#         printer.text("Restaurante El Mundo del Campero\n")
#         printer.set(align='center')
#         printer.text("¡Gracias por tu compra!\n")
#         printer.text("--------------------------------\n")

#         # Información del pedido
#         printer.set(align='left')
#         printer.text(f"Pedido ID: {order_data['order_id']}\n")
#         printer.text(f"Mesa: {order_data['table_number']}\n")
#         printer.text("--------------------------------\n")

#         # Platos
#         printer.text("Platos:\n")
#         for dish in order_data['dishes']:
#             # Letras más grandes y en negrita para el nombre del plato
#             printer.set(align='left', width=4, height=7, bold=True)
#             printer.text(f"- {dish['name']} x{dish['quantity']}\n")
#             printer.set(align='left', width=1, height=1, bold=False)
#             printer.text(f"  Precio: ${dish['price']:.2f}\n")
#             if 'extras' in dish and dish['extras']:
#                 printer.text("  Extras:\n")
#                 for extra in dish['extras']:
#                     printer.text(f"    + {extra['name']} x{extra['quantity']} - ${extra['price']:.2f}\n")
#             if 'exclusions' in dish and dish['exclusions']:
#                 printer.text("  Sin:\n")
#                 for exclusion in dish['exclusions']:
#                     printer.text(f"    - {exclusion['name']}\n")

#         # Bebidas
#         if 'drinks' in order_data and order_data['drinks']:
#             printer.text("--------------------------------\n")
#             printer.text("Bebidas:\n")
#             for drink in order_data['drinks']:
#                 printer.set(align='left', bold=True)
#                 printer.text(f"- {drink['name']} x{drink['quantity']}\n")
#                 printer.set(bold=False)
#                 printer.text(f"  Precio: ${drink['price']:.2f}\n")

#         # Total
#         printer.text("--------------------------------\n")
#         printer.set(align='right', width=2, height=2)
#         printer.text(f"Total: ${order_data['total']:.2f}\n")

#         # Mensaje de despedida
#         printer.text("--------------------------------\n")
#         printer.set(align='center', width=1, height=1)
#         printer.text("¡Esperamos verte pronto!\n")
#         printer.text("\n\n\n")  # Espacios para corte automático

#         # Corta el papel
#         printer.cut()

#     except Exception as e:
#         print(f"Error imprimiendo el ticket: {e}")

def generate_ticket_text(order_data: Dict) -> str:
    """
    Genera el texto del ticket en formato string.

    Args:
        order_data (Dict): Datos del pedido, incluyendo ID, número de mesa, platos, bebidas y total.

    Returns:
        str: Texto formateado del ticket.
    """
    ticket = []
    
    # Cabecera del ticket
    ticket.append("Restaurante El Mundo del Campero\n")
    ticket.append("¡Gracias por tu compra!\n")
    ticket.append("--------------------------------\n")

    # Información del pedido
    ticket.append(f"Pedido ID: {order_data['order_id']}\n")
    ticket.append(f"Mesa: {order_data['table_number']}\n")
    ticket.append("--------------------------------\n")

    # Platos
    ticket.append("Platos:\n")
    for dish in order_data['dishes']:
        ticket.append(f"- {dish['name']} x{dish['quantity']}\n")
        ticket.append(f"  Precio: ${dish['price']:.2f}\n")
        if 'extras' in dish and dish['extras']:
            ticket.append("  Extras:\n")
            for extra in dish['extras']:
                ticket.append(f"    + {extra['name']} x{extra['quantity']} - ${extra['price']:.2f}\n")
        if 'exclusions' in dish and dish['exclusions']:
            ticket.append("  Sin:\n")
            for exclusion in dish['exclusions']:
                ticket.append(f"    - {exclusion['name']}\n")

    # Bebidas
    if 'drinks' in order_data and order_data['drinks']:
        ticket.append("--------------------------------\n")
        ticket.append("Bebidas:\n")
        for drink in order_data['drinks']:
            ticket.append(f"- {drink['name']} x{drink['quantity']}\n")
            ticket.append(f"  Precio: ${drink['price']:.2f}\n")

    # Total
    ticket.append("--------------------------------\n")
    ticket.append(f"Total: ${order_data['total']:.2f}\n")

    # Mensaje de despedida
    ticket.append("--------------------------------\n")
    ticket.append("¡Esperamos verte pronto!\n")
    ticket.append("\n\n\n")  # Espacios para corte automático

    return ''.join(ticket)

def send_ticket_to_esp32(order_data: Dict):
    """
    Envía el ticket formateado a la ESP32 para impresión.

    Args:
        order_data (Dict): Datos del pedido.
    """
    esp32_ip = "192.168.1.153"  # Reemplaza con la IP local de la ESP32
    esp32_port = 9100              # Puerto configurado en la ESP32

    # Generar el texto del ticket
    ticket_data = generate_ticket_text(order_data)

    try:
        # Crear un socket TCP
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # Conectar al servidor ESP32
            s.connect((esp32_ip, esp32_port))
            # Enviar los datos del ticket
            s.sendall(ticket_data.encode('utf-8'))
            print("Ticket enviado a la ESP32")
    except Exception as e:
        print(f"Error enviando datos a la ESP32: {e}")
