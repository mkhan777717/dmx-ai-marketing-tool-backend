from app.constants.enums import ApiProvider
from app.services.social.base import BaseSocialProvider
from app.services.social.facebook_provider import FacebookProvider
from app.services.social.instagram_provider import InstagramProvider
from app.services.social.linkedin_provider import LinkedInProvider
from app.services.social.mock_provider import MockSocialProvider


class SocialProviderFactory:
    """
    Factory for instantiating the correct Social Provider.
    """

    @staticmethod
    def get_provider(provider_type: ApiProvider) -> BaseSocialProvider:
        if provider_type == ApiProvider.MOCK:
            return MockSocialProvider()
        elif provider_type == ApiProvider.META:
            return FacebookProvider()
        elif provider_type == ApiProvider.INSTAGRAM:
            return InstagramProvider()
        elif provider_type == ApiProvider.LINKEDIN:
            return LinkedInProvider()
        elif provider_type == ApiProvider.GOOGLE:
            from app.services.social.google_provider import GoogleProvider

            return GoogleProvider()
        elif provider_type == ApiProvider.TWITTER:
            from app.services.social.twitter_provider import TwitterProvider

            return TwitterProvider()
        else:
            # Fallback for unconnected or unimplemented
            return MockSocialProvider()
