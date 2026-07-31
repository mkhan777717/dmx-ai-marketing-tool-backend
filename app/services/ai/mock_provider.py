from typing import Any

from app.constants.enums import ApiProvider
from app.schemas.campaign_content import (AIContentGenerateRequest,
                                          AIContentGenerateResponse)
from app.services.ai.base import BaseAIProvider


class MockAIProvider(BaseAIProvider):
    """
    Mock AI Provider used for testing and development.
    Returns deterministic responses.
    """

    @property
    def provider_name(self) -> str:
        return ApiProvider.MOCK.value

    async def generate_content(
        self, request: AIContentGenerateRequest, **kwargs: Any
    ) -> AIContentGenerateResponse:
        """
        Return a mock response simulating AI generation.
        """
        body = f"This is mock generated content for topic: {request.prompt}. Audience: {request.target_audience or 'General'}."
        summary = f"Mock summary for {request.prompt}"
        hashtags = "#mock #ai #marketing"
        cta = "Click here to see more mock content!"

        return AIContentGenerateResponse(
            content_type=request.content_type,
            body=body,
            summary=summary,
            hashtags=hashtags,
            cta=cta,
            metadata={"mocked": True, "language": request.language},
            provider_used=self.provider_name,
        )
