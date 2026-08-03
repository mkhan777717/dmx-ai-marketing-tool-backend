import logging

logger = logging.getLogger(__name__)


class InvitationService:
    """
    Abstract interface for sending emails.
    Currently logs to console, but designed to be replaced by Resend, SendGrid, etc.
    """

    @staticmethod
    async def send_invitation(
        email: str, workspace_name: str, token: str, inviter_name: str | None = None
    ) -> bool:
        # Construct invite URL (would normally come from settings)
        invite_url = f"https://frontend-url.com/invites/{token}/accept"
        inviter = inviter_name or "Someone"

        message = (
            f"--- MOCK EMAIL SENDER ---\n"
            f"To: {email}\n"
            f"Subject: You have been invited to join {workspace_name}\n"
            f"Body: {inviter} invited you to join their workspace. Click here to accept: {invite_url}\n"
            f"-------------------------"
        )
        logger.info(message)
        return True

    @staticmethod
    async def resend_invitation(email: str, workspace_name: str, token: str) -> bool:
        return await InvitationService.send_invitation(
            email, workspace_name, token, inviter_name="Workspace Admin (Resend)"
        )


email_service = InvitationService()
