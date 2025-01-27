class PendingTickets:
    def __init__(self):
        self.tickets = []

    def add_ticket(self, ticket):
        self.tickets.append(ticket)

    def get_next_ticket(self):
        if not self.tickets:
            return None
        return self.tickets.pop(0)

    def has_tickets(self):
        return len(self.tickets) > 0


# Instancia global del singleton
pending_tickets_store = PendingTickets()
