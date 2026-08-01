class YouTubeService:
    def __init__(self, access_token: str):
        self.access_token = access_token

    async def upload_video(self):
        raise NotImplementedError(
            "YouTube publishing will be implemented in a future iteration."
        )
