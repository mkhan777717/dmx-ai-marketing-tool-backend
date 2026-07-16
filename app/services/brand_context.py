import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.brand_kit import brand_kit_repo
from typing import Any

class BrandContextService:
    @staticmethod
    async def build_context(db: AsyncSession, workspace_id: uuid.UUID) -> dict[str, Any] | None:
        """
        Builds a flattened, read-only dictionary of the brand context 
        optimized for injection into AI prompts and creative modules.
        Returns None if no brand kit exists.
        """
        kit = await brand_kit_repo.get_by_workspace(db, workspace_id)
        if not kit:
            return None
            
        return {
            "brand_name": kit.brand_name,
            "brand_voice": kit.brand_voice,
            "tone_of_voice": kit.tone_of_voice,
            "brand_description": kit.brand_description,
            "colors": {
                "primary": kit.primary_color,
                "secondary": kit.secondary_color,
                "accent": kit.accent_color
            },
            "fonts": {
                "primary": kit.font_family
            },
            "target_audience": kit.target_audience,
            "default_language": kit.default_language,
            "ai_instructions": kit.ai_writing_instructions,
            "restrictions": kit.ai_content_restrictions,
            "website": kit.website_url,
            "industry": kit.industry
        }

brand_context_service = BrandContextService()
