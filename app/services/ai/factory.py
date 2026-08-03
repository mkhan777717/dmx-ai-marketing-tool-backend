from app.constants.enums import ApiProvider
from app.services.ai.base import BaseAIProvider
from app.services.ai.mock_provider import MockAIProvider

# Future imports:
# from app.services.ai.openai_provider import OpenAIProvider


class AIProviderFactory:
    """
    Factory for instantiating the correct AI provider.
    """

    @staticmethod
    def get_provider(provider_type: ApiProvider) -> BaseAIProvider:
        if provider_type == ApiProvider.MOCK:
            return MockAIProvider()
        # elif provider_type == ApiProvider.OPENAI:
        #     return OpenAIProvider()
        else:
            # Fallback to mock for unimplemented providers during this phase
            return MockAIProvider()
