class GoogleDriveService:
    def __init__(self, access_token: str):
        self.access_token = access_token

    async def list_files(self):
        raise NotImplementedError(
            "Drive integration will be implemented in a future iteration."
        )
