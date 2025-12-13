"""Email service using Resend."""

import logging
from typing import Optional

import resend

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """
    Email service using Resend API.

    Provides methods for sending transactional emails including
    password reset, welcome emails, and notifications.
    """

    def __init__(self):
        self.api_key = settings.RESEND_API_KEY
        self.from_email = settings.EMAIL_FROM
        self.from_name = settings.EMAIL_FROM_NAME

        if self.api_key:
            resend.api_key = self.api_key

    @property
    def is_configured(self) -> bool:
        """Check if email service is properly configured."""
        return bool(self.api_key)

    def _get_from_address(self) -> str:
        """Get formatted from address."""
        return f"{self.from_name} <{self.from_email}>"

    async def send_email(
        self,
        to: str | list[str],
        subject: str,
        html: str,
        text: Optional[str] = None,
    ) -> dict:
        """
        Send an email using Resend.

        Args:
            to: Recipient email address(es).
            subject: Email subject line.
            html: HTML content of the email.
            text: Plain text content (optional).

        Returns:
            Response from Resend API.

        Raises:
            ValueError: If email service is not configured.
            Exception: If sending fails.
        """
        if not self.is_configured:
            logger.warning("Email service not configured, skipping send")
            return {"id": None, "message": "Email service not configured"}

        try:
            params = {
                "from": self._get_from_address(),
                "to": to if isinstance(to, list) else [to],
                "subject": subject,
                "html": html,
            }

            if text:
                params["text"] = text

            response = resend.Emails.send(params)
            logger.info(f"Email sent successfully to {to}")
            return response

        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}")
            raise

    async def send_password_reset(
        self,
        to: str,
        reset_token: str,
        user_name: Optional[str] = None,
    ) -> dict:
        """
        Send password reset email.

        Args:
            to: Recipient email address.
            reset_token: Password reset token.
            user_name: User's name for personalization.

        Returns:
            Response from Resend API.
        """
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

        greeting = f"Hi {user_name}," if user_name else "Hi,"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Reset Your Password</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont,
          'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
          line-height: 1.6; color: #333; max-width: 600px;
          margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg,
              #667eea 0%, #764ba2 100%); padding: 30px;
              border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;
                  font-size: 24px;">Marketing Mix Model</h1>
            </div>

            <div style="background: #ffffff; padding: 30px;
              border: 1px solid #e0e0e0; border-top: none;
              border-radius: 0 0 10px 10px;">
                <h2 style="color: #333; margin-top: 0;">
                  Reset Your Password</h2>

                <p>{greeting}</p>

                <p>We received a request to reset your password.
                  Click the button below to create a new
                  password:</p>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}"
                      style="background: linear-gradient(135deg,
                      #667eea 0%, #764ba2 100%); color: white;
                      padding: 14px 30px; text-decoration: none;
                      border-radius: 5px; font-weight: bold;
                      display: inline-block;">
                        Reset Password
                    </a>
                </div>

                <p style="color: #666; font-size: 14px;">
                    This link will expire in
                    {settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS}
                    hours.
                </p>

                <p style="color: #666; font-size: 14px;">
                    If you didn't request a password reset,
                    you can safely ignore this email.
                    Your password will not be changed.
                </p>

                <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">

                <p style="color: #999; font-size: 12px; margin-bottom: 0;">
                    If the button doesn't work, copy and paste this link into your browser:<br>
                    <a href="{reset_url}" style="color: #667eea; word-break: break-all;">{reset_url}</a>
                </p>
            </div>

            <div style="text-align: center; padding: 20px; color: #999; font-size: 12px;">
                <p>&copy; 2024 Marketing Mix Model. All rights reserved.</p>
            </div>
        </body>
        </html>
        """

        text = f"""
{greeting}

We received a request to reset your password.

Click the link below to create a new password:
{reset_url}

This link will expire in {settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS} hours.

If you didn't request a password reset, you can safely ignore this email.

---
Marketing Mix Model
        """

        return await self.send_email(
            to=to,
            subject="Reset Your Password - Marketing Mix Model",
            html=html,
            text=text,
        )

    async def send_welcome_email(
        self,
        to: str,
        user_name: str,
    ) -> dict:
        """
        Send welcome email to new user.

        Args:
            to: Recipient email address.
            user_name: User's name for personalization.

        Returns:
            Response from Resend API.
        """
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to Marketing Mix Model</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont,
          'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
          line-height: 1.6; color: #333; max-width: 600px;
          margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg,
              #667eea 0%, #764ba2 100%); padding: 30px;
              border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;
                  font-size: 24px;">Marketing Mix Model</h1>
            </div>

            <div style="background: #ffffff; padding: 30px;
              border: 1px solid #e0e0e0; border-top: none;
              border-radius: 0 0 10px 10px;">
                <h2 style="color: #333; margin-top: 0;">
                  Welcome, {user_name}!</h2>

                <p>Thank you for joining Marketing Mix Model.
                  We're excited to help you understand your
                  marketing effectiveness.</p>

                <p>Here's what you can do:</p>

                <ul style="color: #666;">
                    <li>Upload your marketing data</li>
                    <li>Build and compare multiple models</li>
                    <li>Analyze channel contributions</li>
                    <li>Generate professional reports</li>
                </ul>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{settings.FRONTEND_URL}/dashboard"
                      style="background: linear-gradient(135deg,
                      #667eea 0%, #764ba2 100%); color: white;
                      padding: 14px 30px; text-decoration: none;
                      border-radius: 5px; font-weight: bold;
                      display: inline-block;">
                        Go to Dashboard
                    </a>
                </div>

                <p style="color: #666;">If you have any questions, feel free to reach out!</p>
            </div>

            <div style="text-align: center; padding: 20px; color: #999; font-size: 12px;">
                <p>&copy; 2024 Marketing Mix Model. All rights reserved.</p>
            </div>
        </body>
        </html>
        """

        return await self.send_email(
            to=to,
            subject="Welcome to Marketing Mix Model!",
            html=html,
        )


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get email service singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service


async def send_password_reset_email(
    to: str,
    reset_token: str,
    user_name: Optional[str] = None,
) -> dict:
    """
    Convenience function to send password reset email.

    Args:
        to: Recipient email address.
        reset_token: Password reset token.
        user_name: User's name for personalization.

    Returns:
        Response from Resend API.
    """
    service = get_email_service()
    return await service.send_password_reset(to, reset_token, user_name)
