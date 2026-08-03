from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.operations.configuration.models import DataType, RuntimeConfiguration


class ConfigurationService:
    @staticmethod
    async def get_config(db: AsyncSession, key: str) -> str | None:
        stmt = select(RuntimeConfiguration).where(
            RuntimeConfiguration.key == key, RuntimeConfiguration.is_active
        )
        result = await db.execute(stmt)
        config = result.scalars().first()
        return config.value if config else None

    @staticmethod
    async def get_all_configs(db: AsyncSession) -> Sequence[RuntimeConfiguration]:
        result = await db.execute(select(RuntimeConfiguration))
        return result.scalars().all()

    @staticmethod
    async def set_config(
        db: AsyncSession, key: str, value: str, data_type: DataType = DataType.STRING
    ) -> RuntimeConfiguration:
        stmt = select(RuntimeConfiguration).where(RuntimeConfiguration.key == key)
        result = await db.execute(stmt)
        config = result.scalars().first()

        if config:
            config.value = value
            config.data_type = data_type
            config.is_active = True
        else:
            config = RuntimeConfiguration(key=key, value=value, data_type=data_type)
            db.add(config)

        await db.commit()
        await db.refresh(config)
        return config
