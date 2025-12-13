"""Password reset token repository."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.password_reset import PasswordResetToken
from app.repositories.base import BaseRepository


class PasswordResetRepository(BaseRepository[PasswordResetToken]):
    """Repository for password reset token operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, PasswordResetToken)

    async def create_token(self, user_id: UUID) -> PasswordResetToken:
        """Create a new password reset token for a user."""
        # Invalidate any existing tokens for this user
        await self.invalidate_user_tokens(user_id)

        # Create new token
        token = PasswordResetToken.create_token(user_id)
        self.db.add(token)
        await self.db.commit()
        await self.db.refresh(token)
        return token

    async def get_by_token(self, token: str) -> PasswordResetToken | None:
        """Get a password reset token by its token string."""
        result = await self.db.execute(select(PasswordResetToken).where(PasswordResetToken.token == token))
        return result.scalar_one_or_none()

    async def get_valid_token(self, token: str) -> PasswordResetToken | None:
        """Get a valid (not used, not expired) password reset token."""
        result = await self.db.execute(
            select(PasswordResetToken).where(
                and_(
                    PasswordResetToken.token == token,
                    not PasswordResetToken.used,
                    PasswordResetToken.expires_at > datetime.utcnow(),
                )
            )
        )
        return result.scalar_one_or_none()

    async def mark_as_used(self, token: PasswordResetToken) -> PasswordResetToken:
        """Mark a token as used."""
        token.used = True
        await self.db.commit()
        await self.db.refresh(token)
        return token

    async def invalidate_user_tokens(self, user_id: UUID) -> None:
        """Invalidate all existing tokens for a user."""
        result = await self.db.execute(
            select(PasswordResetToken).where(
                and_(
                    PasswordResetToken.user_id == user_id,
                    not PasswordResetToken.used,
                )
            )
        )
        tokens = result.scalars().all()

        for token in tokens:
            token.used = True

        await self.db.commit()

    async def cleanup_expired_tokens(self) -> int:
        """Delete expired tokens. Returns count of deleted tokens."""
        result = await self.db.execute(
            select(PasswordResetToken).where(PasswordResetToken.expires_at < datetime.utcnow())
        )
        tokens = result.scalars().all()

        count = len(tokens)
        for token in tokens:
            await self.db.delete(token)

        await self.db.commit()
        return count
