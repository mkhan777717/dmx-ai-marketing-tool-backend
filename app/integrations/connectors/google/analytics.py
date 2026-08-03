class GoogleAnalyticsService:
    def __init__(self, access_token: str):
        self.access_token = access_token

    async def get_report(self):
        raise NotImplementedError(
            "GA4 reporting will be implemented in a future iteration."
        )
