from abc import ABC, abstractmethod
from typing import Any

from app.schemas.campaign_content import (AIContentGenerateRequest,
                                          AIContentGenerateResponse)


class BaseAIProvider(ABC):
    """
    Abstract base class for all AI providers.
    Ensures that business logic is decoupled from specific APIs (OpenAI, Claude, etc).
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of the provider."""
        pass

    @abstractmethod
    async def generate_content(
        self, request: AIContentGenerateRequest, **kwargs: Any
    ) -> AIContentGenerateResponse:
        """
        Generate content using the AI provider.
        """
        pass
