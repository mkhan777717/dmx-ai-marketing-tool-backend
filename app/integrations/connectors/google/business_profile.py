class GoogleBusinessProfileService:
    def __init__(self, access_token: str):
        self.access_token = access_token

    async def list_locations(self):
        raise NotImplementedError(
            "GMB locations sync will be implemented in a future iteration."
        )
