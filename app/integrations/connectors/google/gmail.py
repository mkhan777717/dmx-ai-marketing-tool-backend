class GmailService:
    def __init__(self, access_token: str):
        self.access_token = access_token

    async def get_profile(self):
        raise NotImplementedError(
            "Gmail integration will be implemented in a future iteration."
        )
