class GoogleCalendarService:
    def __init__(self, access_token: str):
        self.access_token = access_token

    async def list_events(self):
        raise NotImplementedError(
            "Calendar integration will be implemented in a future iteration."
        )
