class PendingTickets:
    def __init__(self):
        self.tickets = []  # Almacena los tickets pendientes

    def add_ticket(self, ticket):
        self.tickets.append(ticket)

    def get_next_ticket(self):
        if not self.tickets:
            return None
        return self.tickets.pop(0)

    def has_tickets(self):
        return len(self.tickets) > 0


# Instancia global para manejar los tickets
pending_tickets_store = PendingTickets()

# Inicializa con datos de prueba
pending_tickets_store.tickets = [
    {
        "order_id": "250127106860",
        "table_number": 7,
        "dishes": [
            {
                "name": "Hamburguesa Clásica",
                "price": 7.5,
                "quantity": 1,
                "extras": [],
                "exclusions": [],
            }
        ],
        "drinks": [],
        "total": 7.5,
        "user_id": "whatsapp:+34607227417",
    }
]
